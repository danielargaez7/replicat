import json
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from cache import get_cached_result, set_cached_result
from database import (
    AnalysisRecord,
    AnalysisResultRecord,
    BundleRootRecord,
    async_session,
)
from models.findings import AnalysisResult

router = APIRouter(tags=["analysis"])


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    # Try cache first
    cached = await get_cached_result(analysis_id)
    if cached:
        return AnalysisResult(**cached)

    # Fall back to database
    async with async_session() as session:
        record = await session.get(AnalysisResultRecord, analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")

    result_data = record.result_data
    # Populate cache for next time
    await set_cached_result(analysis_id, result_data)
    return AnalysisResult(**result_data)


@router.get("/analysis/{analysis_id}/logs")
async def get_log_file(analysis_id: str, path: str = Query(...)):
    async with async_session() as session:
        record = await session.get(BundleRootRecord, analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Bundle data not found")

    from services.bundle_parser import read_log_file

    content = read_log_file(record.root_path, path, max_lines=1000)
    if not content:
        raise HTTPException(status_code=404, detail="Log file not found")
    return {"path": path, "content": content}


@router.get("/analysis/{analysis_id}/files")
async def get_file_tree(analysis_id: str):
    async with async_session() as session:
        record = await session.get(AnalysisResultRecord, analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return {"analysis_id": analysis_id}


@router.get("/analysis/{analysis_id}/stream")
async def stream_analysis(analysis_id: str):
    from services.pipeline import run_analysis_pipeline

    async with async_session() as session:
        metadata = await session.get(AnalysisRecord, analysis_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Analysis not found")

    bundle_path = os.path.join("uploads", analysis_id, metadata.filename)

    if not os.path.exists(bundle_path):
        raise HTTPException(status_code=404, detail="Bundle file not found")

    async def event_stream():
        async for event_type, data in run_analysis_pipeline(analysis_id, bundle_path):
            payload = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
            yield f"event: {event_type}\ndata: {payload}\n\n"

            if event_type == "complete":
                result = AnalysisResult(**data)
                result_record = AnalysisResultRecord(
                    id=analysis_id,
                    bundle_id=result.bundle_id,
                    result_data=data,
                )
                async with async_session() as session:
                    await session.merge(result_record)
                    await session.commit()
                await set_cached_result(analysis_id, data)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
