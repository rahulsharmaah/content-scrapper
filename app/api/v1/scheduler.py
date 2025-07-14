from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List
import structlog
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.job import ScrapingJob, JobFrequency, JobStatus
from app.workers.tasks import scheduled_scraping_task

logger = structlog.get_logger()
router = APIRouter()

@router.post("/jobs/")
async def create_scheduled_job(
    target_url: str,
    frequency: JobFrequency = JobFrequency.DAILY,
    db: AsyncSession = Depends(get_db)
):
    """Create a new scheduled scraping job"""
    try:
        # Calculate next run time
        now = datetime.utcnow()
        if frequency == JobFrequency.DAILY:
            next_run = now + timedelta(days=1)
        elif frequency == JobFrequency.WEEKLY:
            next_run = now + timedelta(weeks=1)
        elif frequency == JobFrequency.MONTHLY:
            next_run = now + timedelta(days=30)
        else:
            next_run = now + timedelta(days=1)
        
        job = ScrapingJob(
            target_url=target_url,
            frequency=frequency,
            next_run_at=next_run,
            status=JobStatus.ACTIVE
        )
        
        db.add(job)
        await db.commit()
        await db.refresh(job)
        
        logger.info("Scheduled job created", job_id=job.id, target_url=target_url)
        return job
        
    except Exception as e:
        await db.rollback()
        logger.error("Failed to create scheduled job", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create scheduled job"
        )

@router.get("/jobs/", response_model=List[ScrapingJob])
async def get_scheduled_jobs(
    db: AsyncSession = Depends(get_db)
):
    """Get all scheduled jobs"""
    try:
        result = await db.execute(
            select(ScrapingJob).order_by(ScrapingJob.created_at.desc())
        )
        jobs = result.scalars().all()
        return jobs
        
    except Exception as e:
        logger.error("Failed to fetch scheduled jobs", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch scheduled jobs"
        )

@router.put("/jobs/{job_id}/pause")
async def pause_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Pause a scheduled job"""
    try:
        result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job.status = JobStatus.PAUSED
        await db.commit()
        
        logger.info("Job paused", job_id=job_id)
        return {"message": "Job paused successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to pause job", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause job"
        )

@router.put("/jobs/{job_id}/resume")
async def resume_job(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Resume a paused job"""
    try:
        result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job.status = JobStatus.ACTIVE
        await db.commit()
        
        logger.info("Job resumed", job_id=job_id)
        return {"message": "Job resumed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error("Failed to resume job", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume job"
        )

@router.post("/jobs/{job_id}/run-now")
async def run_job_now(
    job_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Run a scheduled job immediately"""
    try:
        result = await db.execute(select(ScrapingJob).where(ScrapingJob.id == job_id))
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Trigger the task immediately
        scheduled_scraping_task.delay(job_id)
        
        logger.info("Job triggered to run now", job_id=job_id)
        return {"message": "Job started immediately"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to run job now", job_id=job_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run job"
        ) 