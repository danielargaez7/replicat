import io
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from cache import get_cached_result
from database import (
    AnalysisResultRecord,
    RemediationApprovalRecord,
    async_session,
)
from models.findings import AnalysisResult
from models.remediation import RemediationPlan
from security import is_valid_uuid
from services.pdf_generator import generate_playbook_pdf
from services.remediation import build_remediation_plan

logger = logging.getLogger("bundlescope")

router = APIRouter(tags=["remediation"])


def _validate_id(value: str, label: str = "ID") -> None:
    if not is_valid_uuid(value):
        raise HTTPException(status_code=400, detail=f"Invalid {label} format")


async def _load_analysis_result(analysis_id: str) -> AnalysisResult:
    """Load an analysis result from cache or database."""
    cached = await get_cached_result(analysis_id)
    if cached:
        return AnalysisResult(**cached)

    async with async_session() as session:
        record = await session.get(AnalysisResultRecord, analysis_id)
    if not record:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return AnalysisResult(**record.result_data)


@router.get("/analysis/{analysis_id}/remediation-plan")
async def get_remediation_plan(analysis_id: str) -> RemediationPlan:
    """Build and return a structured, ordered remediation plan."""
    _validate_id(analysis_id, "analysis ID")
    result = await _load_analysis_result(analysis_id)

    if result.status != "complete":
        raise HTTPException(status_code=409, detail="Analysis is not yet complete")

    plan = build_remediation_plan(result)

    # Merge any existing approvals
    async with async_session() as session:
        stmt = select(RemediationApprovalRecord).where(
            RemediationApprovalRecord.analysis_id == analysis_id
        )
        approvals = (await session.execute(stmt)).scalars().all()
        approved_ids = {a.id for a in approvals}

    for item in plan.items:
        if item.id in approved_ids:
            item.approved = True

    return plan


@router.get("/analysis/{analysis_id}/playbook")
async def download_playbook(analysis_id: str):
    """Generate and download a remediation playbook PDF."""
    _validate_id(analysis_id, "analysis ID")
    result = await _load_analysis_result(analysis_id)

    if result.status != "complete":
        raise HTTPException(status_code=409, detail="Analysis is not yet complete")

    plan = build_remediation_plan(result)
    pdf_bytes = generate_playbook_pdf(plan)

    filename = f"bundlescope-playbook-{analysis_id[:8]}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/analysis/{analysis_id}/remediation/{remediation_id}/approve")
async def approve_remediation(analysis_id: str, remediation_id: str):
    """Record approval for a specific remediation item."""
    _validate_id(analysis_id, "analysis ID")
    _validate_id(remediation_id, "remediation ID")

    async with async_session() as session:
        existing = await session.get(RemediationApprovalRecord, remediation_id)
        if existing:
            return {"approved": True, "remediation_id": remediation_id, "already_approved": True}

        approval = RemediationApprovalRecord(
            id=remediation_id,
            analysis_id=analysis_id,
            approved_at=datetime.now(timezone.utc),
            approved_by="",  # Future: extract from auth context
        )
        session.add(approval)
        await session.commit()

    logger.info("Remediation %s approved for analysis %s", remediation_id, analysis_id)
    return {"approved": True, "remediation_id": remediation_id}
