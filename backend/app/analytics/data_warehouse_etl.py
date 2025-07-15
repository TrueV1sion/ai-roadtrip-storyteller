"""
Data Warehouse ETL Pipeline for Analytics.

This module provides ETL (Extract, Transform, Load) processes to move
data from transactional databases to the analytics data warehouse.
"""

import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

from sqlalchemy import text, create_engine
from sqlalchemy.engine import Engine

from backend.app.core.celery_app import celery_app
from backend.app.core.logger import get_logger
from backend.app.core.database_replicas import db_manager
from backend.app.core.tracing import trace_method

logger = get_logger(__name__)


@dataclass
class ETLJob:
    """Configuration for an ETL job."""
    name: str
    source_query: str
    target_table: str
    transform_func: Optional[callable] = None
    incremental_column: Optional[str] = None
    schedule: str = "daily"  # daily, hourly, realtime


class DataWarehouseETL:
    """
    ETL pipeline for moving data to analytics warehouse.
    
    Features:
    - Incremental data loading
    - Data transformation
    - Schema evolution
    - Error handling and retries
    - Performance optimization
    """
    
    def __init__(self):
        self.jobs: Dict[str, ETLJob] = {}
        self._register_etl_jobs()
    
    def _register_etl_jobs(self):
        """Register all ETL jobs."""
        
        # User dimension table
        self.register_job(ETLJob(
            name="user_dimension",
            source_query="""
                SELECT 
                    id,
                    email,
                    name,
                    created_at,
                    preferences,
                    total_journeys,
                    total_miles,
                    favorite_personality,
                    last_active_at
                FROM users
                WHERE updated_at > :last_sync
            """,
            target_table="dim_users",
            incremental_column="updated_at",
            schedule="hourly"
        ))
        
        # Journey fact table
        self.register_job(ETLJob(
            name="journey_facts",
            source_query="""
                SELECT 
                    j.id,
                    j.user_id,
                    j.origin,
                    j.destination,
                    j.theme,
                    j.distance_miles,
                    j.duration_minutes,
                    j.personality,
                    j.started_at,
                    j.completed_at,
                    COUNT(DISTINCT s.id) as story_count,
                    COUNT(DISTINCT b.id) as booking_count,
                    COALESCE(SUM(b.commission_amount), 0) as total_commission
                FROM journeys j
                LEFT JOIN stories s ON s.journey_id = j.id
                LEFT JOIN bookings b ON b.journey_id = j.id
                WHERE j.created_at > :last_sync
                GROUP BY j.id
            """,
            target_table="fact_journeys",
            incremental_column="created_at",
            schedule="hourly"
        ))
        
        # Booking analytics
        self.register_job(ETLJob(
            name="booking_analytics",
            source_query="""
                SELECT 
                    b.id,
                    b.user_id,
                    b.journey_id,
                    b.partner,
                    b.venue_id,
                    b.venue_name,
                    b.booking_date,
                    b.party_size,
                    b.total_amount,
                    b.commission_amount,
                    b.commission_rate,
                    b.status,
                    b.created_at,
                    b.confirmed_at,
                    b.cancelled_at,
                    u.acquisition_channel,
                    u.lifetime_value
                FROM bookings b
                JOIN users u ON u.id = b.user_id
                WHERE b.updated_at > :last_sync
            """,
            target_table="fact_bookings",
            incremental_column="updated_at",
            transform_func=self._transform_booking_data,
            schedule="hourly"
        ))
        
        # Revenue aggregates
        self.register_job(ETLJob(
            name="revenue_daily",
            source_query="""
                SELECT 
                    DATE_TRUNC('day', created_at) as date,
                    partner,
                    COUNT(*) as booking_count,
                    SUM(total_amount) as gross_revenue,
                    SUM(commission_amount) as commission_revenue,
                    AVG(commission_rate) as avg_commission_rate,
                    COUNT(DISTINCT user_id) as unique_users
                FROM bookings
                WHERE status = 'confirmed'
                    AND created_at >= :start_date
                    AND created_at < :end_date
                GROUP BY 1, 2
            """,
            target_table="agg_revenue_daily",
            schedule="daily"
        ))
        
        # Voice interaction analytics
        self.register_job(ETLJob(
            name="voice_analytics",
            source_query="""
                SELECT 
                    DATE_TRUNC('hour', timestamp) as hour,
                    personality,
                    COUNT(*) as interaction_count,
                    AVG(response_time_ms) as avg_response_time,
                    COUNT(DISTINCT user_id) as unique_users,
                    SUM(CASE WHEN is_safety_critical THEN 1 ELSE 0 END) as safety_overrides
                FROM voice_interactions
                WHERE timestamp > :last_sync
                GROUP BY 1, 2
            """,
            target_table="agg_voice_hourly",
            incremental_column="timestamp",
            schedule="hourly"
        ))
        
        # Event stream for real-time analytics
        self.register_job(ETLJob(
            name="event_stream",
            source_query="""
                SELECT 
                    event_id,
                    event_type,
                    aggregate_id,
                    aggregate_type,
                    event_data,
                    user_id,
                    correlation_id,
                    trace_id,
                    timestamp
                FROM events
                WHERE timestamp > :last_sync
                ORDER BY timestamp
                LIMIT 10000
            """,
            target_table="event_stream",
            incremental_column="timestamp",
            schedule="realtime"  # Every 5 minutes
        ))
    
    def register_job(self, job: ETLJob):
        """Register an ETL job."""
        self.jobs[job.name] = job
    
    @trace_method(name="etl.run_job")
    async def run_job(self, job_name: str) -> Dict[str, Any]:
        """Run a specific ETL job."""
        
        job = self.jobs.get(job_name)
        if not job:
            raise ValueError(f"ETL job '{job_name}' not found")
        
        logger.info(f"Starting ETL job: {job_name}")
        
        try:
            # Get last sync time
            last_sync = await self._get_last_sync(job_name)
            
            # Extract data from source
            extracted_data = await self._extract(job, last_sync)
            
            if not extracted_data:
                logger.info(f"No new data for job {job_name}")
                return {"status": "no_data", "rows": 0}
            
            # Transform data if needed
            if job.transform_func:
                transformed_data = await self._transform(job, extracted_data)
            else:
                transformed_data = extracted_data
            
            # Load data to warehouse
            rows_loaded = await self._load(job, transformed_data)
            
            # Update sync timestamp
            await self._update_last_sync(job_name)
            
            logger.info(f"ETL job {job_name} completed: {rows_loaded} rows")
            
            return {
                "status": "success",
                "rows": rows_loaded,
                "last_sync": last_sync,
                "new_sync": datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"ETL job {job_name} failed: {str(e)}")
            raise
    
    async def _extract(
        self, 
        job: ETLJob, 
        last_sync: datetime
    ) -> List[Dict[str, Any]]:
        """Extract data from source database."""
        
        params = {"last_sync": last_sync}
        
        # Add date parameters for aggregate queries
        if "start_date" in job.source_query:
            params["start_date"] = last_sync
            params["end_date"] = datetime.utcnow()
        
        # Use read replica for extraction
        with db_manager.read_session() as session:
            result = session.execute(
                text(job.source_query),
                params
            )
            
            # Convert to list of dicts
            columns = result.keys()
            data = [dict(zip(columns, row)) for row in result.fetchall()]
            
            return data
    
    async def _transform(
        self, 
        job: ETLJob, 
        data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Transform extracted data."""
        
        if asyncio.iscoroutinefunction(job.transform_func):
            return await job.transform_func(data)
        else:
            return job.transform_func(data)
    
    async def _load(
        self, 
        job: ETLJob, 
        data: List[Dict[str, Any]]
    ) -> int:
        """Load data into warehouse."""
        
        if not data:
            return 0
        
        # Prepare bulk insert
        columns = list(data[0].keys())
        
        # Use analytics database for loading
        with db_manager.analytics_session() as session:
            # Create temp table
            temp_table = f"temp_{job.target_table}_{int(datetime.utcnow().timestamp())}"
            
            # Create table with same structure
            session.execute(text(f"""
                CREATE TEMP TABLE {temp_table} AS 
                SELECT * FROM {job.target_table} LIMIT 0
            """))
            
            # Bulk insert into temp table
            insert_query = f"""
                INSERT INTO {temp_table} ({','.join(columns)})
                VALUES ({','.join([f':{col}' for col in columns])})
            """
            
            session.execute(text(insert_query), data)
            
            # Merge into target table (upsert)
            merge_query = f"""
                INSERT INTO {job.target_table}
                SELECT * FROM {temp_table}
                ON CONFLICT (id) DO UPDATE SET
                    {','.join([f'{col} = EXCLUDED.{col}' for col in columns if col != 'id'])}
            """
            
            result = session.execute(text(merge_query))
            session.commit()
            
            return result.rowcount
    
    async def _get_last_sync(self, job_name: str) -> datetime:
        """Get last sync timestamp for a job."""
        
        with db_manager.analytics_session() as session:
            result = session.execute(text("""
                SELECT last_sync FROM etl_job_status
                WHERE job_name = :job_name
            """), {"job_name": job_name})
            
            row = result.fetchone()
            if row:
                return row[0]
            else:
                # Default to 30 days ago for first run
                return datetime.utcnow() - timedelta(days=30)
    
    async def _update_last_sync(self, job_name: str):
        """Update last sync timestamp."""
        
        with db_manager.analytics_session() as session:
            session.execute(text("""
                INSERT INTO etl_job_status (job_name, last_sync, updated_at)
                VALUES (:job_name, :last_sync, :updated_at)
                ON CONFLICT (job_name) DO UPDATE SET
                    last_sync = :last_sync,
                    updated_at = :updated_at
            """), {
                "job_name": job_name,
                "last_sync": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            })
            session.commit()
    
    def _transform_booking_data(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform booking data for analytics."""
        
        for row in data:
            # Calculate booking lead time
            if row.get('booking_date') and row.get('created_at'):
                lead_time = (row['booking_date'] - row['created_at']).days
                row['booking_lead_days'] = lead_time
            
            # Categorize commission tier
            commission_rate = row.get('commission_rate', 0)
            if commission_rate >= 0.15:
                row['commission_tier'] = 'premium'
            elif commission_rate >= 0.10:
                row['commission_tier'] = 'standard'
            else:
                row['commission_tier'] = 'basic'
            
            # Add time-based dimensions
            if row.get('created_at'):
                row['created_hour'] = row['created_at'].hour
                row['created_dow'] = row['created_at'].weekday()
                row['created_month'] = row['created_at'].month
        
        return data


# Celery tasks for scheduled ETL
@celery_app.task(name="etl.run_hourly_jobs")
def run_hourly_etl_jobs():
    """Run all hourly ETL jobs."""
    etl = DataWarehouseETL()
    
    hourly_jobs = [
        job_name for job_name, job in etl.jobs.items()
        if job.schedule == "hourly"
    ]
    
    for job_name in hourly_jobs:
        try:
            asyncio.run(etl.run_job(job_name))
        except Exception as e:
            logger.error(f"Hourly ETL job {job_name} failed: {str(e)}")


@celery_app.task(name="etl.run_daily_jobs")
def run_daily_etl_jobs():
    """Run all daily ETL jobs."""
    etl = DataWarehouseETL()
    
    daily_jobs = [
        job_name for job_name, job in etl.jobs.items()
        if job.schedule == "daily"
    ]
    
    for job_name in daily_jobs:
        try:
            asyncio.run(etl.run_job(job_name))
        except Exception as e:
            logger.error(f"Daily ETL job {job_name} failed: {str(e)}")


@celery_app.task(name="etl.run_realtime_jobs")
def run_realtime_etl_jobs():
    """Run all realtime ETL jobs."""
    etl = DataWarehouseETL()
    
    realtime_jobs = [
        job_name for job_name, job in etl.jobs.items()
        if job.schedule == "realtime"
    ]
    
    for job_name in realtime_jobs:
        try:
            asyncio.run(etl.run_job(job_name))
        except Exception as e:
            logger.error(f"Realtime ETL job {job_name} failed: {str(e)}")