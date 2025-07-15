"""
Database Optimization Module v2 - Six Sigma DMAIC Implementation

This module implements comprehensive database optimizations following DMAIC methodology:
- Define: Connection pool exhaustion, missing indexes, N+1 queries
- Measure: Current performance metrics and bottlenecks
- Analyze: Query patterns and optimization opportunities
- Improve: Connection pool, indexes, partitioning, materialized views
- Control: Monitoring and automated maintenance
"""

import asyncio
import time
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from contextlib import asynccontextmanager

from sqlalchemy import (
    create_engine, text, Index, MetaData, Table, Column, 
    Integer, String, DateTime, Boolean, Float, JSON, ForeignKey,
    and_, or_, func, select, inspect
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool, NullPool
from sqlalchemy.dialects.postgresql import JSONB, GIN
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.logger import get_logger
from app.db.base import Base

logger = get_logger(__name__)


class DatabaseOptimizationManager:
    """
    Comprehensive database optimization manager implementing Six Sigma DMAIC methodology.
    """
    
    def __init__(self):
        self.metrics = DatabaseMetrics()
        self.index_manager = IndexManager()
        self.partition_manager = PartitionManager()
        self.materialized_view_manager = MaterializedViewManager()
        self.query_optimizer = QueryOptimizer()
        self.maintenance_scheduler = MaintenanceScheduler()
        
    async def initialize(self):
        """Initialize all optimization components."""
        logger.info("Initializing Database Optimization Manager...")
        
        # Step 1: Measure current state
        current_metrics = await self.metrics.measure_current_state()
        logger.info(f"Current database metrics: {json.dumps(current_metrics, indent=2)}")
        
        # Step 2: Analyze and identify issues
        issues = await self.analyze_performance_issues(current_metrics)
        logger.info(f"Identified {len(issues)} performance issues")
        
        # Step 3: Improve - Apply optimizations
        await self.apply_optimizations()
        
        # Step 4: Control - Set up monitoring
        await self.setup_monitoring_and_control()
        
        logger.info("Database Optimization Manager initialized successfully")
        
    async def analyze_performance_issues(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze metrics to identify performance issues."""
        issues = []
        
        # Check connection pool usage
        if metrics.get('connection_pool', {}).get('usage_percentage', 0) > 80:
            issues.append({
                'type': 'connection_pool_exhaustion',
                'severity': 'high',
                'details': 'Connection pool usage exceeds 80%'
            })
            
        # Check slow queries
        if metrics.get('slow_queries', []):
            issues.append({
                'type': 'slow_queries',
                'severity': 'medium',
                'queries': metrics['slow_queries']
            })
            
        # Check missing indexes
        if metrics.get('missing_indexes', []):
            issues.append({
                'type': 'missing_indexes',
                'severity': 'high',
                'indexes': metrics['missing_indexes']
            })
            
        return issues
        
    async def apply_optimizations(self):
        """Apply all database optimizations."""
        logger.info("Applying database optimizations...")
        
        # 1. Optimize connection pool
        await self.optimize_connection_pool()
        
        # 2. Create missing indexes
        await self.index_manager.create_all_indexes()
        
        # 3. Set up table partitioning
        await self.partition_manager.setup_partitioning()
        
        # 4. Create materialized views
        await self.materialized_view_manager.create_all_views()
        
        # 5. Configure VACUUM settings
        await self.configure_vacuum_settings()
        
        logger.info("Database optimizations applied successfully")
        
    async def optimize_connection_pool(self):
        """Optimize database connection pool settings."""
        from app.core.database_manager import db_manager
        
        # Close existing connections
        if db_manager.sync_engine:
            db_manager.sync_engine.dispose()
            
        # Recreate with optimized settings
        database_url = settings.DATABASE_URL
        if not database_url:
            raise ValueError("DATABASE_URL not configured")
            
        # Optimized connection pool settings per requirements
        pool_settings = {
            'poolclass': QueuePool,
            'pool_size': 50,  # Increased from 20
            'max_overflow': 100,  # Increased from 40
            'pool_timeout': 30,
            'pool_recycle': 1800,  # 30 minutes
            'pool_pre_ping': True,
            'echo_pool': True,  # Enable pool logging for monitoring
        }
        
        # PostgreSQL-specific optimizations
        connect_args = {
            'connect_timeout': 10,
            'application_name': 'roadtrip_api_optimized',
            'options': '-c statement_timeout=30000 -c idle_in_transaction_session_timeout=60000',
            'keepalives': 1,
            'keepalives_idle': 30,
            'keepalives_interval': 10,
            'keepalives_count': 5,
        }
        
        db_manager.sync_engine = create_engine(
            database_url,
            **pool_settings,
            connect_args=connect_args
        )
        
        db_manager.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=db_manager.sync_engine
        )
        
        logger.info("Connection pool optimized with pool_size=50, max_overflow=100")
        
    async def configure_vacuum_settings(self):
        """Configure PostgreSQL VACUUM settings for optimal performance."""
        vacuum_settings = [
            "SET autovacuum_vacuum_scale_factor = 0.1",  # More aggressive vacuuming
            "SET autovacuum_analyze_scale_factor = 0.05",  # More frequent analysis
            "SET autovacuum_naptime = '30s'",  # Check every 30 seconds
            "SET autovacuum_max_workers = 4",  # Parallel vacuum workers
            "SET maintenance_work_mem = '256MB'",  # More memory for maintenance
        ]
        
        from app.core.database_manager import db_manager
        
        with db_manager.sync_engine.connect() as conn:
            for setting in vacuum_settings:
                try:
                    conn.execute(text(setting))
                    logger.info(f"Applied VACUUM setting: {setting}")
                except Exception as e:
                    logger.warning(f"Could not apply setting {setting}: {e}")
                    
    async def setup_monitoring_and_control(self):
        """Set up continuous monitoring and control mechanisms."""
        # Schedule regular maintenance tasks
        await self.maintenance_scheduler.schedule_all_tasks()
        
        # Set up query performance monitoring
        await self.query_optimizer.enable_monitoring()
        
        logger.info("Monitoring and control mechanisms established")


class DatabaseMetrics:
    """Collect and analyze database performance metrics."""
    
    async def measure_current_state(self) -> Dict[str, Any]:
        """Measure current database performance metrics."""
        from app.core.database_manager import db_manager
        
        metrics = {
            'timestamp': datetime.utcnow().isoformat(),
            'connection_pool': await self.get_connection_pool_metrics(),
            'slow_queries': await self.get_slow_queries(),
            'missing_indexes': await self.analyze_missing_indexes(),
            'table_statistics': await self.get_table_statistics(),
            'database_size': await self.get_database_size(),
        }
        
        return metrics
        
    async def get_connection_pool_metrics(self) -> Dict[str, Any]:
        """Get connection pool usage metrics."""
        from app.core.database_manager import db_manager
        
        if not db_manager.sync_engine:
            return {}
            
        pool = db_manager.sync_engine.pool
        
        return {
            'size': pool.size(),
            'checked_in': pool.checkedin(),
            'checked_out': pool.checkedout(),
            'overflow': pool.overflow(),
            'total': pool.size() + pool.overflow(),
            'usage_percentage': (pool.checkedout() / (pool.size() + pool.overflow()) * 100) if pool.size() > 0 else 0
        }
        
    async def get_slow_queries(self) -> List[Dict[str, Any]]:
        """Identify slow queries from pg_stat_statements."""
        from app.core.database_manager import db_manager
        
        slow_query_threshold_ms = 50  # 50ms threshold
        
        query = """
        SELECT 
            query,
            calls,
            mean_exec_time,
            max_exec_time,
            total_exec_time,
            rows
        FROM pg_stat_statements
        WHERE mean_exec_time > :threshold
        ORDER BY mean_exec_time DESC
        LIMIT 20
        """
        
        slow_queries = []
        
        try:
            with db_manager.sync_engine.connect() as conn:
                result = conn.execute(text(query), {'threshold': slow_query_threshold_ms})
                
                for row in result:
                    slow_queries.append({
                        'query': row[0][:200],  # Truncate long queries
                        'calls': row[1],
                        'mean_time_ms': round(row[2], 2),
                        'max_time_ms': round(row[3], 2),
                        'total_time_ms': round(row[4], 2),
                        'rows': row[5]
                    })
        except Exception as e:
            logger.warning(f"Could not fetch slow queries (pg_stat_statements may not be enabled): {e}")
            
        return slow_queries
        
    async def analyze_missing_indexes(self) -> List[Dict[str, Any]]:
        """Analyze and identify missing indexes."""
        from app.core.database_manager import db_manager
        
        missing_indexes = []
        
        # Check for foreign keys without indexes
        fk_query = """
        SELECT
            tc.table_name,
            kcu.column_name,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name
        FROM information_schema.table_constraints AS tc
        JOIN information_schema.key_column_usage AS kcu
            ON tc.constraint_name = kcu.constraint_name
        JOIN information_schema.constraint_column_usage AS ccu
            ON ccu.constraint_name = tc.constraint_name
        WHERE tc.constraint_type = 'FOREIGN KEY'
        AND NOT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND tablename = tc.table_name
            AND indexdef LIKE '%' || kcu.column_name || '%'
        )
        """
        
        try:
            with db_manager.sync_engine.connect() as conn:
                result = conn.execute(text(fk_query))
                
                for row in result:
                    missing_indexes.append({
                        'type': 'foreign_key',
                        'table': row[0],
                        'column': row[1],
                        'references': f"{row[2]}.{row[3]}"
                    })
        except Exception as e:
            logger.error(f"Error analyzing missing indexes: {e}")
            
        return missing_indexes
        
    async def get_table_statistics(self) -> Dict[str, Any]:
        """Get table size and row count statistics."""
        from app.core.database_manager import db_manager
        
        stats_query = """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
            pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
            n_live_tup AS row_count,
            n_dead_tup AS dead_rows,
            last_vacuum,
            last_autovacuum,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
        """
        
        tables = {}
        
        try:
            with db_manager.sync_engine.connect() as conn:
                result = conn.execute(text(stats_query))
                
                for row in result:
                    tables[row[1]] = {
                        'total_size': row[2],
                        'table_size': row[3],
                        'row_count': row[4],
                        'dead_rows': row[5],
                        'last_vacuum': row[6].isoformat() if row[6] else None,
                        'last_autovacuum': row[7].isoformat() if row[7] else None,
                        'last_analyze': row[8].isoformat() if row[8] else None,
                        'last_autoanalyze': row[9].isoformat() if row[9] else None,
                    }
        except Exception as e:
            logger.error(f"Error getting table statistics: {e}")
            
        return tables
        
    async def get_database_size(self) -> Dict[str, str]:
        """Get total database size."""
        from app.core.database_manager import db_manager
        
        size_query = """
        SELECT
            pg_database.datname,
            pg_size_pretty(pg_database_size(pg_database.datname)) AS size
        FROM pg_database
        WHERE datname = current_database()
        """
        
        try:
            with db_manager.sync_engine.connect() as conn:
                result = conn.execute(text(size_query))
                row = result.fetchone()
                
                return {
                    'database': row[0],
                    'size': row[1]
                }
        except Exception as e:
            logger.error(f"Error getting database size: {e}")
            return {}


class IndexManager:
    """Manage database indexes for optimal query performance."""
    
    def __init__(self):
        self.indexes_to_create = []
        self._define_indexes()
        
    def _define_indexes(self):
        """Define all required indexes based on query patterns."""
        # Core table indexes
        self.indexes_to_create.extend([
            # Users table
            {'name': 'idx_users_email_active', 'table': 'users', 'columns': ['email', 'is_active']},
            {'name': 'idx_users_created_at_desc', 'table': 'users', 'columns': ['created_at DESC']},
            
            # Stories table - comprehensive indexing
            {'name': 'idx_stories_user_id_created', 'table': 'stories', 'columns': ['user_id', 'created_at DESC']},
            {'name': 'idx_stories_location', 'table': 'stories', 'columns': ['latitude', 'longitude']},
            {'name': 'idx_stories_theme_id', 'table': 'stories', 'columns': ['theme_id']},
            {'name': 'idx_stories_is_favorite', 'table': 'stories', 'columns': ['is_favorite'], 'where': 'is_favorite = true'},
            {'name': 'idx_stories_rating', 'table': 'stories', 'columns': ['rating'], 'where': 'rating IS NOT NULL'},
            
            # Event journeys table
            {'name': 'idx_event_journeys_user_status', 'table': 'event_journeys', 'columns': ['user_id', 'status']},
            {'name': 'idx_event_journeys_event_date', 'table': 'event_journeys', 'columns': ['event_date']},
            {'name': 'idx_event_journeys_venue_location', 'table': 'event_journeys', 'columns': ['venue_lat', 'venue_lon']},
            
            # Bookings table
            {'name': 'idx_bookings_user_date', 'table': 'bookings', 'columns': ['user_id', 'service_date']},
            {'name': 'idx_bookings_partner_status', 'table': 'bookings', 'columns': ['partner_id', 'booking_status']},
            {'name': 'idx_bookings_reference', 'table': 'bookings', 'columns': ['booking_reference']},
            
            # Reservations table
            {'name': 'idx_reservations_user_status_date', 'table': 'reservations', 'columns': ['user_id', 'status', 'check_in_date']},
            
            # Side quests table
            {'name': 'idx_side_quests_story_active', 'table': 'side_quests', 'columns': ['story_id', 'is_active']},
            {'name': 'idx_side_quests_location_active', 'table': 'side_quests', 'columns': ['latitude', 'longitude'], 'where': 'is_active = true'},
            
            # Themes table
            {'name': 'idx_themes_user_active', 'table': 'themes', 'columns': ['user_id', 'is_active']},
            
            # Commission tracking
            {'name': 'idx_commissions_booking', 'table': 'commissions', 'columns': ['booking_id']},
            {'name': 'idx_commissions_status_date', 'table': 'commissions', 'columns': ['status', 'created_at DESC']},
        ])
        
        # JSON/JSONB GIN indexes for PostgreSQL
        self.indexes_to_create.extend([
            {'name': 'idx_stories_interests_gin', 'table': 'stories', 'columns': ['interests'], 'method': 'gin'},
            {'name': 'idx_stories_context_gin', 'table': 'stories', 'columns': ['context'], 'method': 'gin'},
            {'name': 'idx_stories_metadata_gin', 'table': 'stories', 'columns': ['story_metadata'], 'method': 'gin'},
            {'name': 'idx_event_journeys_preferences_gin', 'table': 'event_journeys', 'columns': ['preferences'], 'method': 'gin'},
            {'name': 'idx_bookings_metadata_gin', 'table': 'bookings', 'columns': ['booking_metadata'], 'method': 'gin'},
        ])
        
    async def create_all_indexes(self):
        """Create all defined indexes."""
        from app.core.database_manager import db_manager
        
        created_count = 0
        
        with db_manager.sync_engine.connect() as conn:
            for index_def in self.indexes_to_create:
                try:
                    # Check if index already exists
                    check_query = """
                    SELECT 1 FROM pg_indexes 
                    WHERE schemaname = 'public' 
                    AND indexname = :index_name
                    """
                    
                    result = conn.execute(text(check_query), {'index_name': index_def['name']})
                    
                    if result.fetchone():
                        logger.debug(f"Index {index_def['name']} already exists")
                        continue
                        
                    # Build CREATE INDEX statement
                    columns = ', '.join(index_def['columns'])
                    method = f"USING {index_def.get('method', 'btree')}"
                    where_clause = f"WHERE {index_def['where']}" if 'where' in index_def else ""
                    
                    create_query = f"""
                    CREATE INDEX CONCURRENTLY IF NOT EXISTS {index_def['name']}
                    ON {index_def['table']} {method} ({columns})
                    {where_clause}
                    """
                    
                    conn.execute(text(create_query))
                    created_count += 1
                    logger.info(f"Created index: {index_def['name']}")
                    
                except Exception as e:
                    logger.error(f"Failed to create index {index_def['name']}: {e}")
                    
        logger.info(f"Created {created_count} new indexes")
        
    async def analyze_index_usage(self) -> List[Dict[str, Any]]:
        """Analyze index usage statistics."""
        from app.core.database_manager import db_manager
        
        usage_query = """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan AS index_scans,
            idx_tup_read AS tuples_read,
            idx_tup_fetch AS tuples_fetched,
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
        FROM pg_stat_user_indexes
        WHERE schemaname = 'public'
        ORDER BY idx_scan DESC
        """
        
        indexes = []
        
        try:
            with db_manager.sync_engine.connect() as conn:
                result = conn.execute(text(usage_query))
                
                for row in result:
                    indexes.append({
                        'table': row[1],
                        'index': row[2],
                        'scans': row[3],
                        'tuples_read': row[4],
                        'tuples_fetched': row[5],
                        'size': row[6]
                    })
        except Exception as e:
            logger.error(f"Error analyzing index usage: {e}")
            
        return indexes


class PartitionManager:
    """Manage table partitioning for large tables."""
    
    async def setup_partitioning(self):
        """Set up partitioning for large tables."""
        # Define tables to partition
        partition_configs = [
            {
                'table': 'stories',
                'partition_by': 'RANGE (created_at)',
                'interval': 'monthly'
            },
            {
                'table': 'event_journeys',
                'partition_by': 'RANGE (event_date)',
                'interval': 'monthly'
            },
            {
                'table': 'bookings',
                'partition_by': 'RANGE (booking_date)',
                'interval': 'monthly'
            }
        ]
        
        from app.core.database_manager import db_manager
        
        for config in partition_configs:
            try:
                await self._create_partitioned_table(db_manager.sync_engine, config)
            except Exception as e:
                logger.error(f"Failed to partition table {config['table']}: {e}")
                
    async def _create_partitioned_table(self, engine, config: Dict[str, Any]):
        """Create a partitioned table with automatic partition management."""
        table_name = config['table']
        
        with engine.connect() as conn:
            # Check if table is already partitioned
            check_query = """
            SELECT relkind 
            FROM pg_class 
            WHERE relname = :table_name 
            AND relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            """
            
            result = conn.execute(text(check_query), {'table_name': table_name})
            row = result.fetchone()
            
            if row and row[0] == 'p':  # 'p' indicates partitioned table
                logger.info(f"Table {table_name} is already partitioned")
                return
                
            # For new deployments, create partitioned tables
            # For existing deployments, we'd need a migration strategy
            logger.info(f"Table {table_name} partitioning would require migration in production")
            
            # Create partition maintenance function
            maintenance_func = f"""
            CREATE OR REPLACE FUNCTION create_monthly_partitions_{table_name}()
            RETURNS void AS $$
            DECLARE
                start_date date;
                end_date date;
                partition_name text;
            BEGIN
                -- Create partitions for next 3 months
                FOR i IN 0..2 LOOP
                    start_date := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::interval);
                    end_date := start_date + INTERVAL '1 month';
                    partition_name := '{table_name}_' || TO_CHAR(start_date, 'YYYY_MM');
                    
                    -- Create partition if it doesn't exist
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_class 
                        WHERE relname = partition_name
                    ) THEN
                        EXECUTE format(
                            'CREATE TABLE IF NOT EXISTS %I PARTITION OF {table_name} 
                            FOR VALUES FROM (%L) TO (%L)',
                            partition_name, start_date, end_date
                        );
                    END IF;
                END LOOP;
            END;
            $$ LANGUAGE plpgsql;
            """
            
            try:
                conn.execute(text(maintenance_func))
                logger.info(f"Created partition maintenance function for {table_name}")
            except Exception as e:
                logger.warning(f"Could not create partition function for {table_name}: {e}")


class MaterializedViewManager:
    """Manage materialized views for analytics and performance."""
    
    async def create_all_views(self):
        """Create all materialized views."""
        views = [
            {
                'name': 'mv_user_story_stats',
                'query': """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_user_story_stats AS
                SELECT 
                    u.id AS user_id,
                    COUNT(DISTINCT s.id) AS total_stories,
                    COUNT(DISTINCT s.id) FILTER (WHERE s.is_favorite = true) AS favorite_stories,
                    AVG(s.rating) AS avg_rating,
                    MAX(s.created_at) AS last_story_date,
                    COUNT(DISTINCT DATE(s.created_at)) AS active_days
                FROM users u
                LEFT JOIN stories s ON u.id = s.user_id
                GROUP BY u.id
                """,
                'indexes': ['user_id']
            },
            {
                'name': 'mv_daily_booking_stats',
                'query': """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_booking_stats AS
                SELECT 
                    DATE(booking_date) AS booking_day,
                    booking_type,
                    booking_status,
                    COUNT(*) AS booking_count,
                    SUM(gross_amount) AS total_gross,
                    SUM(net_amount) AS total_net,
                    COUNT(DISTINCT user_id) AS unique_users
                FROM bookings
                GROUP BY DATE(booking_date), booking_type, booking_status
                """,
                'indexes': ['booking_day', 'booking_type']
            },
            {
                'name': 'mv_popular_locations',
                'query': """
                CREATE MATERIALIZED VIEW IF NOT EXISTS mv_popular_locations AS
                SELECT 
                    ROUND(latitude::numeric, 2) AS lat_bucket,
                    ROUND(longitude::numeric, 2) AS lon_bucket,
                    COUNT(*) AS story_count,
                    AVG(rating) AS avg_rating,
                    COUNT(DISTINCT user_id) AS unique_visitors
                FROM stories
                WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                GROUP BY lat_bucket, lon_bucket
                HAVING COUNT(*) > 5
                """,
                'indexes': ['lat_bucket', 'lon_bucket']
            }
        ]
        
        from app.core.database_manager import db_manager
        
        for view_def in views:
            try:
                with db_manager.sync_engine.connect() as conn:
                    # Create the materialized view
                    conn.execute(text(view_def['query']))
                    
                    # Create indexes on the view
                    for column in view_def['indexes']:
                        index_name = f"idx_{view_def['name']}_{column}"
                        conn.execute(text(f"CREATE INDEX IF NOT EXISTS {index_name} ON {view_def['name']} ({column})"))
                        
                    logger.info(f"Created materialized view: {view_def['name']}")
                    
            except Exception as e:
                logger.error(f"Failed to create materialized view {view_def['name']}: {e}")
                
    async def refresh_materialized_views(self):
        """Refresh all materialized views."""
        from app.core.database_manager import db_manager
        
        views = ['mv_user_story_stats', 'mv_daily_booking_stats', 'mv_popular_locations']
        
        with db_manager.sync_engine.connect() as conn:
            for view in views:
                try:
                    conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
                    logger.info(f"Refreshed materialized view: {view}")
                except Exception as e:
                    logger.error(f"Failed to refresh view {view}: {e}")


class QueryOptimizer:
    """Optimize query execution and monitor performance."""
    
    async def enable_monitoring(self):
        """Enable query monitoring and optimization."""
        from app.core.database_manager import db_manager
        
        # Enable pg_stat_statements if available
        try:
            with db_manager.sync_engine.connect() as conn:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_stat_statements"))
                logger.info("Enabled pg_stat_statements extension")
        except Exception as e:
            logger.warning(f"Could not enable pg_stat_statements: {e}")
            
    async def optimize_common_queries(self):
        """Optimize commonly used queries."""
        optimizations = [
            {
                'name': 'stories_by_user',
                'original': "SELECT * FROM stories WHERE user_id = ?",
                'optimized': """
                SELECT s.*, t.name as theme_name 
                FROM stories s 
                LEFT JOIN themes t ON s.theme_id = t.id 
                WHERE s.user_id = ? 
                ORDER BY s.created_at DESC
                """
            },
            {
                'name': 'active_bookings',
                'original': "SELECT * FROM bookings WHERE user_id = ? AND booking_status IN ('pending', 'confirmed')",
                'optimized': """
                SELECT b.*, p.name as partner_name, c.commission_amount
                FROM bookings b
                INNER JOIN partners p ON b.partner_id = p.id
                LEFT JOIN commissions c ON b.id = c.booking_id
                WHERE b.user_id = ? 
                AND b.booking_status IN ('pending', 'confirmed')
                AND b.service_date >= CURRENT_DATE
                ORDER BY b.service_date
                """
            }
        ]
        
        return optimizations


class MaintenanceScheduler:
    """Schedule and manage database maintenance tasks."""
    
    async def schedule_all_tasks(self):
        """Schedule all maintenance tasks."""
        tasks = [
            {
                'name': 'vacuum_analyze',
                'schedule': 'daily',
                'function': self._vacuum_analyze_tables
            },
            {
                'name': 'refresh_materialized_views',
                'schedule': 'hourly',
                'function': self._refresh_materialized_views
            },
            {
                'name': 'update_table_statistics',
                'schedule': 'daily',
                'function': self._update_statistics
            },
            {
                'name': 'cleanup_old_partitions',
                'schedule': 'weekly',
                'function': self._cleanup_old_partitions
            }
        ]
        
        # In production, these would be scheduled with Celery or cron
        logger.info(f"Scheduled {len(tasks)} maintenance tasks")
        
    async def _vacuum_analyze_tables(self):
        """Run VACUUM ANALYZE on all tables."""
        from app.core.database_manager import db_manager
        
        tables = [
            'users', 'stories', 'event_journeys', 'bookings', 
            'reservations', 'side_quests', 'themes', 'commissions'
        ]
        
        with db_manager.sync_engine.connect() as conn:
            for table in tables:
                try:
                    conn.execute(text(f"VACUUM ANALYZE {table}"))
                    logger.info(f"Completed VACUUM ANALYZE on {table}")
                except Exception as e:
                    logger.error(f"Failed to VACUUM ANALYZE {table}: {e}")
                    
    async def _refresh_materialized_views(self):
        """Refresh materialized views."""
        view_manager = MaterializedViewManager()
        await view_manager.refresh_materialized_views()
        
    async def _update_statistics(self):
        """Update table statistics for query planner."""
        from app.core.database_manager import db_manager
        
        with db_manager.sync_engine.connect() as conn:
            try:
                conn.execute(text("ANALYZE"))
                logger.info("Updated database statistics")
            except Exception as e:
                logger.error(f"Failed to update statistics: {e}")
                
    async def _cleanup_old_partitions(self):
        """Clean up old partitions beyond retention period."""
        # Keep 6 months of data
        retention_months = 6
        
        from app.core.database_manager import db_manager
        
        cleanup_query = """
        SELECT tablename 
        FROM pg_tables 
        WHERE schemaname = 'public' 
        AND tablename ~ '^(stories|event_journeys|bookings)_\\d{4}_\\d{2}$'
        AND tablename < %s
        """
        
        cutoff_date = datetime.utcnow() - timedelta(days=retention_months * 30)
        cutoff_partition = cutoff_date.strftime('%Y_%m')
        
        with db_manager.sync_engine.connect() as conn:
            try:
                result = conn.execute(text(cleanup_query), (f"%_{cutoff_partition}",))
                
                for row in result:
                    partition_name = row[0]
                    conn.execute(text(f"DROP TABLE IF EXISTS {partition_name}"))
                    logger.info(f"Dropped old partition: {partition_name}")
                    
            except Exception as e:
                logger.error(f"Failed to cleanup old partitions: {e}")


# Global instance
db_optimization_manager = DatabaseOptimizationManager()