import os

from fastapi import APIRouter, HTTPException
from openai import AsyncOpenAI
from pydantic import BaseModel

from prompts.chat import build_chat_context

router = APIRouter(tags=["chat"])

chat_histories: dict[str, list[dict]] = {}


class ChatMessage(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str
    sources: list[str] = []


@router.post("/analysis/{analysis_id}/chat")
async def chat_about_analysis(analysis_id: str, msg: ChatMessage):
    from routers.analysis import results_store

    if analysis_id not in results_store:
        raise HTTPException(status_code=404, detail="Analysis not found or not yet complete")

    result = results_store[analysis_id]

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

    if analysis_id not in chat_histories:
        chat_histories[analysis_id] = []

    chat_histories[analysis_id].append({"role": "user", "content": msg.message})

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
                *chat_histories[analysis_id][-10:],
            ],
            temperature=0.3,
            max_tokens=1024,
        )

        reply = response.choices[0].message.content or "I couldn't generate a response."
        chat_histories[analysis_id].append({"role": "assistant", "content": reply})

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
