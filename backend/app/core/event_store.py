"""
Event Store implementation for event sourcing pattern.

This module provides a complete audit trail of all state changes in the system,
enabling time-travel debugging, compliance, and analytics.
"""

import json
import uuid
from typing import List, Dict, Any, Optional, Type, TypeVar, Callable
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, asdict
from abc import ABC, abstractmethod

from sqlalchemy import (
    Column, String, Integer, DateTime, JSON, Index, Text, 
    BigInteger, Boolean, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.dialects.postgresql import UUID

from app.core.logger import get_logger
from app.core.database_manager import DatabaseManager
from app.middleware.correlation_id import get_correlation_id
from app.core.tracing import get_current_trace_id, trace_method

logger = get_logger(__name__)

Base = declarative_base()
T = TypeVar('T')


class EventType(str, Enum):
    """Standard event types in the system."""
    
    # User events
    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_LOGGED_IN = "user.logged_in"
    USER_LOGGED_OUT = "user.logged_out"
    
    # Journey events
    JOURNEY_STARTED = "journey.started"
    JOURNEY_UPDATED = "journey.updated"
    JOURNEY_COMPLETED = "journey.completed"
    JOURNEY_CANCELLED = "journey.cancelled"
    
    # Booking events
    BOOKING_CREATED = "booking.created"
    BOOKING_CONFIRMED = "booking.confirmed"
    BOOKING_CANCELLED = "booking.cancelled"
    BOOKING_MODIFIED = "booking.modified"
    BOOKING_COMPLETED = "booking.completed"
    
    # Story events
    STORY_GENERATED = "story.generated"
    STORY_PLAYED = "story.played"
    STORY_SKIPPED = "story.skipped"
    
    # Voice events
    VOICE_INTERACTION = "voice.interaction"
    VOICE_PERSONALITY_CHANGED = "voice.personality_changed"
    VOICE_SAFETY_OVERRIDE = "voice.safety_override"
    
    # Commission events
    COMMISSION_CALCULATED = "commission.calculated"
    COMMISSION_PAID = "commission.paid"
    COMMISSION_REVERSED = "commission.reversed"
    
    # System events
    SYSTEM_ERROR = "system.error"
    SYSTEM_MAINTENANCE = "system.maintenance"
    FEATURE_FLAG_CHANGED = "feature.flag_changed"


@dataclass
class Event:
    """Base event class."""
    
    event_id: str
    event_type: EventType
    aggregate_id: str
    aggregate_type: str
    event_data: Dict[str, Any]
    event_version: int
    correlation_id: Optional[str]
    trace_id: Optional[str]
    user_id: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
            "event_data": self.event_data,
            "event_version": self.event_version,
            "correlation_id": self.correlation_id,
            "trace_id": self.trace_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class EventEntity(Base):
    """SQLAlchemy model for event storage."""
    
    __tablename__ = 'events'
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    event_id = Column(String(36), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(String(36), nullable=False, index=True)
    aggregate_type = Column(String(100), nullable=False, index=True)
    event_data = Column(JSON, nullable=False)
    event_version = Column(Integer, nullable=False)
    correlation_id = Column(String(36), index=True)
    trace_id = Column(String(64), index=True)
    user_id = Column(String(36), index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_aggregate_lookup', 'aggregate_type', 'aggregate_id', 'event_version'),
        Index('idx_event_time', 'event_type', 'timestamp'),
        Index('idx_user_events', 'user_id', 'timestamp'),
        Index('idx_correlation', 'correlation_id', 'timestamp'),
    )


class EventStore:
    """
    Event store for persisting and retrieving events.
    
    This class provides:
    - Event persistence with guaranteed ordering
    - Event replay for aggregate reconstruction
    - Query capabilities for audit and analytics
    - Integration with tracing and correlation
    """
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self._event_handlers: Dict[EventType, List[Callable]] = {}
        self._projections: Dict[str, 'Projection'] = {}
    
    @trace_method(name="event_store.append")
    def append(
        self,
        event_type: EventType,
        aggregate_id: str,
        aggregate_type: str,
        event_data: Dict[str, Any],
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Event:
        """
        Append a new event to the store.
        
        Args:
            event_type: Type of the event
            aggregate_id: ID of the aggregate this event belongs to
            aggregate_type: Type of the aggregate (e.g., "User", "Booking")
            event_data: Event-specific data
            user_id: User who triggered the event
            metadata: Additional metadata
        
        Returns:
            The created event
        """
        with self.db_manager.get_session() as session:
            # Get next version for this aggregate
            last_event = session.query(EventEntity).filter_by(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type
            ).order_by(EventEntity.event_version.desc()).first()
            
            next_version = (last_event.event_version + 1) if last_event else 1
            
            # Create event
            event = Event(
                event_id=str(uuid.uuid4()),
                event_type=event_type,
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type,
                event_data=event_data,
                event_version=next_version,
                correlation_id=get_correlation_id(),
                trace_id=get_current_trace_id(),
                user_id=user_id,
                timestamp=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Persist event
            event_entity = EventEntity(
                event_id=event.event_id,
                event_type=event.event_type.value,
                aggregate_id=event.aggregate_id,
                aggregate_type=event.aggregate_type,
                event_data=event.event_data,
                event_version=event.event_version,
                correlation_id=event.correlation_id,
                trace_id=event.trace_id,
                user_id=event.user_id,
                timestamp=event.timestamp,
                metadata=event.metadata
            )
            
            session.add(event_entity)
            session.commit()
            
            logger.info(
                f"Event appended: {event_type.value}",
                extra={
                    "event_id": event.event_id,
                    "aggregate_id": aggregate_id,
                    "correlation_id": event.correlation_id
                }
            )
            
            # Trigger event handlers asynchronously
            self._trigger_handlers(event)
            
            # Update projections
            self._update_projections(event)
            
            return event
    
    def get_events(
        self,
        aggregate_id: str,
        aggregate_type: str,
        from_version: Optional[int] = None,
        to_version: Optional[int] = None
    ) -> List[Event]:
        """Get events for an aggregate."""
        with self.db_manager.get_session() as session:
            query = session.query(EventEntity).filter_by(
                aggregate_id=aggregate_id,
                aggregate_type=aggregate_type
            )
            
            if from_version:
                query = query.filter(EventEntity.event_version >= from_version)
            
            if to_version:
                query = query.filter(EventEntity.event_version <= to_version)
            
            query = query.order_by(EventEntity.event_version)
            
            events = []
            for entity in query.all():
                events.append(Event(
                    event_id=entity.event_id,
                    event_type=EventType(entity.event_type),
                    aggregate_id=entity.aggregate_id,
                    aggregate_type=entity.aggregate_type,
                    event_data=entity.event_data,
                    event_version=entity.event_version,
                    correlation_id=entity.correlation_id,
                    trace_id=entity.trace_id,
                    user_id=entity.user_id,
                    timestamp=entity.timestamp,
                    metadata=entity.metadata or {}
                ))
            
            return events
    
    def get_events_by_type(
        self,
        event_type: EventType,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get events by type within a time range."""
        with self.db_manager.get_session() as session:
            query = session.query(EventEntity).filter_by(
                event_type=event_type.value
            )
            
            if start_time:
                query = query.filter(EventEntity.timestamp >= start_time)
            
            if end_time:
                query = query.filter(EventEntity.timestamp <= end_time)
            
            query = query.order_by(EventEntity.timestamp.desc()).limit(limit)
            
            return [self._entity_to_event(entity) for entity in query.all()]
    
    def get_user_events(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Event]:
        """Get all events for a specific user."""
        with self.db_manager.get_session() as session:
            query = session.query(EventEntity).filter_by(user_id=user_id)
            
            if start_time:
                query = query.filter(EventEntity.timestamp >= start_time)
            
            if end_time:
                query = query.filter(EventEntity.timestamp <= end_time)
            
            query = query.order_by(EventEntity.timestamp.desc()).limit(limit)
            
            return [self._entity_to_event(entity) for entity in query.all()]
    
    def register_handler(self, event_type: EventType, handler: Callable[[Event], None]):
        """Register an event handler."""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
    
    def register_projection(self, projection: 'Projection'):
        """Register a projection to be updated on events."""
        self._projections[projection.name] = projection
    
    def _trigger_handlers(self, event: Event):
        """Trigger registered handlers for an event."""
        handlers = self._event_handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler: {str(e)}", exc_info=True)
    
    def _update_projections(self, event: Event):
        """Update registered projections."""
        for projection in self._projections.values():
            try:
                projection.handle(event)
            except Exception as e:
                logger.error(f"Error updating projection {projection.name}: {str(e)}", exc_info=True)
    
    def _entity_to_event(self, entity: EventEntity) -> Event:
        """Convert entity to event."""
        return Event(
            event_id=entity.event_id,
            event_type=EventType(entity.event_type),
            aggregate_id=entity.aggregate_id,
            aggregate_type=entity.aggregate_type,
            event_data=entity.event_data,
            event_version=entity.event_version,
            correlation_id=entity.correlation_id,
            trace_id=entity.trace_id,
            user_id=entity.user_id,
            timestamp=entity.timestamp,
            metadata=entity.metadata or {}
        )


class Projection(ABC):
    """Base class for event projections."""
    
    def __init__(self, name: str):
        self.name = name
    
    @abstractmethod
    def handle(self, event: Event):
        """Handle an event and update the projection."""
        pass


class UserJourneyProjection(Projection):
    """Example projection that tracks user journey statistics."""
    
    def __init__(self, db_manager: DatabaseManager):
        super().__init__("user_journey_stats")
        self.db_manager = db_manager
    
    def handle(self, event: Event):
        """Update user journey statistics based on events."""
        if event.event_type == EventType.JOURNEY_COMPLETED:
            # Update user's journey count and total miles
            with self.db_manager.get_session() as session:
                # This would update a materialized view or summary table
                user_id = event.user_id
                distance = event.event_data.get('distance_miles', 0)
                
                # Update user stats
                logger.info(f"Updated journey stats for user {user_id}")


class AuditLog:
    """Helper class for querying the event store for audit purposes."""
    
    def __init__(self, event_store: EventStore):
        self.event_store = event_store
    
    def get_user_activity(
        self,
        user_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get user activity for audit."""
        events = self.event_store.get_user_events(
            user_id=user_id,
            start_time=start_date,
            end_time=end_date
        )
        
        return [event.to_dict() for event in events]
    
    def get_booking_history(
        self,
        booking_id: str
    ) -> List[Dict[str, Any]]:
        """Get complete history of a booking."""
        events = self.event_store.get_events(
            aggregate_id=booking_id,
            aggregate_type="Booking"
        )
        
        return [event.to_dict() for event in events]
    
    def get_system_errors(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict[str, Any]]:
        """Get system errors for investigation."""
        events = self.event_store.get_events_by_type(
            event_type=EventType.SYSTEM_ERROR,
            start_time=start_date,
            end_time=end_date
        )
        
        return [event.to_dict() for event in events]