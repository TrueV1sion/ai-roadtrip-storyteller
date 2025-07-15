from typing import Dict, List
from datetime import datetime

from app.core.logger import get_logger

logger = get_logger(__name__)


class FamilyFacilitiesService:
    """Service for managing family-friendly facility information."""

    FACILITY_TYPES = {
        "rest_stop": {
            "priority": "high",
            "check_interval_mins": 30
        },
        "restaurant": {
            "priority": "medium",
            "check_interval_mins": 60
        },
        "playground": {
            "priority": "medium",
            "check_interval_mins": 60
        },
        "medical": {
            "priority": "high",
            "check_interval_mins": 30
        },
        "entertainment": {
            "priority": "low",
            "check_interval_mins": 120
        },
        "shopping": {
            "priority": "low",
            "check_interval_mins": 120
        },
        "nature_spot": {
            "priority": "medium",
            "check_interval_mins": 60
        },
        "indoor_play": {
            "priority": "medium",
            "check_interval_mins": 60
        },
        "emergency": {
            "priority": "critical",
            "check_interval_mins": 15
        }
    }

    def __init__(self):
        self.facility_ratings = {}
        self.user_reviews = {}
        self.emergency_contacts = {}

    async def find_facilities(
        self,
        location: Dict[str, float],
        radius_km: float,
        facility_type: str
    ) -> List[Dict]:
        """
        Find family-friendly facilities near a location.
        
        Args:
            location: Dict with latitude and longitude
            radius_km: Search radius in kilometers
            facility_type: Type of facility (restroom, playground, restaurant, etc.)
        """
        try:
            # In production, this would call external APIs (Google Places, etc.)
            facilities = self._get_demo_facilities(facility_type)
            
            # Add family-friendly metrics
            for facility in facilities:
                facility.update({
                    "family_rating": self._get_family_rating(facility["id"]),
                    "amenities": self._get_facility_amenities(
                        facility["id"],
                        facility_type
                    ),
                    "recent_reviews": self._get_recent_reviews(facility["id"]),
                    "safety_info": self._get_safety_info(
                        facility["id"],
                        facility_type
                    ),
                    "crowd_level": self._get_crowd_level(facility["id"]),
                    "special_needs": self._get_special_needs_info(facility["id"])
                })
            
            return facilities
            
        except Exception as e:
            logger.error(f"Error finding facilities: {str(e)}")
            return []

    def _get_family_rating(self, facility_id: str) -> Dict:
        """Get family-specific ratings for a facility."""
        return {
            "overall": 4.5,
            "cleanliness": 4.2,
            "changing_tables": True,
            "kid_friendly": 4.8,
            "safety": 4.6,
            "noise_level": "Moderate",
            "total_ratings": 125,
            "recent_incidents": 0,
            "staff_friendliness": 4.7,
            "value_for_money": 4.3
        }

    def _get_facility_amenities(
        self,
        facility_id: str,
        facility_type: str
    ) -> Dict:
        """Get family-relevant amenities for a facility."""
        base_amenities = {
            "family_restroom": True,
            "changing_station": True,
            "nursing_room": True,
            "wheelchair_accessible": True,
            "stroller_friendly": True,
            "first_aid_kit": True,
            "water_fountain": True,
            "wifi": True,
            "phone_charging": True,
            "family_parking": True
        }
        
        type_specific = {
            "restaurant": {
                "high_chairs": True,
                "kids_menu": True,
                "allergy_friendly": True,
                "play_area": True,
                "kids_eat_free": False,
                "quick_service": True,
                "outdoor_seating": True,
                "private_rooms": True,
                "dietary_options": ["vegetarian", "gluten-free", "nut-free"]
            },
            "playground": {
                "age_ranges": ["2-5", "5-12"],
                "surface_type": "Rubber",
                "shade_available": True,
                "water_fountain": True,
                "picnic_area": True,
                "fenced": True,
                "equipment_types": ["swings", "slides", "climbing"],
                "restroom_proximity": "< 50m",
                "seating_areas": True
            },
            "rest_stop": {
                "24_hour": True,
                "security": True,
                "vending": True,
                "pet_area": True,
                "shower_facilities": True,
                "laundry": False,
                "market": True,
                "outdoor_space": True,
                "emergency_phone": True
            },
            "medical": {
                "pediatric_care": True,
                "urgent_care": True,
                "pharmacy": True,
                "emergency_services": True,
                "insurance_accepted": ["Major providers"],
                "wait_times": "15-30 mins"
            },
            "entertainment": {
                "age_appropriate": True,
                "indoor": True,
                "cost_range": "$$",
                "avg_duration": "2 hours",
                "booking_required": False,
                "educational_value": True
            },
            "indoor_play": {
                "climate_controlled": True,
                "age_sections": True,
                "supervision": True,
                "safety_equipment": True,
                "snack_bar": True,
                "party_rooms": True
            },
            "nature_spot": {
                "trail_difficulty": "Easy",
                "stroller_accessible": True,
                "wildlife_viewing": True,
                "educational_signs": True,
                "ranger_station": True,
                "bug_spray_needed": True
            }
        }
        
        return {
            **base_amenities,
            **(type_specific.get(facility_type, {}))
        }

    def _get_safety_info(self, facility_id: str, facility_type: str) -> Dict:
        """Get safety information for a facility."""
        return {
            "security_present": True,
            "cctv_monitored": True,
            "emergency_exits": True,
            "first_aid_certified_staff": True,
            "child_safety_measures": [
                "Child ID system",
                "Secured entrances",
                "Safety barriers"
            ],
            "emergency_contacts": {
                "onsite_security": "555-0100",
                "nearest_hospital": "555-0101",
                "police": "911"
            },
            "last_inspection": "2024-01-15",
            "safety_rating": 4.8
        }

    def _get_crowd_level(self, facility_id: str) -> Dict:
        """Get current and predicted crowd levels."""
        return {
            "current_level": "Moderate",
            "predicted_peaks": [
                {"time": "12:00", "level": "High"},
                {"time": "17:00", "level": "High"}
            ],
            "best_visit_times": ["10:00", "14:00", "19:00"],
            "current_wait_time": "5-10 minutes",
            "capacity_status": "65%"
        }

    def _get_special_needs_info(self, facility_id: str) -> Dict:
        """Get information for families with special needs."""
        return {
            "accessibility_features": [
                "Wheelchair ramps",
                "Sensory-friendly spaces",
                "Quiet rooms"
            ],
            "special_equipment": [
                "Mobility aids",
                "Sensory kits",
                "Communication boards"
            ],
            "staff_training": [
                "Special needs certified",
                "First aid trained",
                "ASL proficient"
            ],
            "accommodations": [
                "Priority access",
                "Special parking",
                "Companion care"
            ]
        }

    def _get_recent_reviews(self, facility_id: str) -> List[Dict]:
        """Get recent family-focused reviews."""
        return [
            {
                "rating": 5,
                "comment": "Very clean, great for kids!",
                "date": "2024-02-19",
                "family_type": "Young children",
                "visit_length": "2 hours",
                "would_return": True,
                "helpful_count": 12
            },
            {
                "rating": 4,
                "comment": "Good changing facilities, friendly staff",
                "date": "2024-02-18",
                "family_type": "Toddler",
                "visit_length": "1 hour",
                "would_return": True,
                "helpful_count": 8
            }
        ]

    def _get_demo_facilities(self, facility_type: str) -> List[Dict]:
        """Get demo facility data. Replace with actual API calls."""
        facilities = [
            {
                "id": f"{facility_type}_1",
                "name": f"Family {facility_type.title()} 1",
                "location": {
                    "latitude": 40.7128,
                    "longitude": -74.0060
                },
                "distance": "0.5 km",
                "type": facility_type,
                "open_now": True,
                "photos": ["url1", "url2"]
            },
            {
                "id": f"{facility_type}_2",
                "name": f"Kid-Friendly {facility_type.title()} 2",
                "location": {
                    "latitude": 40.7129,
                    "longitude": -74.0061
                },
                "distance": "0.8 km",
                "type": facility_type,
                "open_now": True,
                "photos": ["url3", "url4"]
            }
        ]
        return facilities


# Global service instance
family_facilities = FamilyFacilitiesService() 