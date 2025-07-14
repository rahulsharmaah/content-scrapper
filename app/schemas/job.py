from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.job import JobFrequency, JobStatus

class ScrapingJobBase(BaseModel):
    target_url: str
    frequency: JobFrequency = JobFrequency.DAILY
    status: JobStatus = JobStatus.ACTIVE

class ScrapingJobCreate(ScrapingJobBase):
    pass

class ScrapingJobUpdate(BaseModel):
    target_url: Optional[str] = None
    frequency: Optional[JobFrequency] = None
    status: Optional[JobStatus] = None

class ScrapingJob(ScrapingJobBase):
    id: int
    last_run_at: Optional[datetime] = None
    next_run_at: Optional[datetime] = None
    celery_task_id: Optional[str] = None
    config: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True 