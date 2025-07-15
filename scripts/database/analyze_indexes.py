#!/usr/bin/env python3
"""
Analyze database indexes and query performance.
Helps identify missing indexes and unused indexes.
"""

import asyncio
import asyncpg
from datetime import datetime
from typing import List, Dict, Any
import os
from tabulate import tabulate

from backend.app.core.config import settings
from backend.app.core.logger import logger


class IndexAnalyzer:
    """Analyze database index usage and performance."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.conn = None
    
    async def connect(self):
        """Connect to database."""
        self.conn = await asyncpg.connect(self.database_url)
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            await self.conn.close()
    
    async def get_table_sizes(self) -> List[Dict[str, Any]]:
        """Get table sizes and row counts."""
        query = """
        SELECT 
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
            n_live_tup AS row_count,
            n_dead_tup AS dead_rows,
            last_vacuum,
            last_autovacuum
        FROM pg_stat_user_tables
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
        
        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]
    
    async def get_index_usage(self) -> List[Dict[str, Any]]:
        """Get index usage statistics."""
        query = """
        SELECT 
            schemaname,
            tablename,
            indexname,
            idx_scan AS index_scans,
            idx_tup_read AS tuples_read,
            idx_tup_fetch AS tuples_fetched,
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
            CASE 
                WHEN idx_scan = 0 THEN 'UNUSED'
                WHEN idx_scan < 100 THEN 'RARELY USED'
                WHEN idx_scan < 1000 THEN 'OCCASIONALLY USED'
                ELSE 'FREQUENTLY USED'
            END AS usage_category
        FROM pg_stat_user_indexes
        ORDER BY idx_scan ASC, pg_relation_size(indexrelid) DESC;
        """
        
        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]
    
    async def get_missing_indexes(self) -> List[Dict[str, Any]]:
        """Identify potentially missing indexes based on query patterns."""
        query = """
        SELECT 
            schemaname,
            tablename,
            attname AS column_name,
            n_distinct,
            correlation,
            null_frac,
            avg_width
        FROM pg_stats
        WHERE schemaname = 'public'
        AND n_distinct > 100
        AND correlation < 0.1
        AND tablename NOT IN (
            SELECT tablename 
            FROM pg_indexes 
            WHERE schemaname = 'public'
        )
        ORDER BY n_distinct DESC;
        """
        
        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]
    
    async def get_slow_queries(self, min_duration_ms: int = 100) -> List[Dict[str, Any]]:
        """Get slow queries that might benefit from indexes."""
        query = """
        SELECT 
            query,
            calls,
            total_time,
            mean_time,
            stddev_time,
            min_time,
            max_time,
            rows
        FROM pg_stat_statements
        WHERE mean_time > $1
        ORDER BY mean_time DESC
        LIMIT 20;
        """
        
        try:
            rows = await self.conn.fetch(query, min_duration_ms)
            return [dict(row) for row in rows]
        except Exception as e:
            logger.warning(f"pg_stat_statements not available: {e}")
            return []
    
    async def get_index_bloat(self) -> List[Dict[str, Any]]:
        """Identify bloated indexes that need maintenance."""
        query = """
        WITH btree_index_atts AS (
            SELECT 
                nspname, 
                indexclass.relname AS index_name, 
                indexclass.reltuples,
                indexclass.relpages, 
                tableclass.relname AS tablename,
                regexp_split_to_table(indkey::text, ' ')::smallint AS attnum,
                indexrelid
            FROM pg_index
            JOIN pg_class AS indexclass ON pg_index.indexrelid = indexclass.oid
            JOIN pg_class AS tableclass ON pg_index.indrelid = tableclass.oid
            JOIN pg_namespace ON pg_namespace.oid = indexclass.relnamespace
            WHERE pg_index.indisvalid AND indexclass.relpages > 0
        )
        SELECT
            nspname AS schemaname,
            tablename,
            index_name,
            pg_size_pretty(pg_relation_size(indexrelid)) AS index_size,
            CASE
                WHEN relpages > 0 THEN
                    round(100 * (relpages - (reltuples * 8 / 8192)) / relpages, 2)
                ELSE 0
            END AS bloat_percentage
        FROM btree_index_atts
        WHERE relpages > 10
        ORDER BY bloat_percentage DESC;
        """
        
        rows = await self.conn.fetch(query)
        return [dict(row) for row in rows]
    
    async def analyze_all(self):
        """Run all analysis queries and display results."""
        print("🔍 Database Index Analysis Report")
        print("=" * 80)
        print(f"Generated at: {datetime.now().isoformat()}")
        print(f"Database: {self.database_url.split('@')[1].split('/')[0]}")
        print()
        
        # Table sizes
        print("📊 Table Sizes")
        print("-" * 80)
        table_sizes = await self.get_table_sizes()
        if table_sizes:
            print(tabulate(
                [(t['tablename'], t['size'], t['row_count'], t['dead_rows']) 
                 for t in table_sizes[:10]],
                headers=['Table', 'Size', 'Rows', 'Dead Rows'],
                tablefmt='grid'
            ))
        print()
        
        # Index usage
        print("📈 Index Usage Statistics")
        print("-" * 80)
        index_usage = await self.get_index_usage()
        
        # Unused indexes
        unused = [idx for idx in index_usage if idx['usage_category'] == 'UNUSED']
        if unused:
            print(f"⚠️  Found {len(unused)} UNUSED indexes:")
            for idx in unused[:5]:
                print(f"  - {idx['indexname']} on {idx['tablename']} ({idx['index_size']})")
        
        # Rarely used indexes
        rarely_used = [idx for idx in index_usage if idx['usage_category'] == 'RARELY USED']
        if rarely_used:
            print(f"⚠️  Found {len(rarely_used)} RARELY USED indexes:")
            for idx in rarely_used[:5]:
                print(f"  - {idx['indexname']} on {idx['tablename']} ({idx['index_scans']} scans)")
        print()
        
        # Slow queries
        print("🐌 Slow Queries (potential index candidates)")
        print("-" * 80)
        slow_queries = await self.get_slow_queries()
        if slow_queries:
            for i, query in enumerate(slow_queries[:5], 1):
                print(f"{i}. Mean time: {query['mean_time']:.2f}ms, Calls: {query['calls']}")
                print(f"   Query: {query['query'][:100]}...")
                print()
        else:
            print("No slow queries found (pg_stat_statements may not be enabled)")
        print()
        
        # Index bloat
        print("🗑️  Index Bloat Analysis")
        print("-" * 80)
        bloated = await self.get_index_bloat()
        high_bloat = [idx for idx in bloated if idx.get('bloat_percentage', 0) > 20]
        if high_bloat:
            print(f"⚠️  Found {len(high_bloat)} indexes with >20% bloat:")
            for idx in high_bloat[:5]:
                print(f"  - {idx['index_name']} on {idx['tablename']}: "
                      f"{idx['bloat_percentage']}% bloat ({idx['index_size']})")
        print()
        
        # Recommendations
        print("💡 Recommendations")
        print("-" * 80)
        
        if unused:
            print("1. Consider dropping unused indexes to save space and improve write performance")
        
        if high_bloat:
            print("2. Reindex bloated indexes to reclaim space:")
            print("   REINDEX INDEX index_name;")
        
        if slow_queries:
            print("3. Analyze slow queries with EXPLAIN to identify missing indexes")
        
        print("\n4. Run VACUUM ANALYZE regularly to update statistics")
        print("5. Monitor pg_stat_user_tables for tables needing vacuum")


async def main():
    """Run index analysis."""
    # Use production database URL or default to development
    database_url = os.getenv("DATABASE_URL", settings.DATABASE_URL)
    
    if not database_url:
        print("❌ No database URL configured")
        return
    
    analyzer = IndexAnalyzer(database_url)
    
    try:
        await analyzer.connect()
        await analyzer.analyze_all()
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"❌ Error: {e}")
    finally:
        await analyzer.disconnect()


if __name__ == "__main__":
    asyncio.run(main())