import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import traceback
from services.automation_service import AutomationService

logger = logging.getLogger(__name__)

class JobManager:
    """
    Manages background jobs using the 'jobs' table.
    """

    def __init__(self):
        self._registry: Dict[str, Callable] = {}

    def register(self, job_type: str, handler: Callable):
        """Register a handler function for a job type."""
        self._registry[job_type] = handler
        logger.info(f"JOB: Registered handler for '{job_type}'")

    def enqueue(self, job_type: str, payload: Dict[str, Any], db: Session) -> str:
        """Create a new job in pending state."""
        job_id = str(uuid.uuid4())
        job = models.Job(
            id=job_id,
            type=job_type,
            status="pending",
            payload=json.dumps(payload),
            created_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        logger.info(f"JOB: Enqueued {job_type} ({job_id})")
        return job_id

    def run_worker(self, single_run: bool = False):
        """
        Worker loop to process pending jobs.
        In a real deployment, this would run in a separate process or thread.
        """
        db = SessionLocal()
        try:
            while True:
                # 1. Fetch next pending job
                job = db.query(models.Job).filter(models.Job.status == "pending").first()
                
                if not job:
                    if single_run:
                        break
                    # Sleep or wait in real loop (simplified here)
                    break 

                # 2. Lock/Start job
                job.status = "running"
                job.started_at = datetime.utcnow()
                db.commit()

                logger.info(f"JOB: Starting {job.type} ({job.id})")

                # 3. Execute
                try:
                    handler = self._registry.get(job.type)
                    if not handler:
                        raise ValueError(f"No handler registered for job type '{job.type}'")
                    
                    payload = json.loads(job.payload) if job.payload else {}
                    result = handler(payload, db)
                    
                    job.result = json.dumps(result)
                    job.status = "completed"
                except Exception as e:
                    logger.error(f"JOB FAILED: {job.type} ({job.id}) - {str(e)}")
                    traceback.print_exc()
                    job.error = str(e)
                    job.status = "failed"
                finally:
                    job.completed_at = datetime.utcnow()
                    db.commit()
                    
        finally:
            db.close()

# Global Job Manager Instance
job_manager = JobManager()

# --- Job Handlers ---

def automation_sync_handler(payload: Dict[str, Any], db: Session):
    """Handler for syncing external sources (Email/OneDrive)."""
    service = AutomationService(db)
    
    # Run syncs
    service.sync_email_invoices()
    service.sync_onedrive_invoices()
    
    return {"status": "success", "timestamp": datetime.utcnow().isoformat()}

# Register handlers
job_manager.register("automation_sync", automation_sync_handler)
