"""
Utilities for handling transactions in mixed sync/async environments
"""

import asyncio
from typing import Any, Callable, TypeVar, Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.transaction_manager import transaction_manager
from app.core.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


def sync_transactional_wrapper(
    sync_func: Callable[..., Any],
    session: Session,
    isolation_level: Optional[str] = None
) -> Any:
    """
    Wrap a synchronous function in a transaction.
    """
    with transaction_manager.transaction(
        session,
        isolation_level=isolation_level
    ):
        return sync_func()


async def async_to_sync_transaction(
    async_func: Callable[..., Any],
    session: Session,
    *args,
    **kwargs
) -> Any:
    """
    Execute an async function within a synchronous transaction context.
    
    This is useful when you have async external API calls but want
    transactional consistency for database operations.
    """
    # Start transaction
    trans = session.begin_nested() if session.in_transaction() else session.begin()
    
    try:
        # Run async function
        if asyncio.iscoroutinefunction(async_func):
            # Create new event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(async_func(*args, **kwargs))
        else:
            result = await async_func(*args, **kwargs)
        
        trans.commit()
        return result
        
    except Exception as e:
        trans.rollback()
        logger.error(f"Transaction failed in async_to_sync_transaction: {e}")
        raise
    

def create_reservation_with_transaction(
    db: Session,
    reservation_data: dict,
    async_provider_call: Callable,
    provider_args: tuple
) -> Any:
    """
    Special handler for reservation creation that needs both
    async API calls and transactional database operations.
    """
    with transaction_manager.transaction(db):
        # Make async provider call
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Execute async provider booking
        booking_result = loop.run_until_complete(
            async_provider_call(*provider_args)
        )
        
        # If provider booking succeeded, create database records
        # These will be committed when transaction completes
        return booking_result