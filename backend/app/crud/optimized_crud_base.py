from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
import time
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy.orm import Session, Query
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base
from app.core.logger import get_logger
from app.core.db_optimized import QueryOptimizer

logger = get_logger(__name__)

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDOptimizedBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Enhanced CRUD operations with optimized query patterns.
    """

    def __init__(self, model: Type[ModelType]):
        """
        Initialize with the SQLAlchemy model.
        
        Args:
            model: The SQLAlchemy model
        """
        self.model = model
        self._query_cache = {}
    
    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Get a record by ID.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Record or None if not found
        """
        start_time = time.time()
        result = db.query(self.model).filter(self.model.id == id).first()
        query_time = time.time() - start_time
        
        if query_time > 0.1:  # Log slow queries (>100ms)
            logger.warning(f"Slow get query for {self.model.__name__} ID {id}: {query_time:.4f}s")
        
        return result
    
    def get_multi(
        self, 
        db: Session, 
        *, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None
    ) -> List[ModelType]:
        """
        Get multiple records with pagination, filtering, and sorting.
        
        Args:
            db: Database session
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Dictionary of field-value pairs for filtering
            order_by: List of fields to order by (prefix with - for descending)
            
        Returns:
            List of records
        """
        query = db.query(self.model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if value is None:
                        query = query.filter(getattr(self.model, field).is_(None))
                    else:
                        query = query.filter(getattr(self.model, field) == value)
        
        # Apply sorting
        if order_by:
            for field in order_by:
                if field.startswith("-") and hasattr(self.model, field[1:]):
                    query = query.order_by(getattr(self.model, field[1:]).desc())
                elif hasattr(self.model, field):
                    query = query.order_by(getattr(self.model, field))
        
        # Optimize the query
        query = QueryOptimizer.optimize_query(query)
        
        # Apply pagination
        start_time = time.time()
        result = query.offset(skip).limit(limit).all()
        query_time = time.time() - start_time
        
        if query_time > 0.2:  # Log slow queries (>200ms)
            logger.warning(f"Slow get_multi query for {self.model.__name__}: {query_time:.4f}s")
        
        return result
    
    def get_paginated(
        self,
        db: Session,
        *,
        page: int = 1,
        page_size: int = 20,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get paginated records with metadata.
        
        Args:
            db: Database session
            page: Page number (1-indexed)
            page_size: Number of items per page
            filters: Dictionary of field-value pairs for filtering
            order_by: List of fields to order by (prefix with - for descending)
            
        Returns:
            Dictionary with items and pagination metadata
        """
        query = db.query(self.model)
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if value is None:
                        query = query.filter(getattr(self.model, field).is_(None))
                    else:
                        query = query.filter(getattr(self.model, field) == value)
        
        # Apply sorting
        if order_by:
            for field in order_by:
                if field.startswith("-") and hasattr(self.model, field[1:]):
                    query = query.order_by(getattr(self.model, field[1:]).desc())
                elif hasattr(self.model, field):
                    query = query.order_by(getattr(self.model, field))
        
        # Optimize and paginate
        query = QueryOptimizer.optimize_query(query)
        return QueryOptimizer.paginate(query, page, page_size)
    
    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Create a new record.
        
        Args:
            db: Database session
            obj_in: Input data
            
        Returns:
            Created record
        """
        obj_in_data = jsonable_encoder(obj_in)
        db_obj = self.model(**obj_in_data)
        
        start_time = time.time()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        query_time = time.time() - start_time
        
        if query_time > 0.2:
            logger.warning(f"Slow create operation for {self.model.__name__}: {query_time:.4f}s")
        
        return db_obj
    
    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> ModelType:
        """
        Update a record.
        
        Args:
            db: Database session
            db_obj: Database object to update
            obj_in: Update data
            
        Returns:
            Updated record
        """
        obj_data = jsonable_encoder(db_obj)
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.dict(exclude_unset=True)
            
        for field in obj_data:
            if field in update_data:
                setattr(db_obj, field, update_data[field])
        
        start_time = time.time()
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        query_time = time.time() - start_time
        
        if query_time > 0.2:
            logger.warning(f"Slow update operation for {self.model.__name__}: {query_time:.4f}s")
        
        return db_obj
    
    def remove(self, db: Session, *, id: Any) -> ModelType:
        """
        Remove a record.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            Removed record
        """
        obj = db.query(self.model).get(id)
        
        start_time = time.time()
        db.delete(obj)
        db.commit()
        query_time = time.time() - start_time
        
        if query_time > 0.2:
            logger.warning(f"Slow remove operation for {self.model.__name__}: {query_time:.4f}s")
            
        return obj
    
    def bulk_create(self, db: Session, *, objs_in: List[CreateSchemaType]) -> List[ModelType]:
        """
        Create multiple records in bulk.
        
        Args:
            db: Database session
            objs_in: List of input data
            
        Returns:
            List of created records
        """
        start_time = time.time()
        
        # Convert input objects to model instances
        db_objs = []
        for obj_in in objs_in:
            obj_in_data = jsonable_encoder(obj_in)
            db_obj = self.model(**obj_in_data)
            db_objs.append(db_obj)
        
        # Use optimized bulk insert
        try:
            # Add all objects to session
            db.add_all(db_objs)
            
            # Commit the transaction
            db.commit()
            
            # Refresh the objects to get generated IDs
            for obj in db_objs:
                db.refresh(obj)
                
            query_time = time.time() - start_time
            
            if query_time > 0.5:  # Higher threshold for bulk operations
                logger.warning(f"Slow bulk_create operation for {self.model.__name__}: {query_time:.4f}s")
                
            return db_objs
            
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error in bulk_create for {self.model.__name__}: {str(e)}")
            raise
    
    def count(self, db: Session, *, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records with optional filtering.
        
        Args:
            db: Database session
            filters: Dictionary of field-value pairs for filtering
            
        Returns:
            Record count
        """
        query = db.query(func.count(self.model.id))
        
        # Apply filters
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field):
                    if value is None:
                        query = query.filter(getattr(self.model, field).is_(None))
                    else:
                        query = query.filter(getattr(self.model, field) == value)
        
        # Get count
        start_time = time.time()
        result = query.scalar()
        query_time = time.time() - start_time
        
        if query_time > 0.2:
            logger.warning(f"Slow count operation for {self.model.__name__}: {query_time:.4f}s")
            
        return result
    
    def exists(self, db: Session, *, id: Any) -> bool:
        """
        Check if a record with given ID exists.
        
        Args:
            db: Database session
            id: Record ID
            
        Returns:
            True if exists, False otherwise
        """
        # Optimize by not fetching the entire record
        query = db.query(func.count(self.model.id)).filter(self.model.id == id)
        
        start_time = time.time()
        result = query.scalar() > 0
        query_time = time.time() - start_time
        
        if query_time > 0.1:
            logger.warning(f"Slow exists operation for {self.model.__name__}: {query_time:.4f}s")
            
        return result
    
    def get_by_field(
        self, 
        db: Session, 
        *, 
        field: str, 
        value: Any
    ) -> Optional[ModelType]:
        """
        Get a record by a specific field value.
        
        Args:
            db: Database session
            field: Field name
            value: Field value
            
        Returns:
            Record or None if not found
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field {field} does not exist on model {self.model.__name__}")
        
        query = db.query(self.model).filter(getattr(self.model, field) == value)
        query = QueryOptimizer.optimize_query(query)
        
        start_time = time.time()
        result = query.first()
        query_time = time.time() - start_time
        
        if query_time > 0.1:
            logger.warning(f"Slow get_by_field operation for {self.model.__name__}: {query_time:.4f}s")
            
        return result
    
    def get_multi_by_field(
        self, 
        db: Session, 
        *, 
        field: str, 
        value: Any,
        skip: int = 0, 
        limit: int = 100
    ) -> List[ModelType]:
        """
        Get multiple records by a specific field value.
        
        Args:
            db: Database session
            field: Field name
            value: Field value
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        if not hasattr(self.model, field):
            raise ValueError(f"Field {field} does not exist on model {self.model.__name__}")
        
        query = db.query(self.model).filter(getattr(self.model, field) == value)
        query = QueryOptimizer.optimize_query(query)
        
        start_time = time.time()
        result = query.offset(skip).limit(limit).all()
        query_time = time.time() - start_time
        
        if query_time > 0.2:
            logger.warning(f"Slow get_multi_by_field operation for {self.model.__name__}: {query_time:.4f}s")
            
        return result