import asyncio
import logging
import os

from fastapi import APIRouter, HTTPException, Request
from openai import AsyncOpenAI
from pydantic import BaseModel, Field
from sqlalchemy import select

from cache import get_cached_result
from database import AnalysisResultRecord, ChatMessageRecord, async_session
from models.findings import AnalysisResult
from prompts.chat import build_chat_context
from rate_limit import CHAT_RATE, limiter
from security import is_valid_uuid, sanitize_chat_input

logger = logging.getLogger("bundlescope")

router = APIRouter(tags=["chat"])

# Timeout for OpenAI API calls (seconds)
OPENAI_TIMEOUT = 30


class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    response: str
    sources: list[str] = []


async def _get_analysis_result(analysis_id: str) -> AnalysisResult:
    cached = await get_cached_result(analysis_id)
    if cached:
        return AnalysisResult(**cached)

    async with async_session() as session:
        record = await session.get(AnalysisResultRecord, analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found or not yet complete")
    return AnalysisResult(**record.result_data)


@router.post("/analysis/{analysis_id}/chat")
@limiter.limit(CHAT_RATE)
async def chat_about_analysis(request: Request, analysis_id: str, msg: ChatMessage):
    if not is_valid_uuid(analysis_id):
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

    # Sanitize user input
    clean_message = sanitize_chat_input(msg.message)
    if not clean_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    result = await _get_analysis_result(analysis_id)

    findings_text = "\n".join(
        f"- [{f.severity.value.upper()}] {f.title}: {f.description[:200]}"
        for f in result.findings[:30]
    )

    bundle_stats = (
        f"Cluster: {result.cluster_version}\n"
        f"Namespaces: {result.namespace_count}, Nodes: {result.node_count}, "
        f"Pods: {result.pod_count} ({result.pod_failing_count} failing)\n"
        f"Warning events: {result.event_warning_count}"
    )

    system_prompt = build_chat_context(
        analysis_summary=result.summary or "No summary available.",
        findings_text=findings_text,
        bundle_stats=bundle_stats,
    )

    # Save user message to DB
    async with async_session() as session:
        session.add(ChatMessageRecord(
            analysis_id=analysis_id,
            role="user",
            content=clean_message,
        ))
        await session.commit()

    # Load chat history from DB (limited to recent messages)
    async with async_session() as session:
        rows = await session.execute(
            select(ChatMessageRecord)
            .where(ChatMessageRecord.analysis_id == analysis_id)
            .order_by(ChatMessageRecord.id.desc())
            .limit(20)
        )
        history = [{"role": r.role, "content": r.content} for r in reversed(rows.scalars().all())]

    api_key = os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return ChatResponse(
            response="Chat is unavailable: no API key configured.",
            sources=[],
        )

    client = AsyncOpenAI(
        api_key=api_key,
        base_url=os.environ.get("OPENAI_BASE_URL"),
        timeout=OPENAI_TIMEOUT,
    )
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    *history[-10:],
                ],
                temperature=0.3,
                max_tokens=1024,
            ),
            timeout=OPENAI_TIMEOUT + 5,
        )

        reply = response.choices[0].message.content or "I couldn't generate a response."

        # Save assistant reply to DB
        async with async_session() as session:
            session.add(ChatMessageRecord(
                analysis_id=analysis_id,
                role="assistant",
                content=reply,
            ))
            await session.commit()

        sources = []
        for f in result.findings:
            if f.resource_name and f.resource_name.lower() in clean_message.lower():
                sources.append(f"{f.resource_kind}/{f.resource_name}")

        return ChatResponse(response=reply, sources=sources[:5])

    except asyncio.TimeoutError:
        logger.error("OpenAI API timeout for analysis %s", analysis_id)
        return ChatResponse(
            response="Request timed out. Please try again with a shorter question.",
            sources=[],
        )
    except Exception as e:
        # Log the real error but return a safe message
        logger.error("Chat error for analysis %s: %s", analysis_id, type(e).__name__)
        return ChatResponse(
            response="Chat is temporarily unavailable. Please check your API key configuration and try again.",
            sources=[],
        )
