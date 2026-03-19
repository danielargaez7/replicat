import os
import uuid
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile
from sqlalchemy import select

from database import AnalysisRecord, async_session
from models.bundle import AnalysisStatus, BundleMetadata

router = APIRouter(tags=["upload"])


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

    now = datetime.now(timezone.utc)
    record = AnalysisRecord(
        id=analysis_id,
        filename=file.filename,
        upload_time=now,
        status=AnalysisStatus.PENDING.value,
        size_bytes=size,
    )
    async with async_session() as session:
        session.add(record)
        await session.commit()

    return {"analysis_id": analysis_id, "filename": file.filename, "size_bytes": size}


@router.get("/analyses")
async def list_analyses():
    async with async_session() as session:
        result = await session.execute(
            select(AnalysisRecord).order_by(AnalysisRecord.upload_time.desc())
        )
        records = result.scalars().all()

    return [
        BundleMetadata(
            id=r.id,
            filename=r.filename,
            upload_time=r.upload_time,
            status=AnalysisStatus(r.status),
            file_count=r.file_count,
            size_bytes=r.size_bytes,
        )
        for r in records
    ]


@router.get("/analyses/{analysis_id}")
async def get_analysis_metadata(analysis_id: str):
    async with async_session() as session:
        record = await session.get(AnalysisRecord, analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return BundleMetadata(
        id=record.id,
        filename=record.filename,
        upload_time=record.upload_time,
        status=AnalysisStatus(record.status),
        file_count=record.file_count,
        size_bytes=record.size_bytes,
    )
