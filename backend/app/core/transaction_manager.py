"""
Transaction Management System for Database Operations
Provides decorators, context managers, and utilities for safe transaction handling
"""

import asyncio
import functools
import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, List
from datetime import datetime, timedelta
import uuid

from sqlalchemy import event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import (
    IntegrityError, 
    OperationalError, 
    DataError,
    DatabaseError,
    DisconnectionError,
    InvalidRequestError
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_log,
    after_log
)

from app.core.logger import get_logger
from app.core.standardized_errors import (
    DatabaseError as CustomDatabaseError,
    DataIntegrityError,
    ConcurrencyError,
    TransactionError
)

logger = get_logger(__name__)

T = TypeVar('T')

# Retry configuration for deadlock handling
DEADLOCK_RETRY_CONFIG = {
    'stop': stop_after_attempt(3),
    'wait': wait_exponential(multiplier=0.5, min=0.5, max=2),
    'retry': retry_if_exception_type(OperationalError),
    'before': before_log(logger, logging.WARNING),
    'after': after_log(logger, logging.WARNING)
}


class TransactionManager:
    """Manages database transactions with proper error handling and retry logic."""
    
    def __init__(self):
        self.active_transactions: Dict[str, Dict[str, Any]] = {}
        self.transaction_metrics = {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'retried': 0,
            'deadlocks': 0
        }
    
    def _generate_transaction_id(self) -> str:
        """Generate unique transaction ID for tracking."""
        return f"txn_{uuid.uuid4().hex[:12]}"
    
    def _is_deadlock_error(self, error: Exception) -> bool:
        """Check if error is a deadlock error."""
        error_msg = str(error).lower()
        deadlock_indicators = [
            'deadlock detected',
            'lock wait timeout exceeded',
            'could not serialize access',
            'concurrent update'
        ]
        return any(indicator in error_msg for indicator in deadlock_indicators)
    
    def _is_integrity_error(self, error: Exception) -> bool:
        """Check if error is an integrity constraint violation."""
        if isinstance(error, IntegrityError):
            return True
        error_msg = str(error).lower()
        integrity_indicators = [
            'foreign key constraint',
            'unique constraint',
            'check constraint',
            'not null constraint',
            'duplicate key'
        ]
        return any(indicator in error_msg for indicator in integrity_indicators)
    
    @contextmanager
    def transaction(
        self, 
        session: Session, 
        isolation_level: Optional[str] = None,
        read_only: bool = False,
        nested: bool = False
    ):
        """
        Context manager for database transactions with automatic rollback.
        
        Args:
            session: SQLAlchemy session
            isolation_level: Transaction isolation level
            read_only: Whether transaction is read-only
            nested: Whether to use savepoints for nested transactions
        
        Yields:
            Session object for database operations
        """
        transaction_id = self._generate_transaction_id()
        start_time = datetime.utcnow()
        
        self.active_transactions[transaction_id] = {
            'start_time': start_time,
            'type': 'sync',
            'read_only': read_only,
            'nested': nested
        }
        
        try:
            # Set isolation level if specified
            if isolation_level:
                session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            
            # Set read-only mode if specified
            if read_only:
                session.execute(text("SET TRANSACTION READ ONLY"))
            
            # Use savepoint for nested transactions
            if nested and session.in_transaction():
                savepoint = session.begin_nested()
                try:
                    yield session
                    savepoint.commit()
                except Exception as e:
                    savepoint.rollback()
                    raise
            else:
                # Regular transaction
                yield session
                session.commit()
            
            self.transaction_metrics['successful'] += 1
            
        except Exception as e:
            session.rollback()
            self.transaction_metrics['failed'] += 1
            
            if self._is_deadlock_error(e):
                self.transaction_metrics['deadlocks'] += 1
                logger.warning(f"Deadlock detected in transaction {transaction_id}: {e}")
                raise ConcurrencyError(f"Transaction deadlock: {str(e)}")
            
            elif self._is_integrity_error(e):
                logger.error(f"Integrity error in transaction {transaction_id}: {e}")
                raise DataIntegrityError(f"Data integrity violation: {str(e)}")
            
            else:
                logger.error(f"Transaction {transaction_id} failed: {e}")
                raise TransactionError(f"Transaction failed: {str(e)}")
            
        finally:
            self.transaction_metrics['total'] += 1
            del self.active_transactions[transaction_id]
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.debug(f"Transaction {transaction_id} completed in {duration:.3f}s")
    
    @asynccontextmanager
    async def async_transaction(
        self,
        session: AsyncSession,
        isolation_level: Optional[str] = None,
        read_only: bool = False,
        nested: bool = False
    ):
        """
        Async context manager for database transactions.
        
        Args:
            session: SQLAlchemy async session
            isolation_level: Transaction isolation level
            read_only: Whether transaction is read-only
            nested: Whether to use savepoints for nested transactions
        
        Yields:
            AsyncSession object for database operations
        """
        transaction_id = self._generate_transaction_id()
        start_time = datetime.utcnow()
        
        self.active_transactions[transaction_id] = {
            'start_time': start_time,
            'type': 'async',
            'read_only': read_only,
            'nested': nested
        }
        
        try:
            # Set isolation level if specified
            if isolation_level:
                await session.execute(text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}"))
            
            # Set read-only mode if specified
            if read_only:
                await session.execute(text("SET TRANSACTION READ ONLY"))
            
            # Use savepoint for nested transactions
            if nested and session.in_transaction():
                async with session.begin_nested():
                    yield session
            else:
                # Regular transaction
                async with session.begin():
                    yield session
            
            self.transaction_metrics['successful'] += 1
            
        except Exception as e:
            await session.rollback()
            self.transaction_metrics['failed'] += 1
            
            if self._is_deadlock_error(e):
                self.transaction_metrics['deadlocks'] += 1
                logger.warning(f"Deadlock detected in transaction {transaction_id}: {e}")
                raise ConcurrencyError(f"Transaction deadlock: {str(e)}")
            
            elif self._is_integrity_error(e):
                logger.error(f"Integrity error in transaction {transaction_id}: {e}")
                raise DataIntegrityError(f"Data integrity violation: {str(e)}")
            
            else:
                logger.error(f"Transaction {transaction_id} failed: {e}")
                raise TransactionError(f"Transaction failed: {str(e)}")
            
        finally:
            self.transaction_metrics['total'] += 1
            del self.active_transactions[transaction_id]
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.debug(f"Transaction {transaction_id} completed in {duration:.3f}s")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get transaction metrics."""
        return {
            **self.transaction_metrics,
            'active_transactions': len(self.active_transactions),
            'success_rate': (
                self.transaction_metrics['successful'] / self.transaction_metrics['total']
                if self.transaction_metrics['total'] > 0 else 0
            )
        }


# Global transaction manager instance
transaction_manager = TransactionManager()


def transactional(
    isolation_level: Optional[str] = None,
    read_only: bool = False,
    nested: bool = False,
    retry_on_deadlock: bool = True
):
    """
    Decorator for transactional methods.
    
    Args:
        isolation_level: Transaction isolation level
        read_only: Whether transaction is read-only
        nested: Whether to use savepoints for nested transactions
        retry_on_deadlock: Whether to retry on deadlock errors
    
    The decorated function must have 'db' or 'session' as first parameter
    or have it injected via dependency injection.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> T:
            # Extract session from arguments
            session = None
            if args and hasattr(args[0], 'db'):
                session = args[0].db
            elif args and isinstance(args[0], Session):
                session = args[0]
            elif 'db' in kwargs:
                session = kwargs['db']
            elif 'session' in kwargs:
                session = kwargs['session']
            
            if not session:
                raise ValueError("No database session found in function arguments")
            
            # Apply retry logic for deadlocks if enabled
            if retry_on_deadlock:
                @retry(**DEADLOCK_RETRY_CONFIG)
                def execute_with_retry():
                    with transaction_manager.transaction(
                        session,
                        isolation_level=isolation_level,
                        read_only=read_only,
                        nested=nested
                    ):
                        return func(*args, **kwargs)
                
                transaction_manager.transaction_metrics['retried'] += 1
                return execute_with_retry()
            else:
                with transaction_manager.transaction(
                    session,
                    isolation_level=isolation_level,
                    read_only=read_only,
                    nested=nested
                ):
                    return func(*args, **kwargs)
        
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> T:
            # Extract session from arguments
            session = None
            if args and hasattr(args[0], 'db'):
                session = args[0].db
            elif args and isinstance(args[0], AsyncSession):
                session = args[0]
            elif 'db' in kwargs:
                session = kwargs['db']
            elif 'session' in kwargs:
                session = kwargs['session']
            
            if not session:
                raise ValueError("No database session found in function arguments")
            
            # Apply retry logic for deadlocks if enabled
            if retry_on_deadlock:
                @retry(**DEADLOCK_RETRY_CONFIG)
                async def execute_with_retry():
                    async with transaction_manager.async_transaction(
                        session,
                        isolation_level=isolation_level,
                        read_only=read_only,
                        nested=nested
                    ):
                        return await func(*args, **kwargs)
                
                transaction_manager.transaction_metrics['retried'] += 1
                return await execute_with_retry()
            else:
                async with transaction_manager.async_transaction(
                    session,
                    isolation_level=isolation_level,
                    read_only=read_only,
                    nested=nested
                ):
                    return await func(*args, **kwargs)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def bulk_transactional(
    batch_size: int = 1000,
    isolation_level: Optional[str] = None,
    on_batch_error: Optional[Callable[[Exception, List[Any]], None]] = None
):
    """
    Decorator for bulk operations with automatic batching and error handling.
    
    Args:
        batch_size: Size of each batch
        isolation_level: Transaction isolation level
        on_batch_error: Callback for handling batch errors
    
    The decorated function must accept a list of items as first argument
    after self/cls.
    """
    def decorator(func: Callable[..., None]) -> Callable[..., Dict[str, Any]]:
        @functools.wraps(func)
        def wrapper(self, items: List[Any], *args, **kwargs) -> Dict[str, Any]:
            results = {
                'total': len(items),
                'processed': 0,
                'failed': 0,
                'failed_items': []
            }
            
            # Process in batches
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                
                try:
                    with transaction_manager.transaction(
                        self.db,
                        isolation_level=isolation_level
                    ):
                        func(self, batch, *args, **kwargs)
                    
                    results['processed'] += len(batch)
                    
                except Exception as e:
                    results['failed'] += len(batch)
                    results['failed_items'].extend(batch)
                    
                    logger.error(f"Batch processing failed: {e}")
                    
                    if on_batch_error:
                        on_batch_error(e, batch)
                    else:
                        # Default behavior: continue with next batch
                        continue
            
            return results
        
        return wrapper
    
    return decorator


class TransactionValidator:
    """Validates data consistency within transactions."""
    
    @staticmethod
    def validate_foreign_keys(session: Session, model_instance: Any) -> bool:
        """
        Validate all foreign key constraints for a model instance.
        
        Args:
            session: Database session
            model_instance: SQLAlchemy model instance
        
        Returns:
            bool: True if all foreign keys are valid
        """
        from sqlalchemy.inspection import inspect
        
        mapper = inspect(model_instance.__class__)
        
        for relationship in mapper.relationships:
            if relationship.direction.name in ['MANYTOONE', 'ONETOONE']:
                # Get the foreign key value
                fk_value = getattr(model_instance, relationship.key + '_id', None)
                
                if fk_value is not None:
                    # Check if referenced record exists
                    referenced_model = relationship.mapper.class_
                    exists = session.query(
                        session.query(referenced_model).filter_by(id=fk_value).exists()
                    ).scalar()
                    
                    if not exists:
                        logger.error(
                            f"Foreign key constraint violation: "
                            f"{relationship.key}_id={fk_value} not found in {referenced_model.__name__}"
                        )
                        return False
        
        return True
    
    @staticmethod
    def validate_unique_constraints(
        session: Session, 
        model_class: Type[Any], 
        **field_values
    ) -> bool:
        """
        Validate unique constraints before insert/update.
        
        Args:
            session: Database session
            model_class: SQLAlchemy model class
            **field_values: Field values to check for uniqueness
        
        Returns:
            bool: True if unique constraints are satisfied
        """
        query = session.query(model_class)
        
        for field, value in field_values.items():
            query = query.filter(getattr(model_class, field) == value)
        
        return query.count() == 0


# Utility functions for common transaction patterns

@transactional()
def create_with_validation(session: Session, model_instance: Any) -> Any:
    """Create a model instance with validation."""
    validator = TransactionValidator()
    
    if not validator.validate_foreign_keys(session, model_instance):
        raise DataIntegrityError("Foreign key validation failed")
    
    session.add(model_instance)
    session.flush()  # Get ID without committing
    
    return model_instance


@transactional(nested=True)
def update_with_consistency_check(
    session: Session,
    model_instance: Any,
    updates: Dict[str, Any],
    consistency_check: Optional[Callable[[Any], bool]] = None
) -> Any:
    """Update a model instance with optional consistency check."""
    # Apply updates
    for field, value in updates.items():
        setattr(model_instance, field, value)
    
    # Run consistency check if provided
    if consistency_check and not consistency_check(model_instance):
        raise DataIntegrityError("Consistency check failed")
    
    session.add(model_instance)
    session.flush()
    
    return model_instance


# Event listeners for additional transaction handling

def setup_transaction_events(engine):
    """Setup SQLAlchemy event listeners for transaction monitoring."""
    
    @event.listens_for(engine, "begin")
    def receive_begin(conn):
        logger.debug(f"Transaction started on connection {id(conn)}")
    
    @event.listens_for(engine, "commit")
    def receive_commit(conn):
        logger.debug(f"Transaction committed on connection {id(conn)}")
    
    @event.listens_for(engine, "rollback")
    def receive_rollback(conn):
        logger.warning(f"Transaction rolled back on connection {id(conn)}")