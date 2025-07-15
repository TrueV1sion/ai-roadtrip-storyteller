"""Commission schemas for API requests and responses."""

from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict
from pydantic import BaseModel, Field

from app.core.enums import BookingType
from app.models.commission import CommissionStatus


class CommissionRateBase(BaseModel):
    """Base commission rate schema."""
    booking_type: BookingType
    base_rate: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    tier_1_threshold: Optional[Decimal] = Field(None, ge=0)
    tier_1_rate: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=4)
    tier_2_threshold: Optional[Decimal] = Field(None, ge=0)
    tier_2_rate: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=4)
    tier_3_threshold: Optional[Decimal] = Field(None, ge=0)
    tier_3_rate: Optional[Decimal] = Field(None, ge=0, le=1, decimal_places=4)


class CommissionRateCreate(CommissionRateBase):
    """Schema for creating commission rate."""
    partner_id: int
    valid_from: Optional[datetime] = None


class CommissionRateUpdate(BaseModel):
    """Schema for updating commission rate."""
    base_rate: Decimal = Field(..., ge=0, le=1, decimal_places=4)
    tier_rates: Optional[Dict[str, tuple[Decimal, Decimal]]] = None
    valid_from: Optional[datetime] = None


class CommissionRateResponse(CommissionRateBase):
    """Schema for commission rate response."""
    id: int
    partner_id: int
    valid_from: datetime
    valid_to: Optional[datetime]
    created_at: datetime
    
    class Config:
        orm_mode = True


class CommissionResponse(BaseModel):
    """Schema for commission response."""
    id: int
    booking_id: int
    commission_rate_id: int
    commission_amount: Decimal
    commission_rate: Decimal
    commission_status: CommissionStatus
    payment_date: Optional[datetime]
    payment_reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        orm_mode = True


class CommissionUpdateStatus(BaseModel):
    """Schema for updating commission status."""
    status: CommissionStatus
    payment_reference: Optional[str] = None
    notes: Optional[str] = None