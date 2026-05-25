from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="app.workers.scan_worker.run_scan", max_retries=3)
def run_scan(self, scan_id: str, target_url: str, scan_type: str = "url"):
    """
    Main scan Celery task.
    Phase 4 will replace this stub with the full LangGraph agent orchestration.
    """
    logger.info(f"[Scan {scan_id}] Starting scan for {target_url} (type={scan_type})")
    try:
        # TODO Phase 4: initialize LangGraph agent, run ReAct loop, stream events to Redis pub/sub
        return {
            "scan_id": scan_id,
            "status": "completed",
            "findings_count": 0,
            "message": "Placeholder — full agent implemented in Phase 4",
        }
    except Exception as exc:
        logger.error(f"[Scan {scan_id}] Failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
