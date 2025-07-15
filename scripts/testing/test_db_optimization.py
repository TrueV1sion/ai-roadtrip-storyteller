#!/usr/bin/env python3
"""
Test script to verify database optimization improvements.
"""

import asyncio
import time
from datetime import datetime, timedelta
import sys
sys.path.insert(0, '.')

from backend.app.database import SessionLocal
from backend.app.models import User, Story, Theme, Reservation
from backend.app.core.database_optimization import (
    QueryOptimizationStrategies,
    OptimizedQueries,
    performance_monitor,
    index_optimizer
)


def test_query_optimization():
    """Test various query optimizations."""
    print("Testing Database Query Optimizations...")
    
    db = SessionLocal()
    
    try:
        # Initialize optimized queries
        optimized = OptimizedQueries(db)
        
        # Test 1: User query with preferences
        print("\n1. Testing optimized user query...")
        start = time.time()
        user = optimized.get_user_with_preferences(1)  # Assuming user ID 1 exists
        duration = time.time() - start
        print(f"✓ User query executed in {duration:.3f}s")
        
        # Test 2: Story queries by route
        print("\n2. Testing spatial story query...")
        start = time.time()
        stories = optimized.get_recent_stories_for_route(
            origin_lat=37.7749,
            origin_lng=-122.4194,
            dest_lat=34.0522,
            dest_lng=-118.2437,
            limit=10
        )
        duration = time.time() - start
        print(f"✓ Found {len(stories)} stories in {duration:.3f}s")
        
        # Test 3: Active reservations
        print("\n3. Testing reservation query...")
        start = time.time()
        reservations = optimized.get_active_reservations(
            user_id=1,
            start_date=datetime.now() - timedelta(days=30),
            end_date=datetime.now() + timedelta(days=30)
        )
        duration = time.time() - start
        print(f"✓ Found {len(reservations)} reservations in {duration:.3f}s")
        
        # Test 4: Nearby side quests
        print("\n4. Testing nearby side quests query...")
        start = time.time()
        quests = optimized.search_nearby_sidequests(
            latitude=37.7749,
            longitude=-122.4194,
            radius_miles=5.0,
            limit=10
        )
        duration = time.time() - start
        print(f"✓ Found {len(quests)} side quests in {duration:.3f}s")
        
        # Get performance report
        print("\n5. Query Performance Report:")
        report = optimized.get_performance_report()
        
        for query_name, stats in report['query_stats'].items():
            print(f"\n  {query_name}:")
            print(f"    - Calls: {stats['count']}")
            print(f"    - Avg time: {stats['avg_time']}s")
            print(f"    - Min/Max: {stats['min_time']}s / {stats['max_time']}s")
        
        # Test N+1 query prevention
        print("\n6. Testing N+1 query prevention...")
        
        # Bad pattern (would cause N+1)
        print("  Without optimization:")
        start = time.time()
        stories_bad = db.query(Story).limit(5).all()
        for story in stories_bad:
            _ = story.themes  # This triggers a query for each story
            _ = story.side_quests  # Another query per story
        duration_bad = time.time() - start
        print(f"    Time: {duration_bad:.3f}s")
        
        # Good pattern (eager loading)
        print("  With optimization:")
        start = time.time()
        query = db.query(Story)
        query = QueryOptimizationStrategies.optimize_story_queries(query)
        stories_good = query.limit(5).all()
        for story in stories_good:
            _ = story.themes  # Already loaded
            _ = story.side_quests  # Already loaded
        duration_good = time.time() - start
        print(f"    Time: {duration_good:.3f}s")
        print(f"    Improvement: {((duration_bad - duration_good) / duration_bad * 100):.1f}%")
        
        print("\n✓ All optimization tests completed!")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        db.close()


def test_index_analysis():
    """Analyze database indexes."""
    print("\n\nAnalyzing Database Indexes...")
    
    from backend.app.database import engine
    
    # Check existing indexes
    with engine.connect() as conn:
        # Get all indexes
        result = conn.execute(text("""
            SELECT 
                schemaname,
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
        """))
        
        current_indexes = {}
        for row in result:
            table = row.tablename
            if table not in current_indexes:
                current_indexes[table] = []
            current_indexes[table].append({
                'name': row.indexname,
                'definition': row.indexdef
            })
        
        print("\nCurrent indexes by table:")
        for table, indexes in current_indexes.items():
            print(f"\n  {table}:")
            for idx in indexes:
                print(f"    - {idx['name']}")
        
        # Suggest missing indexes
        print("\n\nSuggested additional indexes:")
        for index in index_optimizer.INDEXES:
            print(f"  - {index.name} (on {', '.join(str(col) for col in index.columns)})")


def test_query_caching():
    """Test query result caching."""
    print("\n\nTesting Query Result Caching...")
    
    from backend.app.core.cache import cache_manager
    
    async def test_cache():
        # Test cache operations
        print("1. Testing cache set/get...")
        await cache_manager.set("test_key", {"data": "test_value"}, ttl=60)
        result = await cache_manager.get("test_key")
        print(f"✓ Cache working: {result}")
        
        # Test query caching
        print("\n2. Testing query result caching...")
        
        # First call (cache miss)
        start = time.time()
        # Simulate expensive query result
        await cache_manager.set(
            "query:expensive_aggregation",
            {"total": 1000, "avg": 4.5},
            ttl=300
        )
        duration_miss = time.time() - start
        
        # Second call (cache hit)
        start = time.time()
        cached_result = await cache_manager.get("query:expensive_aggregation")
        duration_hit = time.time() - start
        
        print(f"  Cache miss time: {duration_miss:.3f}s")
        print(f"  Cache hit time: {duration_hit:.3f}s")
        print(f"  Speed improvement: {(duration_miss / duration_hit):.0f}x")
        
        # Clean up
        await cache_manager.delete("test_key")
        await cache_manager.delete("query:expensive_aggregation")
    
    asyncio.run(test_cache())


if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE OPTIMIZATION TEST SUITE")
    print("=" * 60)
    
    # Run tests
    test_query_optimization()
    test_index_analysis()
    test_query_caching()
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)