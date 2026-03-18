import os
import uuid
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile

from models.bundle import AnalysisStatus, BundleMetadata

router = APIRouter(tags=["upload"])

analyses: dict[str, BundleMetadata] = {}


@router.post("/upload")
async def upload_bundle(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith((".tar.gz", ".tgz")):
        raise HTTPException(status_code=400, detail="File must be a .tar.gz or .tgz archive")

    analysis_id = str(uuid.uuid4())
    upload_dir = os.path.join("uploads", analysis_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, file.filename)
    size = 0
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            await f.write(chunk)
            size += len(chunk)

    metadata = BundleMetadata(
        id=analysis_id,
        filename=file.filename,
        upload_time=datetime.now(timezone.utc),
        status=AnalysisStatus.PENDING,
        size_bytes=size,
    )
    analyses[analysis_id] = metadata

    return {"analysis_id": analysis_id, "filename": file.filename, "size_bytes": size}


@router.get("/analyses")
async def list_analyses():
    return sorted(analyses.values(), key=lambda a: a.upload_time, reverse=True)


@router.get("/analyses/{analysis_id}")
async def get_analysis_metadata(analysis_id: str):
    if analysis_id not in analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analyses[analysis_id]
