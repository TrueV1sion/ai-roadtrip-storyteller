"""
Database Consistency Checks and Validators
Ensures data integrity across related tables
"""

from typing import Dict, List, Any, Optional, Type
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text, and_, or_, func

from app.core.logger import get_logger
from app.models.booking import Booking, BookingStatus
from app.models.commission import Commission, CommissionStatus
from app.models.partner import Partner
from app.models.user import User

logger = get_logger(__name__)


class DatabaseConsistencyChecker:
    """Performs consistency checks across database tables."""
    
    def __init__(self, db: Session):
        self.db = db
        self.issues = []
    
    def check_booking_commission_consistency(self) -> Dict[str, Any]:
        """
        Check that all completed bookings have corresponding commission records.
        """
        logger.info("Checking booking-commission consistency...")
        
        # Find completed bookings without commissions
        bookings_without_commission = self.db.query(Booking).outerjoin(
            Commission, Commission.booking_id == Booking.id
        ).filter(
            and_(
                Booking.booking_status == BookingStatus.COMPLETED,
                Commission.id.is_(None)
            )
        ).all()
        
        # Find commissions without bookings
        orphaned_commissions = self.db.query(Commission).outerjoin(
            Booking, Booking.id == Commission.booking_id
        ).filter(Booking.id.is_(None)).all()
        
        issues = {
            "bookings_without_commission": [
                {
                    "booking_id": b.id,
                    "booking_reference": b.booking_reference,
                    "gross_amount": float(b.gross_amount),
                    "booking_date": b.booking_date.isoformat()
                }
                for b in bookings_without_commission
            ],
            "orphaned_commissions": [
                {
                    "commission_id": c.id,
                    "booking_id": c.booking_id,
                    "amount": float(c.commission_amount)
                }
                for c in orphaned_commissions
            ]
        }
        
        return {
            "check": "booking_commission_consistency",
            "passed": len(bookings_without_commission) == 0 and len(orphaned_commissions) == 0,
            "issues": issues,
            "summary": {
                "bookings_without_commission": len(bookings_without_commission),
                "orphaned_commissions": len(orphaned_commissions)
            }
        }
    
    def check_commission_amount_accuracy(self) -> Dict[str, Any]:
        """
        Verify that commission amounts match the calculated values.
        """
        logger.info("Checking commission amount accuracy...")
        
        # Get all bookings with commissions
        results = self.db.query(
            Booking, Commission
        ).join(
            Commission, Commission.booking_id == Booking.id
        ).filter(
            Booking.booking_status.in_([BookingStatus.COMPLETED, BookingStatus.CONFIRMED])
        ).all()
        
        discrepancies = []
        
        for booking, commission in results:
            # Recalculate what the commission should be
            expected_commission = booking.gross_amount - booking.net_amount
            
            if abs(expected_commission - commission.commission_amount) > 0.01:  # Allow 1 cent difference
                discrepancies.append({
                    "booking_id": booking.id,
                    "booking_reference": booking.booking_reference,
                    "expected_commission": float(expected_commission),
                    "actual_commission": float(commission.commission_amount),
                    "difference": float(expected_commission - commission.commission_amount)
                })
        
        return {
            "check": "commission_amount_accuracy",
            "passed": len(discrepancies) == 0,
            "issues": discrepancies,
            "summary": {
                "total_checked": len(results),
                "discrepancies_found": len(discrepancies)
            }
        }
    
    def check_user_data_integrity(self) -> Dict[str, Any]:
        """
        Check user data integrity across related tables.
        """
        logger.info("Checking user data integrity...")
        
        # Find active users without profiles
        from app.models.user_profile import UserProfile
        users_without_profile = self.db.query(User).outerjoin(
            UserProfile, UserProfile.user_id == User.id
        ).filter(
            and_(
                User.is_active == True,
                UserProfile.id.is_(None)
            )
        ).all()
        
        # Find active users without preferences
        from app.models.user_preferences import UserPreferences
        users_without_preferences = self.db.query(User).outerjoin(
            UserPreferences, UserPreferences.user_id == User.id
        ).filter(
            and_(
                User.is_active == True,
                UserPreferences.id.is_(None)
            )
        ).all()
        
        # Find profiles/preferences for non-existent users
        orphaned_profiles = self.db.query(UserProfile).outerjoin(
            User, User.id == UserProfile.user_id
        ).filter(User.id.is_(None)).all()
        
        orphaned_preferences = self.db.query(UserPreferences).outerjoin(
            User, User.id == UserPreferences.user_id
        ).filter(User.id.is_(None)).all()
        
        return {
            "check": "user_data_integrity",
            "passed": all([
                len(users_without_profile) == 0,
                len(users_without_preferences) == 0,
                len(orphaned_profiles) == 0,
                len(orphaned_preferences) == 0
            ]),
            "issues": {
                "users_without_profile": [u.id for u in users_without_profile],
                "users_without_preferences": [u.id for u in users_without_preferences],
                "orphaned_profiles": [p.id for p in orphaned_profiles],
                "orphaned_preferences": [p.id for p in orphaned_preferences]
            },
            "summary": {
                "users_without_profile": len(users_without_profile),
                "users_without_preferences": len(users_without_preferences),
                "orphaned_profiles": len(orphaned_profiles),
                "orphaned_preferences": len(orphaned_preferences)
            }
        }
    
    def check_foreign_key_violations(self) -> Dict[str, Any]:
        """
        Check for foreign key constraint violations that might not be enforced.
        """
        logger.info("Checking foreign key violations...")
        
        violations = []
        
        # Check bookings reference valid users
        invalid_user_bookings = self.db.query(Booking).outerjoin(
            User, User.id == Booking.user_id
        ).filter(User.id.is_(None)).all()
        
        if invalid_user_bookings:
            violations.extend([
                {
                    "table": "bookings",
                    "column": "user_id",
                    "invalid_id": b.user_id,
                    "record_id": b.id
                }
                for b in invalid_user_bookings
            ])
        
        # Check bookings reference valid partners
        invalid_partner_bookings = self.db.query(Booking).outerjoin(
            Partner, Partner.id == Booking.partner_id
        ).filter(Partner.id.is_(None)).all()
        
        if invalid_partner_bookings:
            violations.extend([
                {
                    "table": "bookings",
                    "column": "partner_id",
                    "invalid_id": b.partner_id,
                    "record_id": b.id
                }
                for b in invalid_partner_bookings
            ])
        
        return {
            "check": "foreign_key_violations",
            "passed": len(violations) == 0,
            "issues": violations,
            "summary": {
                "total_violations": len(violations),
                "tables_affected": list(set(v["table"] for v in violations))
            }
        }
    
    def check_duplicate_bookings(self) -> Dict[str, Any]:
        """
        Check for potential duplicate bookings.
        """
        logger.info("Checking for duplicate bookings...")
        
        # Find bookings with same user, partner, service date within 5 minutes
        subquery = self.db.query(
            Booking.user_id,
            Booking.partner_id,
            Booking.service_date,
            func.count(Booking.id).label('count')
        ).filter(
            Booking.booking_status != BookingStatus.CANCELLED
        ).group_by(
            Booking.user_id,
            Booking.partner_id,
            Booking.service_date
        ).having(
            func.count(Booking.id) > 1
        ).subquery()
        
        duplicates = self.db.query(Booking).join(
            subquery,
            and_(
                Booking.user_id == subquery.c.user_id,
                Booking.partner_id == subquery.c.partner_id,
                Booking.service_date == subquery.c.service_date
            )
        ).order_by(
            Booking.user_id,
            Booking.partner_id,
            Booking.service_date
        ).all()
        
        duplicate_groups = {}
        for booking in duplicates:
            key = f"{booking.user_id}_{booking.partner_id}_{booking.service_date}"
            if key not in duplicate_groups:
                duplicate_groups[key] = []
            duplicate_groups[key].append({
                "booking_id": booking.id,
                "booking_reference": booking.booking_reference,
                "status": booking.booking_status.value,
                "created_at": booking.booking_date.isoformat()
            })
        
        return {
            "check": "duplicate_bookings",
            "passed": len(duplicates) == 0,
            "issues": duplicate_groups,
            "summary": {
                "duplicate_groups": len(duplicate_groups),
                "total_duplicates": len(duplicates)
            }
        }
    
    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all consistency checks and return a comprehensive report.
        """
        logger.info("Running comprehensive database consistency checks...")
        
        checks = [
            self.check_booking_commission_consistency(),
            self.check_commission_amount_accuracy(),
            self.check_user_data_integrity(),
            self.check_foreign_key_violations(),
            self.check_duplicate_bookings()
        ]
        
        all_passed = all(check["passed"] for check in checks)
        
        report = {
            "timestamp": datetime.utcnow().isoformat(),
            "all_passed": all_passed,
            "checks": checks,
            "summary": {
                "total_checks": len(checks),
                "passed": sum(1 for check in checks if check["passed"]),
                "failed": sum(1 for check in checks if not check["passed"])
            }
        }
        
        logger.info(f"Consistency check complete: {report['summary']}")
        
        return report
    
    def fix_missing_commissions(self, dry_run: bool = True) -> Dict[str, Any]:
        """
        Fix bookings that are missing commission records.
        """
        from app.services.commission_calculator import CommissionCalculator
        
        logger.info(f"Fixing missing commissions (dry_run={dry_run})...")
        
        # Find completed bookings without commissions
        bookings_without_commission = self.db.query(Booking).outerjoin(
            Commission, Commission.booking_id == Booking.id
        ).filter(
            and_(
                Booking.booking_status == BookingStatus.COMPLETED,
                Commission.id.is_(None)
            )
        ).all()
        
        fixed = []
        errors = []
        
        commission_calculator = CommissionCalculator(self.db)
        
        for booking in bookings_without_commission:
            try:
                # Calculate commission
                commission_amount, commission_rate = commission_calculator.calculate_commission(booking)
                
                if not dry_run:
                    # Create commission record
                    commission = commission_calculator.create_commission_record(
                        booking,
                        commission_amount,
                        commission_rate
                    )
                    fixed.append({
                        "booking_id": booking.id,
                        "commission_id": commission.id,
                        "amount": float(commission_amount)
                    })
                else:
                    fixed.append({
                        "booking_id": booking.id,
                        "calculated_commission": float(commission_amount),
                        "calculated_rate": float(commission_rate)
                    })
                    
            except Exception as e:
                errors.append({
                    "booking_id": booking.id,
                    "error": str(e)
                })
        
        if not dry_run:
            self.db.commit()
        
        return {
            "dry_run": dry_run,
            "fixed": fixed,
            "errors": errors,
            "summary": {
                "total_missing": len(bookings_without_commission),
                "fixed": len(fixed),
                "errors": len(errors)
            }
        }


def run_consistency_check(db: Session) -> Dict[str, Any]:
    """Convenience function to run all consistency checks."""
    checker = DatabaseConsistencyChecker(db)
    return checker.run_all_checks()


def fix_consistency_issues(db: Session, dry_run: bool = True) -> Dict[str, Any]:
    """Convenience function to fix known consistency issues."""
    checker = DatabaseConsistencyChecker(db)
    
    results = {
        "timestamp": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "fixes": {}
    }
    
    # Fix missing commissions
    results["fixes"]["missing_commissions"] = checker.fix_missing_commissions(dry_run)
    
    return results