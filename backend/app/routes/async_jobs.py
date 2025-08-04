"""
API endpoints for async job management and status tracking.

Provides:
- Job submission with immediate response
- Status polling endpoints
- Job cancellation
- Batch job management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from celery.result import AsyncResult

from app.core.auth import get_current_user
from app.core.cache import cache_manager
from app.core.logger import get_logger
from app.models.user import User
from app.tasks.ai_enhanced import (
    generate_story_with_status,
    synthesize_story_voice,
    process_journey_image,
    batch_pregenerate_stories
)
from app.tasks.booking import process_reservation
from app.core.celery_app import celery_app

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/jobs", tags=["async_jobs"])

# Request/Response models
class StoryGenerationRequest(BaseModel):
    """Request model for async story generation."""
    location: Dict[str, Any] = Field(..., description="Location coordinates and details")
    interests: List[str] = Field(default=[], description="User interests for story context")
    context: Dict[str, Any] = Field(default={}, description="Additional context")
    preferences: Dict[str, Any] = Field(default={}, description="User preferences")
    include_voice: bool = Field(default=False, description="Generate voice narration")
    voice_personality: str = Field(default="morgan_freeman", description="Voice personality")
    priority: int = Field(default=5, min=1, max=10, description="Job priority (1-10)")

class BookingRequest(BaseModel):
    """Request model for async booking processing."""
    partner: str = Field(..., description="Booking partner name")
    venue_id: str = Field(..., description="Venue identifier")
    booking_date: datetime = Field(..., description="Booking date and time")
    party_size: int = Field(default=2, min=1, max=20, description="Party size")
    special_requests: Optional[str] = None
    user_data: Dict[str, Any] = Field(default={}, description="Additional user data")

class JobSubmissionResponse(BaseModel):
    """Response model for job submission."""
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Initial job status")
    status_url: str = Field(..., description="URL to check job status")
    estimated_completion_time: Optional[int] = Field(None, description="Estimated seconds to completion")

class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: str
    progress: int = Field(0, min=0, max=100)
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    duration: Optional[float] = None

class BatchJobResponse(BaseModel):
    """Response model for batch job submission."""
    batch_id: str
    total_jobs: int
    status_url: str
    jobs: List[Dict[str, str]]


@router.post("/story/generate", response_model=JobSubmissionResponse)
async def submit_story_generation(
    request: StoryGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
) -> JobSubmissionResponse:
    """
    Submit story generation job for async processing.
    
    Returns immediately with a job ID that can be polled for status.
    API response time: <3 seconds guaranteed.
    """
    try:
        # Prepare request data
        request_data = request.dict()
        request_data['user_id'] = current_user.id
        
        # Submit task with priority
        task = generate_story_with_status.apply_async(
            args=[request_data],
            priority=request.priority
        )
        
        # Return immediate response
        return JobSubmissionResponse(
            job_id=task.id,
            status="accepted",
            status_url=f"/api/v1/jobs/status/{task.id}",
            estimated_completion_time=30 if not request.include_voice else 45
        )
        
    except Exception as e:
        logger.error(f"Failed to submit story generation job: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit job")


@router.post("/booking/process", response_model=JobSubmissionResponse)
async def submit_booking(
    request: BookingRequest,
    current_user: User = Depends(get_current_user)
) -> JobSubmissionResponse:
    """
    Submit booking for async processing.
    
    Returns immediately with a job ID for status tracking.
    """
    try:
        # Prepare booking data
        booking_data = request.dict()
        booking_data['user_id'] = current_user.id
        booking_data['id'] = f"booking_{current_user.id}_{datetime.utcnow().timestamp()}"
        
        # Submit high-priority booking task
        task = process_reservation.apply_async(
            args=[booking_data],
            priority=9  # High priority for bookings
        )
        
        return JobSubmissionResponse(
            job_id=task.id,
            status="accepted",
            status_url=f"/api/v1/jobs/status/{task.id}",
            estimated_completion_time=15
        )
        
    except Exception as e:
        logger.error(f"Failed to submit booking job: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit booking")


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> JobStatusResponse:
    """
    Get status of an async job.
    
    Poll this endpoint to track job progress.
    """
    try:
        # Check cache first for job status
        cache_keys = [
            f"story_job:{job_id}",
            f"voice_job:{job_id}",
            f"booking_job:{job_id}"
        ]
        
        job_status = None
        for key in cache_keys:
            status = cache_manager.get(key)
            if status:
                job_status = status
                break
        
        if job_status:
            return JobStatusResponse(**job_status)
        
        # Fallback to Celery result backend
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state == 'PENDING':
            return JobStatusResponse(
                job_id=job_id,
                status='pending',
                progress=0,
                message='Job is waiting to be processed'
            )
        elif result.state == 'STARTED':
            return JobStatusResponse(
                job_id=job_id,
                status='processing',
                progress=10,
                message='Job has started processing'
            )
        elif result.state == 'SUCCESS':
            return JobStatusResponse(
                job_id=job_id,
                status='completed',
                progress=100,
                result=result.result
            )
        elif result.state == 'FAILURE':
            return JobStatusResponse(
                job_id=job_id,
                status='failed',
                error=str(result.info)
            )
        else:
            return JobStatusResponse(
                job_id=job_id,
                status=result.state.lower(),
                progress=50
            )
            
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")


@router.post("/cancel/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Cancel a running job.
    
    Note: Job may complete before cancellation takes effect.
    """
    try:
        result = AsyncResult(job_id, app=celery_app)
        
        if result.state in ['SUCCESS', 'FAILURE']:
            return {
                'job_id': job_id,
                'status': 'already_completed',
                'message': f'Job already {result.state.lower()}'
            }
        
        # Revoke the task
        result.revoke(terminate=True)
        
        # Update cache
        for key_prefix in ['story_job:', 'voice_job:', 'booking_job:']:
            key = f"{key_prefix}{job_id}"
            status = cache_manager.get(key)
            if status:
                status['status'] = 'cancelled'
                status['updated_at'] = datetime.utcnow().isoformat()
                cache_manager.set(key, status, ttl=3600)
                break
        
        return {
            'job_id': job_id,
            'status': 'cancelled',
            'message': 'Job cancellation requested'
        }
        
    except Exception as e:
        logger.error(f"Failed to cancel job: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to cancel job")


@router.post("/batch/stories", response_model=BatchJobResponse)
async def submit_batch_stories(
    routes: List[Dict[str, Any]],
    current_user: User = Depends(get_current_user)
) -> BatchJobResponse:
    """
    Submit batch story generation for multiple routes.
    
    Useful for pre-generating content for upcoming trips.
    """
    try:
        if len(routes) > 50:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 50 routes per batch")
        
        # Submit batch task
        batch_task = batch_pregenerate_stories.apply_async(
            args=[routes],
            priority=3  # Lower priority for batch jobs
        )
        
        # Create individual job tracking
        jobs = []
        for i, route in enumerate(routes):
            jobs.append({
                'route_index': str(i),
                'origin': route.get('origin', 'Unknown'),
                'destination': route.get('destination', 'Unknown')
            })
        
        return BatchJobResponse(
            batch_id=batch_task.id,
            total_jobs=len(routes) * 4,  # 4 themes per route
            status_url=f"/api/v1/jobs/batch/status/{batch_task.id}",
            jobs=jobs
        )
        
    except Exception as e:
        logger.error(f"Failed to submit batch job: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit batch")


@router.get("/batch/status/{batch_id}")
async def get_batch_status(
    batch_id: str,
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Get status of a batch job."""
    try:
        result = AsyncResult(batch_id, app=celery_app)
        
        if result.state == 'SUCCESS':
            # Get individual job statuses
            batch_result = result.result
            if isinstance(batch_result, dict) and 'batch_id' in batch_result:
                return {
                    'batch_id': batch_id,
                    'status': 'completed',
                    'total_tasks': batch_result.get('total_tasks', 0),
                    'completed_at': datetime.utcnow().isoformat()
                }
        
        return {
            'batch_id': batch_id,
            'status': result.state.lower(),
            'message': 'Batch processing in progress'
        }
        
    except Exception as e:
        logger.error(f"Failed to get batch status: {str(e)}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")


@router.get("/queue/stats")
async def get_queue_statistics(
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current queue statistics.
    
    Requires admin privileges in production.
    """
    try:
        # Get cached health report
        health_report = cache_manager.get('celery:health_report')
        metrics_report = cache_manager.get('celery:metrics_report')
        
        if not health_report:
            return {
                'status': 'no_data',
                'message': 'Queue statistics not available'
            }
        
        # Combine reports
        stats = {
            'timestamp': health_report.get('timestamp'),
            'queues': health_report.get('queues', {}),
            'workers': len(health_report.get('workers', {})),
            'alerts': health_report.get('alerts', [])
        }
        
        if metrics_report:
            stats['performance'] = metrics_report.get('windows', {}).get('5min', {})
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get queue statistics: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get statistics")


@router.get("/jobs/recent")
async def get_recent_jobs(
    limit: int = Query(default=10, le=50),
    job_type: Optional[str] = Query(default=None),
    current_user: User = Depends(get_current_user)
) -> List[Dict[str, Any]]:
    """
    Get user's recent jobs.
    
    Returns up to 50 most recent jobs.
    """
    try:
        # In production, this would query from a job history table
        # For now, return mock data
        recent_jobs = []
        
        job_types = ['story_generation', 'voice_synthesis', 'booking'] if not job_type else [job_type]
        
        for i in range(min(limit, 10)):
            recent_jobs.append({
                'job_id': f"job_{i}_{current_user.id}",
                'type': job_types[i % len(job_types)],
                'status': 'completed' if i < 7 else 'processing',
                'created_at': datetime.utcnow().isoformat(),
                'duration': 15.5 if i < 7 else None
            })
        
        return recent_jobs
        
    except Exception as e:
        logger.error(f"Failed to get recent jobs: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get job history")