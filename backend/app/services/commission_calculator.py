"""Commission calculation service for booking transactions."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingStatus
from app.core.enums import BookingType
from backend.app.models.commission import Commission, CommissionRate, CommissionStatus
from backend.app.models.partner import Partner
from backend.app.core.logger import logger


class CommissionCalculator:
    """Service for calculating and managing commissions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_commission(
        self,
        booking: Booking,
        override_rate: Optional[Decimal] = None
    ) -> Tuple[Decimal, Decimal]:
        """
        Calculate commission for a booking.
        
        Args:
            booking: Booking instance
            override_rate: Optional override commission rate
            
        Returns:
            Tuple of (commission_amount, commission_rate)
        """
        if override_rate:
            commission_rate = override_rate
        else:
            # Get applicable commission rate
            rate_record = self._get_applicable_rate(
                booking.partner_id,
                booking.booking_type,
                booking.gross_amount
            )
            
            if not rate_record:
                logger.warning(
                    f"No commission rate found for partner {booking.partner_id}, "
                    f"type {booking.booking_type}"
                )
                return Decimal("0"), Decimal("0")
            
            commission_rate = self._calculate_tiered_rate(
                rate_record,
                booking.gross_amount
            )
        
        commission_amount = booking.gross_amount * commission_rate
        commission_amount = commission_amount.quantize(Decimal("0.01"))
        
        return commission_amount, commission_rate
    
    def _get_applicable_rate(
        self,
        partner_id: int,
        booking_type: BookingType,
        amount: Decimal
    ) -> Optional[CommissionRate]:
        """Get the applicable commission rate for a booking."""
        now = datetime.utcnow()
        
        rate = self.db.query(CommissionRate).filter(
            and_(
                CommissionRate.partner_id == partner_id,
                CommissionRate.booking_type == booking_type,
                CommissionRate.valid_from <= now,
                or_(
                    CommissionRate.valid_to.is_(None),
                    CommissionRate.valid_to >= now
                )
            )
        ).order_by(CommissionRate.valid_from.desc()).first()
        
        return rate
    
    def _calculate_tiered_rate(
        self,
        rate_record: CommissionRate,
        amount: Decimal
    ) -> Decimal:
        """Calculate tiered commission rate based on amount."""
        if rate_record.tier_3_threshold and amount >= rate_record.tier_3_threshold:
            return rate_record.tier_3_rate
        elif rate_record.tier_2_threshold and amount >= rate_record.tier_2_threshold:
            return rate_record.tier_2_rate
        elif rate_record.tier_1_threshold and amount >= rate_record.tier_1_threshold:
            return rate_record.tier_1_rate
        else:
            return rate_record.base_rate
    
    def create_commission_record(
        self,
        booking: Booking,
        commission_amount: Decimal,
        commission_rate: Decimal
    ) -> Commission:
        """Create a commission record for a booking."""
        rate_record = self._get_applicable_rate(
            booking.partner_id,
            booking.booking_type,
            booking.gross_amount
        )
        
        commission = Commission(
            booking_id=booking.id,
            commission_rate_id=rate_record.id if rate_record else None,
            commission_amount=commission_amount,
            commission_rate=commission_rate,
            commission_status=CommissionStatus.PENDING
        )
        
        self.db.add(commission)
        self.db.commit()
        self.db.refresh(commission)
        
        return commission
    
    def update_commission_status(
        self,
        commission_id: int,
        status: CommissionStatus,
        payment_reference: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Commission:
        """Update commission status."""
        commission = self.db.query(Commission).filter(
            Commission.id == commission_id
        ).first()
        
        if not commission:
            raise ValueError(f"Commission {commission_id} not found")
        
        commission.commission_status = status
        
        if status == CommissionStatus.PAID:
            commission.payment_date = datetime.utcnow()
            if payment_reference:
                commission.payment_reference = payment_reference
        
        if notes:
            commission.notes = notes
        
        self.db.commit()
        self.db.refresh(commission)
        
        return commission
    
    def get_partner_commission_summary(
        self,
        partner_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get commission summary for a partner."""
        commissions = self.db.query(
            Commission.commission_status,
            func.count(Commission.id).label('count'),
            func.sum(Commission.commission_amount).label('total')
        ).join(
            Booking
        ).filter(
            and_(
                Booking.partner_id == partner_id,
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date
            )
        ).group_by(Commission.commission_status).all()
        
        summary = {
            "partner_id": partner_id,
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "commissions": {}
        }
        
        total_amount = Decimal("0")
        total_count = 0
        
        for status, count, amount in commissions:
            summary["commissions"][status.value] = {
                "count": count,
                "amount": float(amount or 0)
            }
            total_amount += amount or Decimal("0")
            total_count += count
        
        summary["total"] = {
            "count": total_count,
            "amount": float(total_amount)
        }
        
        return summary
    
    def calculate_monthly_revenue_share(
        self,
        year: int,
        month: int
    ) -> List[Dict]:
        """Calculate revenue share for all partners for a month."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(seconds=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(seconds=1)
        
        results = self.db.query(
            Partner.id,
            Partner.name,
            Partner.partner_code,
            func.sum(Booking.gross_amount).label('gross_revenue'),
            func.sum(Commission.commission_amount).label('total_commission'),
            func.count(Booking.id).label('booking_count')
        ).join(
            Booking, Booking.partner_id == Partner.id
        ).join(
            Commission, Commission.booking_id == Booking.id
        ).filter(
            and_(
                Booking.booking_date >= start_date,
                Booking.booking_date <= end_date,
                Booking.booking_status == BookingStatus.COMPLETED
            )
        ).group_by(
            Partner.id,
            Partner.name,
            Partner.partner_code
        ).all()
        
        revenue_shares = []
        for result in results:
            net_revenue = result.gross_revenue - result.total_commission
            revenue_shares.append({
                "partner": {
                    "id": result.id,
                    "name": result.name,
                    "code": result.partner_code
                },
                "period": f"{year}-{month:02d}",
                "bookings": result.booking_count,
                "gross_revenue": float(result.gross_revenue),
                "commission": float(result.total_commission),
                "net_revenue": float(net_revenue),
                "average_commission_rate": float(
                    result.total_commission / result.gross_revenue
                ) if result.gross_revenue > 0 else 0
            })
        
        return revenue_shares
    
    def get_commission_rates_by_partner(
        self,
        partner_id: int,
        active_only: bool = True
    ) -> List[CommissionRate]:
        """Get all commission rates for a partner."""
        query = self.db.query(CommissionRate).filter(
            CommissionRate.partner_id == partner_id
        )
        
        if active_only:
            now = datetime.utcnow()
            query = query.filter(
                and_(
                    CommissionRate.valid_from <= now,
                    or_(
                        CommissionRate.valid_to.is_(None),
                        CommissionRate.valid_to >= now
                    )
                )
            )
        
        return query.order_by(
            CommissionRate.booking_type,
            CommissionRate.valid_from.desc()
        ).all()
    
    def update_commission_rate(
        self,
        partner_id: int,
        booking_type: BookingType,
        base_rate: Decimal,
        tier_rates: Optional[Dict[str, Tuple[Decimal, Decimal]]] = None,
        valid_from: Optional[datetime] = None
    ) -> CommissionRate:
        """Update commission rate for a partner and booking type."""
        if valid_from is None:
            valid_from = datetime.utcnow()
        
        # End current rate
        current_rate = self._get_applicable_rate(
            partner_id,
            booking_type,
            Decimal("0")  # Amount doesn't matter for finding current rate
        )
        
        if current_rate:
            current_rate.valid_to = valid_from - timedelta(seconds=1)
            self.db.commit()
        
        # Create new rate
        new_rate = CommissionRate(
            partner_id=partner_id,
            booking_type=booking_type,
            base_rate=base_rate,
            valid_from=valid_from
        )
        
        # Set tier rates if provided
        if tier_rates:
            if "tier_1" in tier_rates:
                new_rate.tier_1_threshold = tier_rates["tier_1"][0]
                new_rate.tier_1_rate = tier_rates["tier_1"][1]
            if "tier_2" in tier_rates:
                new_rate.tier_2_threshold = tier_rates["tier_2"][0]
                new_rate.tier_2_rate = tier_rates["tier_2"][1]
            if "tier_3" in tier_rates:
                new_rate.tier_3_threshold = tier_rates["tier_3"][0]
                new_rate.tier_3_rate = tier_rates["tier_3"][1]
        
        self.db.add(new_rate)
        self.db.commit()
        self.db.refresh(new_rate)
        
        return new_rate