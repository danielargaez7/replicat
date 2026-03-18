import json
import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from models.findings import AnalysisResult

router = APIRouter(tags=["analysis"])

results_store: dict[str, AnalysisResult] = {}
bundle_roots: dict[str, str] = {}


@router.get("/analysis/{analysis_id}")
async def get_analysis(analysis_id: str):
    if analysis_id not in results_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return results_store[analysis_id]


@router.get("/analysis/{analysis_id}/logs")
async def get_log_file(analysis_id: str, path: str = Query(...)):
    if analysis_id not in bundle_roots:
        raise HTTPException(status_code=404, detail="Bundle data not found")

    from services.bundle_parser import read_log_file
    root = bundle_roots[analysis_id]
    content = read_log_file(root, path, max_lines=1000)
    if not content:
        raise HTTPException(status_code=404, detail="Log file not found")
    return {"path": path, "content": content}


@router.get("/analysis/{analysis_id}/files")
async def get_file_tree(analysis_id: str):
    if analysis_id not in results_store:
        raise HTTPException(status_code=404, detail="Analysis not found")
    # File tree is included in the full analysis result's parsed data
    return {"analysis_id": analysis_id}


@router.get("/analysis/{analysis_id}/stream")
async def stream_analysis(analysis_id: str):
    from routers.upload import analyses
    from services.pipeline import run_analysis_pipeline

    if analysis_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    metadata = analyses[analysis_id]
    bundle_path = os.path.join("uploads", analysis_id, metadata.filename)

    if not os.path.exists(bundle_path):
        raise HTTPException(status_code=404, detail="Bundle file not found")

    async def event_stream():
        async for event_type, data in run_analysis_pipeline(analysis_id, bundle_path):
            payload = json.dumps(data) if isinstance(data, (dict, list)) else str(data)
            yield f"event: {event_type}\ndata: {payload}\n\n"

            if event_type == "complete":
                result = AnalysisResult(**data)
                results_store[analysis_id] = result

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
