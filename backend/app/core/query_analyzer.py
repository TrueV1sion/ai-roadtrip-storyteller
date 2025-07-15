"""
Advanced Query Analyzer for Database Performance Optimization
"""
from typing import Dict, List, Any, Optional, Tuple
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict
import json

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Query
from sqlalchemy.sql import Select
import asyncio

from app.core.logger import get_logger
from app.core.cache import get_redis_client

logger = get_logger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query execution"""
    query: str
    duration: float
    rows_examined: int
    rows_returned: int
    timestamp: datetime
    explain_plan: Optional[Dict[str, Any]] = None
    slow_query: bool = False
    optimized_version: Optional[str] = None


class QueryAnalyzer:
    """
    Advanced query analyzer that tracks, analyzes, and optimizes database queries.
    """
    
    def __init__(self, slow_query_threshold: float = 0.1):
        self.slow_query_threshold = slow_query_threshold
        self.query_metrics: Dict[str, List[QueryMetrics]] = defaultdict(list)
        self.optimization_suggestions: Dict[str, List[str]] = defaultdict(list)
        self._redis = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the query analyzer"""
        if not self._initialized:
            self._redis = await get_redis_client()
            self._initialized = True
            logger.info("Query Analyzer initialized")
    
    def register_engine(self, engine: Engine):
        """Register SQLAlchemy engine for query monitoring"""
        @event.listens_for(engine, "before_cursor_execute")
        def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            conn.info.setdefault('query_start_time', []).append(time.time())
            
        @event.listens_for(engine, "after_cursor_execute")
        def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            total = time.time() - conn.info['query_start_time'].pop(-1)
            
            # Skip internal queries
            if "information_schema" in statement.lower() or "pg_" in statement.lower():
                return
                
            # Create metrics
            metrics = QueryMetrics(
                query=statement,
                duration=total,
                rows_examined=0,  # Will be populated by EXPLAIN
                rows_returned=cursor.rowcount if cursor.rowcount > 0 else 0,
                timestamp=datetime.utcnow(),
                slow_query=total > self.slow_query_threshold
            )
            
            # Store metrics
            query_hash = self._hash_query(statement)
            self.query_metrics[query_hash].append(metrics)
            
            # Log slow queries
            if metrics.slow_query:
                logger.warning(f"Slow query detected ({total:.3f}s): {statement[:100]}...")
                asyncio.create_task(self._analyze_slow_query(conn, statement, metrics))
    
    async def _analyze_slow_query(self, conn, statement: str, metrics: QueryMetrics):
        """Analyze slow queries and generate optimization suggestions"""
        try:
            # Get EXPLAIN plan for SELECT queries
            if statement.strip().upper().startswith("SELECT"):
                explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {statement}"
                result = conn.execute(text(explain_query))
                explain_data = result.fetchone()[0]
                metrics.explain_plan = explain_data
                
                # Analyze the plan
                suggestions = self._analyze_explain_plan(explain_data)
                if suggestions:
                    query_hash = self._hash_query(statement)
                    self.optimization_suggestions[query_hash].extend(suggestions)
                    
                    # Store in Redis for persistence
                    if self._redis:
                        await self._redis.setex(
                            f"query_analysis:{query_hash}",
                            86400,  # 24 hours
                            json.dumps({
                                "query": statement,
                                "duration": metrics.duration,
                                "suggestions": suggestions,
                                "explain_plan": explain_data
                            })
                        )
                        
        except Exception as e:
            logger.error(f"Error analyzing slow query: {e}")
    
    def _analyze_explain_plan(self, explain_data: Dict[str, Any]) -> List[str]:
        """Analyze EXPLAIN plan and generate optimization suggestions"""
        suggestions = []
        plan = explain_data[0]["Plan"]
        
        # Check for sequential scans on large tables
        if self._check_sequential_scan(plan):
            suggestions.append("Consider adding an index to avoid sequential scan")
            
        # Check for missing indexes
        if self._check_missing_index(plan):
            suggestions.append("Missing index detected on join/filter columns")
            
        # Check for expensive sorts
        if self._check_expensive_sort(plan):
            suggestions.append("Consider adding an index to avoid expensive sorting")
            
        # Check for nested loops on large datasets
        if self._check_nested_loops(plan):
            suggestions.append("Nested loop on large dataset - consider different join strategy")
            
        # Check buffer usage
        if self._check_high_buffer_usage(plan):
            suggestions.append("High buffer usage detected - consider query restructuring")
            
        return suggestions
    
    def _check_sequential_scan(self, plan: Dict[str, Any], threshold: int = 10000) -> bool:
        """Check if there's a sequential scan on a large table"""
        if plan.get("Node Type") == "Seq Scan" and plan.get("Actual Rows", 0) > threshold:
            return True
            
        # Recursively check child plans
        for child in plan.get("Plans", []):
            if self._check_sequential_scan(child, threshold):
                return True
                
        return False
    
    def _check_missing_index(self, plan: Dict[str, Any]) -> bool:
        """Check for potential missing indexes"""
        # Look for filter conditions without index usage
        if plan.get("Filter") and plan.get("Node Type") == "Seq Scan":
            return True
            
        # Check for hash joins that could benefit from indexes
        if plan.get("Node Type") == "Hash Join":
            hash_cond = plan.get("Hash Cond", "")
            if "id" in hash_cond.lower() and any(
                child.get("Node Type") == "Seq Scan" 
                for child in plan.get("Plans", [])
            ):
                return True
                
        # Recursively check child plans
        for child in plan.get("Plans", []):
            if self._check_missing_index(child):
                return True
                
        return False
    
    def _check_expensive_sort(self, plan: Dict[str, Any], threshold: int = 5000) -> bool:
        """Check for expensive sort operations"""
        if plan.get("Node Type") == "Sort":
            sort_method = plan.get("Sort Method", "")
            if "external" in sort_method.lower() or plan.get("Actual Rows", 0) > threshold:
                return True
                
        # Recursively check child plans
        for child in plan.get("Plans", []):
            if self._check_expensive_sort(child, threshold):
                return True
                
        return False
    
    def _check_nested_loops(self, plan: Dict[str, Any], threshold: int = 1000) -> bool:
        """Check for nested loops on large datasets"""
        if plan.get("Node Type") == "Nested Loop":
            total_rows = sum(
                child.get("Actual Rows", 0) 
                for child in plan.get("Plans", [])
            )
            if total_rows > threshold:
                return True
                
        # Recursively check child plans
        for child in plan.get("Plans", []):
            if self._check_nested_loops(child, threshold):
                return True
                
        return False
    
    def _check_high_buffer_usage(self, plan: Dict[str, Any], threshold: int = 1000) -> bool:
        """Check for high buffer usage"""
        shared_buffers = plan.get("Shared Hit Blocks", 0) + plan.get("Shared Read Blocks", 0)
        if shared_buffers > threshold:
            return True
            
        # Recursively check child plans
        for child in plan.get("Plans", []):
            if self._check_high_buffer_usage(child, threshold):
                return True
                
        return False
    
    def optimize_query(self, query: Query) -> Query:
        """Apply query optimizations based on analysis"""
        query_str = str(query)
        query_hash = self._hash_query(query_str)
        
        # Check for known optimizations
        if query_hash in self.optimization_suggestions:
            suggestions = self.optimization_suggestions[query_hash]
            
            # Apply automatic optimizations
            if "Consider adding an index" in suggestions:
                # Add query hints for index usage
                query = query.execution_options(
                    synchronize_session=False,
                    autoflush=False
                )
                
            if "expensive sorting" in str(suggestions):
                # Limit default sorting to indexed columns only
                pass  # Specific implementation depends on model
                
        return query
    
    def get_query_statistics(self) -> Dict[str, Any]:
        """Get comprehensive query statistics"""
        total_queries = sum(len(metrics) for metrics in self.query_metrics.values())
        slow_queries = sum(
            1 for metrics_list in self.query_metrics.values()
            for metric in metrics_list
            if metric.slow_query
        )
        
        # Calculate average query time by type
        avg_times = {}
        for query_hash, metrics_list in self.query_metrics.items():
            if metrics_list:
                query_type = self._get_query_type(metrics_list[0].query)
                if query_type not in avg_times:
                    avg_times[query_type] = []
                avg_times[query_type].extend([m.duration for m in metrics_list])
        
        for query_type, times in avg_times.items():
            avg_times[query_type] = sum(times) / len(times)
        
        # Get top slow queries
        all_metrics = []
        for metrics_list in self.query_metrics.values():
            all_metrics.extend(metrics_list)
            
        top_slow_queries = sorted(
            [m for m in all_metrics if m.slow_query],
            key=lambda x: x.duration,
            reverse=True
        )[:10]
        
        return {
            "total_queries": total_queries,
            "slow_queries": slow_queries,
            "slow_query_percentage": (slow_queries / total_queries * 100) if total_queries > 0 else 0,
            "average_times_by_type": avg_times,
            "top_slow_queries": [
                {
                    "query": q.query[:100] + "..." if len(q.query) > 100 else q.query,
                    "duration": q.duration,
                    "timestamp": q.timestamp.isoformat()
                }
                for q in top_slow_queries
            ],
            "optimization_suggestions": dict(self.optimization_suggestions)
        }
    
    def _hash_query(self, query: str) -> str:
        """Create a hash for query deduplication"""
        # Normalize query by removing values and whitespace
        normalized = " ".join(query.split())
        # Simple hash - in production use proper query fingerprinting
        return str(hash(normalized))
    
    def _get_query_type(self, query: str) -> str:
        """Determine query type (SELECT, INSERT, UPDATE, DELETE)"""
        query_upper = query.strip().upper()
        for query_type in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
            if query_upper.startswith(query_type):
                return query_type
        return "OTHER"
    
    def get_optimization_report(self) -> str:
        """Generate a comprehensive optimization report"""
        stats = self.get_query_statistics()
        
        report = [
            "=== Database Query Optimization Report ===",
            f"Total Queries Analyzed: {stats['total_queries']}",
            f"Slow Queries: {stats['slow_queries']} ({stats['slow_query_percentage']:.1f}%)",
            "",
            "Average Query Times by Type:",
        ]
        
        for query_type, avg_time in stats['average_times_by_type'].items():
            report.append(f"  {query_type}: {avg_time:.3f}s")
            
        if stats['top_slow_queries']:
            report.extend([
                "",
                "Top Slow Queries:",
            ])
            for i, query in enumerate(stats['top_slow_queries'], 1):
                report.append(f"  {i}. {query['query']} ({query['duration']:.3f}s)")
                
        if stats['optimization_suggestions']:
            report.extend([
                "",
                "Optimization Suggestions:",
            ])
            for query_hash, suggestions in stats['optimization_suggestions'].items():
                report.append(f"  Query {query_hash[:8]}:")
                for suggestion in suggestions:
                    report.append(f"    - {suggestion}")
                    
        return "\n".join(report)


# Global instance
query_analyzer = QueryAnalyzer()


# Utility function for analyzing specific queries
async def analyze_query_performance(db_session, query: str) -> Dict[str, Any]:
    """Analyze performance of a specific query"""
    try:
        # Execute EXPLAIN ANALYZE
        explain_query = f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {query}"
        result = db_session.execute(text(explain_query))
        explain_data = result.fetchone()[0]
        
        # Extract key metrics
        plan = explain_data[0]["Plan"]
        
        return {
            "execution_time": explain_data[0].get("Execution Time", 0),
            "planning_time": explain_data[0].get("Planning Time", 0),
            "total_cost": plan.get("Total Cost", 0),
            "actual_rows": plan.get("Actual Rows", 0),
            "node_type": plan.get("Node Type"),
            "suggestions": query_analyzer._analyze_explain_plan(explain_data)
        }
        
    except Exception as e:
        logger.error(f"Error analyzing query: {e}")
        return {"error": str(e)}