from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user
from app.api.v1.schemas import ReportExportRead
from app.core.database import get_db
from app.models import AuditEvent, ReportExport, Scan, User
from app.services.access_control import load_scan_for_user
from app.services.risk import build_risk_report, render_markdown_report, render_pdf_report

router = APIRouter()


async def _load_scan_for_user(scan_id: str, db: AsyncSession, user: User) -> Scan:
    return await load_scan_for_user(db, scan_id=scan_id, user=user)


async def _record_export(
    db: AsyncSession, *, scan: Scan, user: User, export_type: str, media_type: str
) -> None:
    db.add(
        ReportExport(
            scan_id=scan.id,
            requested_by_id=user.id,
            export_type=export_type,
            status="completed",
            artifact_uri=None,
            metadata_json={"media_type": media_type},
        )
    )
    db.add(
        AuditEvent(
            user_id=user.id,
            target_id=scan.target_id,
            scan_id=scan.id,
            event_type="report.exported",
            message=f"{export_type.upper()} report exported.",
            details={"export_type": export_type, "media_type": media_type},
        )
    )
    await db.commit()


@router.get("/{scan_id}/pdf")
async def download_pdf(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await _load_scan_for_user(scan_id, db, current_user)
    report = _risk_report_for_scan(scan)
    pdf_bytes = render_pdf_report(report)
    await _record_export(db, scan=scan, user=current_user, export_type="pdf", media_type="application/pdf")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="armorscan-{scan.id}.pdf"'},
    )


@router.get("/{scan_id}/markdown")
async def download_markdown(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await _load_scan_for_user(scan_id, db, current_user)
    report = _risk_report_for_scan(scan)
    await _record_export(
        db, scan=scan, user=current_user, export_type="markdown", media_type="text/markdown"
    )
    return Response(
        content=render_markdown_report(report),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="armorscan-{scan.id}.md"'},
    )


@router.get("/{scan_id}/sarif")
async def download_sarif(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await _load_scan_for_user(scan_id, db, current_user)
    await _record_export(
        db, scan=scan, user=current_user, export_type="sarif", media_type="application/sarif+json"
    )
    return {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "ArmorScan AI",
                        "version": "0.1.0",
                        "informationUri": "https://github.com/",
                        "rules": [
                            {
                                "id": finding.id,
                                "name": finding.title,
                                "shortDescription": {"text": finding.title},
                                "fullDescription": {"text": finding.summary},
                                "help": {"text": finding.remediation or ""},
                                "properties": {
                                    "severity": finding.severity,
                                    "risk_score": finding.risk_score,
                                    "risk_rating": finding.risk_rating,
                                    "confidence": finding.confidence,
                                },
                            }
                            for finding in scan.findings
                        ],
                    }
                },
                "results": [
                    {
                        "ruleId": finding.id,
                        "level": _sarif_level(finding.risk_rating),
                        "message": {"text": finding.title},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": scan.target.target_url},
                                    "region": {"snippet": {"text": finding.location}},
                                }
                            }
                        ],
                        "properties": {
                            "risk_score": finding.risk_score,
                            "risk_rating": finding.risk_rating,
                            "confidence": finding.confidence,
                            "business_impact": finding.business_impact,
                            "remediation": finding.remediation,
                        },
                    }
                    for finding in scan.findings
                ],
            }
        ],
    }


@router.get("/{scan_id}/json")
async def download_json(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = await _load_scan_for_user(scan_id, db, current_user)
    risk_report = _risk_report_for_scan(scan)
    await _record_export(
        db, scan=scan, user=current_user, export_type="json", media_type="application/json"
    )
    audit_result = await db.execute(
        select(AuditEvent).where(AuditEvent.scan_id == scan.id).order_by(AuditEvent.created_at.asc())
    )
    return {
        "scan": {
            "id": scan.id,
            "status": scan.status,
            "scan_type": scan.scan_type,
            "summary": scan.summary,
            "report_json": scan.report_json,
            "risk_report": risk_report,
            "agent_trace": scan.agent_trace,
            "intent_plan": scan.intent_plan,
            "policy_decisions": scan.policy_decisions,
            "created_at": scan.created_at,
            "completed_at": scan.completed_at,
        },
        "target": {
            "id": scan.target.id,
            "name": scan.target.name,
            "target_type": scan.target.target_type,
            "target_url": scan.target.target_url,
            "scope": scan.target.scope,
        },
        "findings": [
            {
                "id": finding.id,
                "severity": finding.severity,
                "title": finding.title,
                "location": finding.location,
                "confidence": finding.confidence,
                "risk_score": finding.risk_score,
                "risk_rating": finding.risk_rating,
                "status": finding.status,
                "summary": finding.summary,
                "business_impact": finding.business_impact,
                "remediation": finding.remediation,
                "risk_factors": finding.risk_factors,
                "reproduction_steps": finding.reproduction_steps,
            }
            for finding in scan.findings
        ],
        "audit_events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "message": event.message,
                "details": event.details,
                "created_at": event.created_at,
            }
            for event in audit_result.scalars().all()
        ],
    }


@router.get("/{scan_id}/exports", response_model=list[ReportExportRead])
async def list_report_exports(
    scan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    await _load_scan_for_user(scan_id, db, current_user)
    result = await db.execute(
        select(ReportExport)
        .where(ReportExport.scan_id == scan_id)
        .order_by(ReportExport.created_at.desc())
    )
    return [ReportExportRead.model_validate(export) for export in result.scalars().all()]


def _finding_dict(finding) -> dict:
    return {
        "id": finding.id,
        "severity": finding.severity,
        "title": finding.title,
        "location": finding.location,
        "confidence": finding.confidence,
        "risk_score": finding.risk_score,
        "risk_rating": finding.risk_rating,
        "summary": finding.summary,
        "business_impact": finding.business_impact,
        "remediation": finding.remediation,
        "risk_factors": finding.risk_factors,
        "reproduction_steps": finding.reproduction_steps,
    }


def _risk_report_for_scan(scan: Scan) -> dict:
    existing = (scan.report_json or {}).get("risk_report")
    if existing:
        return existing
    return build_risk_report(
        scan={
            "id": scan.id,
            "status": scan.status,
            "scan_type": scan.scan_type,
            "created_at": scan.created_at,
            "completed_at": scan.completed_at,
        },
        target={
            "id": scan.target.id,
            "name": scan.target.name,
            "target_type": scan.target.target_type,
            "target_url": scan.target.target_url,
            "scope": scan.target.scope,
        },
        findings=[_finding_dict(finding) for finding in scan.findings],
    )


def _sarif_level(rating: str) -> str:
    if rating in {"critical", "high"}:
        return "error"
    if rating in {"medium", "low"}:
        return "warning"
    return "note"
