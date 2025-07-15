import pytest
from unittest.mock import MagicMock, patch
import time
from sqlalchemy.orm import Session

from app.core.db_optimized import QueryOptimizer
from app.monitoring.db_performance import DBPerformanceMonitor
from app.crud.optimized_crud_base import CRUDOptimizedBase
from app.models.story import Story


class TestQueryOptimizer:
    """Tests for the QueryOptimizer class."""
    
    def test_paginate(self):
        """Test pagination functionality."""
        # Mock query object
        query = MagicMock()
        query.count.return_value = 50
        query.offset.return_value = query
        query.limit.return_value = query
        query.all.return_value = ["result1", "result2", "result3"]
        
        # Test pagination
        result = QueryOptimizer.paginate(query, page=2, page_size=10)
        
        # Verify pagination metadata
        assert result["pagination"]["page"] == 2
        assert result["pagination"]["page_size"] == 10
        assert result["pagination"]["total_items"] == 50
        assert result["pagination"]["total_pages"] == 5
        assert result["pagination"]["has_next"] is True
        assert result["pagination"]["has_prev"] is True
        
        # Verify correct offset and limit
        query.offset.assert_called_once_with(10)  # (page-1) * page_size
        query.limit.assert_called_once_with(10)
        
        # Test with page=1
        result = QueryOptimizer.paginate(query, page=1, page_size=10)
        assert result["pagination"]["has_prev"] is False
        
        # Test with last page
        result = QueryOptimizer.paginate(query, page=5, page_size=10)
        assert result["pagination"]["has_next"] is False


class TestDBPerformanceMonitor:
    """Tests for the DBPerformanceMonitor class."""
    
    def test_track_query(self):
        """Test query tracking functionality."""
        # Clear existing stats
        DBPerformanceMonitor.clear_stats()
        
        # Track a test query
        DBPerformanceMonitor.track_query(
            "SELECT * FROM stories WHERE id = :id",
            {"id": "test-id"},
            0.5,  # 500ms execution time
            {"function": "test_function"}
        )
        
        # Get slow queries
        slow_queries = DBPerformanceMonitor.get_slow_queries(threshold=0.1)
        
        # Should have one slow query
        assert len(slow_queries) == 1
        assert slow_queries[0]["avg_execution_time"] == 0.5
        assert slow_queries[0]["call_count"] == 1
        
        # Track another execution of the same query
        DBPerformanceMonitor.track_query(
            "SELECT * FROM stories WHERE id = :id",
            {"id": "another-id"},
            0.3,  # 300ms execution time
            {"function": "test_function"}
        )
        
        # Get query stats
        stats = DBPerformanceMonitor.get_query_stats()
        
        # Check overall stats
        assert stats["total_queries_tracked"] == 2
        assert stats["unique_queries"] == 1  # Same normalized query
        assert stats["total_execution_time"] == 0.8  # 0.5 + 0.3
        assert stats["average_execution_time"] == 0.4  # (0.5 + 0.3) / 2
        
        # Clear stats
        DBPerformanceMonitor.clear_stats()
        
        # Stats should be empty
        stats = DBPerformanceMonitor.get_query_stats()
        assert stats["total_queries_tracked"] == 0


class TestCRUDOptimizedBase:
    """Tests for the CRUDOptimizedBase class."""
    
    def test_crud_methods(self):
        """Test CRUD method signatures and functionality."""
        # Create a mock session
        db = MagicMock(spec=Session)
        
        # Create a mock query result
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.return_value = [MagicMock()]
        mock_query.first.return_value = MagicMock()
        mock_query.count.return_value = 10
        
        # Mock the session query method
        db.query.return_value = mock_query
        
        # Create a CRUD instance
        crud = CRUDOptimizedBase(Story)
        
        # Test get method
        result = crud.get(db, "test-id")
        assert result is not None
        db.query.assert_called_with(Story)
        mock_query.filter.assert_called_once()
        
        # Test get_multi method
        results = crud.get_multi(db, skip=0, limit=10)
        assert len(results) == 1
        mock_query.offset.assert_called_with(0)
        mock_query.limit.assert_called_with(10)
        
        # Test get_multi with filters
        results = crud.get_multi(db, filters={"user_id": "user-123"})
        assert len(results) == 1
        
        # Test create method
        db.commit = MagicMock()
        db.refresh = MagicMock()
        db.add = MagicMock()
        
        # Mock object creation
        mock_obj = MagicMock()
        mock_json = MagicMock(return_value={})
        
        with patch("app.crud.optimized_crud_base.jsonable_encoder", mock_json):
            result = crud.create(db, obj_in=mock_obj)
            assert result is not None
            db.add.assert_called_once()
            db.commit.assert_called_once()
            db.refresh.assert_called_once()