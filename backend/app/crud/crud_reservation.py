from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, and_, or_
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta

from app import models, schemas
from app.core.logger import get_logger

logger = get_logger(__name__)


def get_reservation(db: Session, reservation_id: str) -> Optional[models.Reservation]:
    """Get a single reservation by its ID."""
    return db.query(models.Reservation).filter(models.Reservation.id == reservation_id).first()


def get_reservations(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None,
    user_id: Optional[str] = None,
    reservation_type: Optional[str] = None
) -> List[models.Reservation]:
    """Get a list of reservations with optional filtering."""
    query = db.query(models.Reservation)
    
    if status:
        query = query.filter(models.Reservation.status == status)
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    if reservation_type:
        query = query.filter(models.Reservation.reservation_type == reservation_type)
    
    return query.order_by(models.Reservation.created_at.desc()).offset(skip).limit(limit).all()


def get_reservations_by_user(
    db: Session, 
    user_id: str, 
    skip: int = 0, 
    limit: int = 100,
    status: Optional[str] = None
) -> List[models.Reservation]:
    """Get reservations for a specific user."""
    query = db.query(models.Reservation).filter(models.Reservation.user_id == user_id)
    
    if status:
        query = query.filter(models.Reservation.status == status)
    
    return query.order_by(models.Reservation.created_at.desc()).offset(skip).limit(limit).all()


def create_reservation(db: Session, reservation: schemas.ReservationCreate) -> models.Reservation:
    """Create a new reservation in the database."""
    try:
        reservation_data = reservation.dict(exclude_unset=True)
        db_reservation = models.Reservation(**reservation_data)
        
        db.add(db_reservation)
        db.commit()
        db.refresh(db_reservation)
        return db_reservation
    except IntegrityError as e:
        db.rollback()
        logger.error(f"Error creating reservation: {e}")
        raise ValueError("Error creating reservation")


def update_reservation(
    db: Session, 
    reservation_id: str, 
    reservation_update: schemas.ReservationUpdate
) -> Optional[models.Reservation]:
    """Update an existing reservation."""
    db_reservation = get_reservation(db, reservation_id)
    if not db_reservation:
        return None
        
    update_data = reservation_update.dict(exclude_unset=True)
    
    for field, value in update_data.items():
        setattr(db_reservation, field, value)
    
    db.commit()
    db.refresh(db_reservation)
    return db_reservation


def delete_reservation(db: Session, reservation_id: str) -> bool:
    """Delete a reservation by ID."""
    db_reservation = get_reservation(db, reservation_id)
    if db_reservation:
        db.delete(db_reservation)
        db.commit()
        return True
    return False


def update_reservation_status(
    db: Session, 
    reservation_id: str, 
    status: str,
    notes: Optional[str] = None
) -> Optional[models.Reservation]:
    """Update the status of a reservation."""
    db_reservation = get_reservation(db, reservation_id)
    if db_reservation:
        old_status = db_reservation.status
        db_reservation.status = status
        
        # Update timestamps based on status
        if status == "confirmed" and old_status != "confirmed":
            db_reservation.confirmed_at = datetime.utcnow()
        elif status == "cancelled" and old_status != "cancelled":
            db_reservation.cancelled_at = datetime.utcnow()
        elif status == "completed" and old_status != "completed":
            db_reservation.completed_at = datetime.utcnow()
        
        # Add status change notes
        if notes:
            if db_reservation.reservation_metadata:
                if "status_notes" not in db_reservation.reservation_metadata:
                    db_reservation.reservation_metadata["status_notes"] = []
                db_reservation.reservation_metadata["status_notes"].append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "old_status": old_status,
                    "new_status": status,
                    "notes": notes
                })
            else:
                db_reservation.reservation_metadata = {
                    "status_notes": [{
                        "timestamp": datetime.utcnow().isoformat(),
                        "old_status": old_status,
                        "new_status": status,
                        "notes": notes
                    }]
                }
            
        db.commit()
        db.refresh(db_reservation)
    return db_reservation


def get_reservations_by_date_range(
    db: Session,
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 50
) -> List[models.Reservation]:
    """Get reservations within a date range."""
    query = db.query(models.Reservation)
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    if start_date:
        query = query.filter(func.date(models.Reservation.reservation_date) >= start_date)
    
    if end_date:
        query = query.filter(func.date(models.Reservation.reservation_date) <= end_date)
    
    return query.order_by(models.Reservation.reservation_date.asc()).limit(limit).all()


def get_upcoming_reservations(
    db: Session, 
    user_id: Optional[str] = None,
    days_ahead: int = 7
) -> List[models.Reservation]:
    """Get upcoming reservations (within the next N days)."""
    end_date = datetime.utcnow() + timedelta(days=days_ahead)
    
    query = db.query(models.Reservation).filter(
        models.Reservation.reservation_date >= datetime.utcnow(),
        models.Reservation.reservation_date <= end_date,
        models.Reservation.status.in_(["pending", "confirmed"])
    )
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    return query.order_by(models.Reservation.reservation_date.asc()).all()


def get_active_reservations(db: Session, user_id: Optional[str] = None) -> List[models.Reservation]:
    """Get all active reservations (pending, confirmed)."""
    query = db.query(models.Reservation).filter(
        models.Reservation.status.in_(["pending", "confirmed"])
    )
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    return query.order_by(models.Reservation.reservation_date.asc()).all()


def get_reservations_by_location(
    db: Session,
    latitude: float,
    longitude: float,
    radius: float = 0.1,  # Approx 11km at equator
    limit: int = 20,
    user_id: Optional[str] = None
) -> List[models.Reservation]:
    """Get reservations near a specific location."""
    query = db.query(models.Reservation)
    
    # Filter by location if venue has coordinates
    if hasattr(models.Reservation, 'venue_latitude') and hasattr(models.Reservation, 'venue_longitude'):
        query = query.filter(
            models.Reservation.venue_latitude.between(latitude - radius, latitude + radius),
            models.Reservation.venue_longitude.between(longitude - radius, longitude + radius)
        )
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    return query.order_by(models.Reservation.reservation_date.asc()).limit(limit).all()


def get_reservation_statistics(db: Session, user_id: Optional[str] = None) -> Dict[str, Any]:
    """Get reservation statistics."""
    query = db.query(models.Reservation)
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    total_count = query.count()
    
    # Count by status
    status_counts = db.query(
        models.Reservation.status,
        func.count(models.Reservation.id).label('count')
    )
    
    if user_id:
        status_counts = status_counts.filter(models.Reservation.user_id == user_id)
    
    status_counts = status_counts.group_by(models.Reservation.status).all()
    
    # Count by reservation type
    type_counts = db.query(
        models.Reservation.reservation_type,
        func.count(models.Reservation.id).label('count')
    )
    
    if user_id:
        type_counts = type_counts.filter(models.Reservation.user_id == user_id)
    
    type_counts = type_counts.group_by(models.Reservation.reservation_type).all()
    
    # Get upcoming reservations count
    upcoming_count = query.filter(
        models.Reservation.reservation_date >= datetime.utcnow(),
        models.Reservation.status.in_(["pending", "confirmed"])
    ).count()
    
    return {
        "total_reservations": total_count,
        "status_breakdown": {status: count for status, count in status_counts},
        "type_breakdown": {res_type: count for res_type, count in type_counts},
        "upcoming_reservations": upcoming_count
    }


def search_reservations(
    db: Session,
    query: str,
    user_id: Optional[str] = None,
    limit: int = 20
) -> List[models.Reservation]:
    """Search reservations by venue name or confirmation number."""
    search_query = db.query(models.Reservation).filter(
        or_(
            models.Reservation.venue_name.ilike(f"%{query}%"),
            models.Reservation.confirmation_number.ilike(f"%{query}%")
        )
    )
    
    if user_id:
        search_query = search_query.filter(models.Reservation.user_id == user_id)
    
    return search_query.order_by(models.Reservation.reservation_date.desc()).limit(limit).all()


def get_reservations_by_type(
    db: Session, 
    reservation_type: str,
    user_id: Optional[str] = None,
    limit: int = 20
) -> List[models.Reservation]:
    """Get reservations by type (restaurant, hotel, activity, etc.)."""
    query = db.query(models.Reservation).filter(models.Reservation.reservation_type == reservation_type)
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    return query.order_by(models.Reservation.reservation_date.desc()).limit(limit).all()


def get_reservations_requiring_action(
    db: Session, 
    user_id: Optional[str] = None
) -> List[models.Reservation]:
    """Get reservations that require user action (pending confirmation, etc.)."""
    query = db.query(models.Reservation).filter(
        models.Reservation.status == "pending"
    )
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    return query.order_by(models.Reservation.reservation_date.asc()).all()


def get_expired_reservations(
    db: Session,
    user_id: Optional[str] = None
) -> List[models.Reservation]:
    """Get reservations that have passed their date and are still pending/confirmed."""
    query = db.query(models.Reservation).filter(
        models.Reservation.reservation_date < datetime.utcnow(),
        models.Reservation.status.in_(["pending", "confirmed"])
    )
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    return query.order_by(models.Reservation.reservation_date.desc()).all()


def cancel_reservation(
    db: Session,
    reservation_id: str,
    cancellation_reason: Optional[str] = None
) -> Optional[models.Reservation]:
    """Cancel a reservation."""
    db_reservation = get_reservation(db, reservation_id)
    if db_reservation and db_reservation.status in ["pending", "confirmed"]:
        db_reservation.status = "cancelled"
        db_reservation.cancelled_at = datetime.utcnow()
        
        # Store cancellation reason
        if cancellation_reason:
            if db_reservation.reservation_metadata:
                db_reservation.reservation_metadata["cancellation_reason"] = cancellation_reason
            else:
                db_reservation.reservation_metadata = {"cancellation_reason": cancellation_reason}
        
        db.commit()
        db.refresh(db_reservation)
    return db_reservation


def confirm_reservation(
    db: Session,
    reservation_id: str,
    confirmation_number: Optional[str] = None
) -> Optional[models.Reservation]:
    """Confirm a pending reservation."""
    db_reservation = get_reservation(db, reservation_id)
    if db_reservation and db_reservation.status == "pending":
        db_reservation.status = "confirmed"
        db_reservation.confirmed_at = datetime.utcnow()
        
        if confirmation_number:
            db_reservation.confirmation_number = confirmation_number
        
        db.commit()
        db.refresh(db_reservation)
    return db_reservation


def complete_reservation(
    db: Session,
    reservation_id: str,
    completion_notes: Optional[str] = None
) -> Optional[models.Reservation]:
    """Mark a reservation as completed."""
    db_reservation = get_reservation(db, reservation_id)
    if db_reservation and db_reservation.status == "confirmed":
        db_reservation.status = "completed"
        db_reservation.completed_at = datetime.utcnow()
        
        if completion_notes:
            if db_reservation.reservation_metadata:
                db_reservation.reservation_metadata["completion_notes"] = completion_notes
            else:
                db_reservation.reservation_metadata = {"completion_notes": completion_notes}
        
        db.commit()
        db.refresh(db_reservation)
    return db_reservation


def get_reservation_reminders(
    db: Session,
    user_id: Optional[str] = None,
    hours_ahead: int = 24
) -> List[models.Reservation]:
    """Get reservations that need reminders (within specified hours)."""
    reminder_time = datetime.utcnow() + timedelta(hours=hours_ahead)
    
    query = db.query(models.Reservation).filter(
        models.Reservation.reservation_date <= reminder_time,
        models.Reservation.reservation_date >= datetime.utcnow(),
        models.Reservation.status == "confirmed"
    )
    
    if user_id:
        query = query.filter(models.Reservation.user_id == user_id)
    
    return query.order_by(models.Reservation.reservation_date.asc()).all()


def update_reservation_metadata(
    db: Session,
    reservation_id: str,
    metadata: Dict[str, Any]
) -> Optional[models.Reservation]:
    """Update reservation metadata."""
    db_reservation = get_reservation(db, reservation_id)
    if db_reservation:
        if db_reservation.reservation_metadata:
            # Merge with existing metadata
            current_metadata = db_reservation.reservation_metadata
            current_metadata.update(metadata)
            db_reservation.reservation_metadata = current_metadata
        else:
            # Set new metadata
            db_reservation.reservation_metadata = metadata
            
        db.commit()
        db.refresh(db_reservation)
    return db_reservation