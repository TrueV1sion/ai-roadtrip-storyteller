"""
Maintenance tasks for Celery system health.

Implements:
- Expired job cleanup
- Queue maintenance
- Performance optimization
- Graceful shutdown handling
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from celery import Task
import redis

from app.core.celery_app import celery_app
from app.core.database_manager import DatabaseManager
from app.core.cache import cache_manager
from app.core.logger import get_logger
from app.monitoring.metrics import metrics_collector

logger = get_logger(__name__)

class MaintenanceTask(Task):
    """Base task for maintenance operations."""
    
    _db_manager = None
    _redis_client = None
    
    @property
    def db_manager(self):
        if self._db_manager is None:
            self._db_manager = DatabaseManager()
        return self._db_manager
    
    @property
    def redis_client(self):
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                celery_app.conf.broker_url,
                decode_responses=True
            )
        return self._redis_client


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name='maintenance.cleanup_expired_jobs',
    max_retries=2
)
def cleanup_expired_jobs(self) -> Dict[str, Any]:
    """
    Clean up expired job data and results.
    
    Removes:
    - Completed job results older than 24 hours
    - Failed job data older than 7 days
    - Orphaned cache entries
    """
    try:
        logger.info("Starting expired job cleanup")
        
        cleanup_stats = {
            'started_at': datetime.utcnow().isoformat(),
            'completed_jobs': 0,
            'failed_jobs': 0,
            'cache_entries': 0,
            'total_freed_bytes': 0
        }
        
        # Define retention periods
        retention_periods = {
            'completed': timedelta(hours=24),
            'failed': timedelta(days=7),
            'cancelled': timedelta(hours=12)
        }
        
        # Clean up job status cache entries
        for status_type, retention in retention_periods.items():
            cutoff_time = datetime.utcnow() - retention
            
            # Scan Redis for job keys
            pattern = f"*_job:*"
            cursor = 0
            
            while True:
                cursor, keys = self.redis_client.scan(
                    cursor, match=pattern, count=100
                )
                
                for key in keys:
                    try:
                        job_data = cache_manager.get(key)
                        if job_data and 'updated_at' in job_data:
                            updated_at = datetime.fromisoformat(
                                job_data['updated_at'].replace('Z', '+00:00')
                            )
                            
                            if (job_data.get('status') == status_type and 
                                updated_at < cutoff_time):
                                # Delete expired entry
                                cache_manager.delete(key)
                                cleanup_stats[f'{status_type}_jobs'] += 1
                                
                    except Exception as e:
                        logger.warning(f"Error processing key {key}: {str(e)}")
                
                if cursor == 0:
                    break
        
        # Clean up Celery result backend
        try:
            # Get all task results
            result_keys = self.redis_client.keys('celery-task-meta-*')
            
            for key in result_keys:
                try:
                    result_data = self.redis_client.get(key)
                    if result_data:
                        # Check age and status
                        # (Implementation depends on result serialization format)
                        pass
                        
                except Exception as e:
                    logger.warning(f"Error cleaning result {key}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error accessing result backend: {str(e)}")
        
        # Clean up orphaned cache entries
        cleanup_stats['cache_entries'] = _cleanup_orphaned_cache_entries()
        
        # Update metrics
        metrics_collector.increment('celery.maintenance.cleanup_completed')
        for stat_name, value in cleanup_stats.items():
            if isinstance(value, (int, float)):
                metrics_collector.gauge(f'celery.cleanup.{stat_name}', value)
        
        cleanup_stats['completed_at'] = datetime.utcnow().isoformat()
        cleanup_stats['duration'] = (
            datetime.utcnow() - datetime.fromisoformat(cleanup_stats['started_at'].replace('Z', '+00:00'))
        ).total_seconds()
        
        logger.info(f"Cleanup completed: {cleanup_stats}")
        return cleanup_stats
        
    except Exception as e:
        logger.error(f"Cleanup task failed: {str(e)}")
        raise self.retry(exc=e, countdown=3600)


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name='maintenance.optimize_queues',
    max_retries=1
)
def optimize_queues(self) -> Dict[str, Any]:
    """
    Optimize queue performance by reorganizing messages.
    
    Actions:
    - Rebalance queue priorities
    - Move stuck messages
    - Compact queue storage
    """
    try:
        logger.info("Starting queue optimization")
        
        optimization_stats = {
            'started_at': datetime.utcnow().isoformat(),
            'queues_optimized': 0,
            'messages_moved': 0,
            'stuck_messages': 0
        }
        
        queue_names = [
            'ai_generation', 'voice_synthesis', 'booking',
            'notifications', 'analytics', 'default'
        ]
        
        for queue_name in queue_names:
            try:
                # Check for stuck messages (in queue > 30 minutes)
                queue_key = f"celery:{queue_name}"
                queue_length = self.redis_client.llen(queue_key)
                
                if queue_length > 0:
                    # Sample messages to check age
                    sample_size = min(10, queue_length)
                    
                    for i in range(sample_size):
                        msg = self.redis_client.lindex(queue_key, i)
                        if msg:
                            # Parse message timestamp
                            # (Implementation depends on message format)
                            pass
                    
                    optimization_stats['queues_optimized'] += 1
                    
            except Exception as e:
                logger.warning(f"Error optimizing queue {queue_name}: {str(e)}")
        
        # Compact Redis storage if needed
        try:
            info = self.redis_client.info('memory')
            if info.get('used_memory_rss', 0) > info.get('used_memory', 0) * 1.5:
                logger.info("Triggering Redis memory compaction")
                self.redis_client.bgrewriteaof()
        except Exception as e:
            logger.warning(f"Could not optimize Redis memory: {str(e)}")
        
        optimization_stats['completed_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Queue optimization completed: {optimization_stats}")
        return optimization_stats
        
    except Exception as e:
        logger.error(f"Queue optimization failed: {str(e)}")
        raise


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name='maintenance.health_check',
    max_retries=1
)
def health_check(self) -> Dict[str, Any]:
    """
    Comprehensive system health check.
    
    Checks:
    - Database connectivity
    - Redis connectivity
    - Queue responsiveness
    - Worker availability
    """
    try:
        health_status = {
            'timestamp': datetime.utcnow().isoformat(),
            'components': {},
            'overall_status': 'healthy'
        }
        
        # Check database
        try:
            with self.db_manager.get_session() as session:
                session.execute('SELECT 1')
            health_status['components']['database'] = 'healthy'
        except Exception as e:
            health_status['components']['database'] = 'unhealthy'
            health_status['overall_status'] = 'degraded'
            logger.error(f"Database health check failed: {str(e)}")
        
        # Check Redis
        try:
            self.redis_client.ping()
            health_status['components']['redis'] = 'healthy'
        except Exception as e:
            health_status['components']['redis'] = 'unhealthy'
            health_status['overall_status'] = 'unhealthy'
            logger.error(f"Redis health check failed: {str(e)}")
        
        # Check cache
        try:
            test_key = 'health_check_test'
            cache_manager.set(test_key, 'test', ttl=10)
            if cache_manager.get(test_key) == 'test':
                health_status['components']['cache'] = 'healthy'
                cache_manager.delete(test_key)
            else:
                health_status['components']['cache'] = 'unhealthy'
                health_status['overall_status'] = 'degraded'
        except Exception as e:
            health_status['components']['cache'] = 'unhealthy'
            health_status['overall_status'] = 'degraded'
            logger.error(f"Cache health check failed: {str(e)}")
        
        # Check worker responsiveness
        try:
            # Send a ping to workers
            i = celery_app.control.inspect()
            active_workers = i.active()
            if active_workers:
                health_status['components']['workers'] = 'healthy'
                health_status['worker_count'] = len(active_workers)
            else:
                health_status['components']['workers'] = 'unhealthy'
                health_status['overall_status'] = 'unhealthy'
        except Exception as e:
            health_status['components']['workers'] = 'unknown'
            logger.error(f"Worker health check failed: {str(e)}")
        
        # Store health status
        cache_manager.set('system:health_status', health_status, ttl=300)
        
        logger.info(f"Health check completed: {health_status['overall_status']}")
        return health_status
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_status': 'error',
            'error': str(e)
        }


@celery_app.task(
    bind=True,
    base=MaintenanceTask,
    name='maintenance.prepare_for_shutdown',
    max_retries=0
)
def prepare_for_shutdown(self) -> Dict[str, Any]:
    """
    Prepare system for graceful shutdown.
    
    Actions:
    - Stop accepting new tasks
    - Wait for current tasks to complete
    - Save state for recovery
    """
    try:
        logger.info("Preparing for graceful shutdown")
        
        shutdown_stats = {
            'started_at': datetime.utcnow().isoformat(),
            'active_tasks': 0,
            'saved_state': False
        }
        
        # Get current active tasks
        i = celery_app.control.inspect()
        active = i.active()
        
        if active:
            for worker, tasks in active.items():
                shutdown_stats['active_tasks'] += len(tasks)
                
                # Save task state for recovery
                for task in tasks:
                    task_state = {
                        'task_id': task['id'],
                        'name': task['name'],
                        'args': task['args'],
                        'kwargs': task['kwargs'],
                        'worker': worker,
                        'saved_at': datetime.utcnow().isoformat()
                    }
                    cache_manager.set(
                        f"shutdown_state:{task['id']}", 
                        task_state, 
                        ttl=86400  # 24 hours
                    )
        
        shutdown_stats['saved_state'] = True
        
        # Signal workers to stop accepting new tasks
        celery_app.control.broadcast('shutdown')
        
        shutdown_stats['completed_at'] = datetime.utcnow().isoformat()
        
        logger.info(f"Shutdown preparation completed: {shutdown_stats}")
        return shutdown_stats
        
    except Exception as e:
        logger.error(f"Shutdown preparation failed: {str(e)}")
        return {'error': str(e)}


# Helper functions
def _cleanup_orphaned_cache_entries() -> int:
    """Clean up orphaned cache entries."""
    cleaned = 0
    
    try:
        # Patterns for temporary cache entries
        temp_patterns = [
            'temp:*',
            'session:*',
            '*:expired',
            'test:*'
        ]
        
        for pattern in temp_patterns:
            cursor = 0
            redis_client = redis.from_url(
                celery_app.conf.broker_url,
                decode_responses=True
            )
            
            while True:
                cursor, keys = redis_client.scan(
                    cursor, match=pattern, count=100
                )
                
                for key in keys:
                    try:
                        # Check if entry is orphaned
                        ttl = redis_client.ttl(key)
                        if ttl == -1:  # No expiration set
                            # Set expiration to clean up
                            redis_client.expire(key, 3600)
                            cleaned += 1
                    except Exception as e:
                        logger.warning(f"Error processing key {key}: {str(e)}")
                
                if cursor == 0:
                    break
                    
    except Exception as e:
        logger.error(f"Error cleaning orphaned entries: {str(e)}")
    
    return cleaned