import os

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel
from sqlalchemy import select

from cache import get_cached_result
from database import AnalysisResultRecord, ChatMessageRecord, async_session
from models.findings import AnalysisResult
from prompts.chat import build_chat_context

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    message: str


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
async def chat_about_analysis(analysis_id: str, msg: ChatMessage):
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
            content=msg.message,
        ))
        await session.commit()

    # Load chat history from DB
    async with async_session() as session:
        rows = await session.execute(
            select(ChatMessageRecord)
            .where(ChatMessageRecord.analysis_id == analysis_id)
            .order_by(ChatMessageRecord.id)
        )
        history = [{"role": r.role, "content": r.content} for r in rows.scalars().all()]

    client = AsyncOpenAI(
        api_key=os.environ.get("OPENAI_API_KEY", ""),
        base_url=os.environ.get("OPENAI_BASE_URL"),
    )
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                *history[-10:],
            ],
            temperature=0.3,
            max_tokens=1024,
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
            if f.resource_name and f.resource_name.lower() in msg.message.lower():
                sources.append(f"{f.resource_kind}/{f.resource_name}")

        return ChatResponse(response=reply, sources=sources[:5])

    except Exception as e:
        return ChatResponse(
            response=f"Chat unavailable: {e}. Please check your API key configuration.",
            sources=[],
        )
