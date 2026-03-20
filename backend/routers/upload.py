import logging
import os
import uuid
from datetime import datetime, timezone

import aiofiles
from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlalchemy import select

from database import AnalysisRecord, async_session
from middleware import MAX_UPLOAD_BYTES
from models.bundle import AnalysisStatus, BundleMetadata
from rate_limit import UPLOAD_RATE, limiter
from security import validate_upload_filename

logger = logging.getLogger("bundlescope")

router = APIRouter(tags=["upload"])


@router.post("/upload")
@limiter.limit(UPLOAD_RATE)
async def upload_bundle(request: Request, file: UploadFile = File(...)):
    # Validate filename
    safe_filename = validate_upload_filename(file.filename)
    if not safe_filename:
        raise HTTPException(
            status_code=400,
            detail="Invalid file. Must be a .tar.gz or .tgz archive with a valid filename.",
        )

    analysis_id = str(uuid.uuid4())
    upload_dir = os.path.join("uploads", analysis_id)
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, safe_filename)
    size = 0

    try:
        async with aiofiles.open(file_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):  # 1MB chunks
                size += len(chunk)
                # Enforce size limit during streaming (defense in depth)
                if size > MAX_UPLOAD_BYTES:
                    await f.close()
                    # Clean up partial file
                    try:
                        os.remove(file_path)
                        os.rmdir(upload_dir)
                    except OSError:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"File too large. Maximum upload size is {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
                    )
                await f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Upload write failed for %s: %s", analysis_id, e)
        # Clean up on failure
        try:
            os.remove(file_path)
            os.rmdir(upload_dir)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail="Upload failed. Please try again.")

    logger.info("Upload complete: id=%s, file=%s, size=%d bytes", analysis_id, safe_filename, size)

    now = datetime.now(timezone.utc)
    record = AnalysisRecord(
        id=analysis_id,
        filename=safe_filename,
        upload_time=now,
        status=AnalysisStatus.PENDING.value,
        size_bytes=size,
    )
    async with async_session() as session:
        session.add(record)
        await session.commit()

    return {"analysis_id": analysis_id, "filename": safe_filename, "size_bytes": size}


@router.get("/analyses")
async def list_analyses():
    async with async_session() as session:
        result = await session.execute(
            select(AnalysisRecord).order_by(AnalysisRecord.upload_time.desc()).limit(100)
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
    from security import is_valid_uuid

    if not is_valid_uuid(analysis_id):
        raise HTTPException(status_code=400, detail="Invalid analysis ID format")

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
