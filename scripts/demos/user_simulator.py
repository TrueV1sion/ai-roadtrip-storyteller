"""
User Simulator for AI Road Trip Storyteller
Generates realistic user profiles and behaviors for testing
"""

import random
from typing import Dict, List, Optional, Any
from datetime import datetime, time
from dataclasses import dataclass, field
import json


@dataclass
class FamilyMember:
    """Represents a family member with specific characteristics"""
    name: str
    age: int
    role: str  # parent, child, teen, etc.
    interests: List[str]
    attention_span: float  # 0-1, affects interaction patterns
    
    
@dataclass 
class UserProfile:
    """Complete user profile for simulation"""
    id: str
    name: str
    email: str
    age: int
    occupation: str
    family_members: List[FamilyMember] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    travel_frequency: str = "occasional"  # frequent, occasional, rare
    tech_savviness: float = 0.5  # 0-1
    budget_level: str = "moderate"  # budget, moderate, premium
    accessibility_needs: List[str] = field(default_factory=list)
    language_preferences: List[str] = field(default_factory=list)
    device_type: str = "smartphone"
    subscription_tier: str = "free"  # free, basic, premium
    created_at: datetime = field(default_factory=datetime.now)
    

class UserSimulator:
    """Generates diverse, realistic user profiles"""
    
    # Name pools for realistic user generation
    FIRST_NAMES = {
        "male": ["James", "John", "Robert", "Michael", "William", "David", "Richard", 
                 "Joseph", "Thomas", "Christopher", "Daniel", "Paul", "Mark", "Donald",
                 "Kenneth", "Steven", "Edward", "Brian", "Ronald", "Anthony"],
        "female": ["Mary", "Patricia", "Jennifer", "Linda", "Elizabeth", "Barbara",
                   "Susan", "Jessica", "Sarah", "Karen", "Nancy", "Betty", "Helen",
                   "Sandra", "Donna", "Carol", "Ruth", "Sharon", "Michelle", "Laura"]
    }
    
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
                  "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
                  "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]
    
    OCCUPATIONS = {
        "professional": ["Software Engineer", "Doctor", "Lawyer", "Teacher", "Nurse",
                        "Accountant", "Marketing Manager", "Data Scientist", "Architect",
                        "Financial Analyst", "Product Manager", "Consultant"],
        "service": ["Restaurant Manager", "Retail Manager", "Customer Service Rep",
                   "Sales Associate", "Administrative Assistant", "Hotel Manager"],
        "creative": ["Graphic Designer", "Writer", "Photographer", "Musician",
                    "Artist", "Video Editor", "Content Creator"],
        "trades": ["Electrician", "Plumber", "Contractor", "Mechanic", "HVAC Tech"],
        "other": ["Student", "Retired", "Stay-at-home Parent", "Entrepreneur"]
    }
    
    INTERESTS = {
        "outdoor": ["hiking", "camping", "fishing", "photography", "birdwatching",
                   "rock climbing", "kayaking", "cycling", "running"],
        "cultural": ["history", "art", "music", "theater", "museums", "architecture",
                    "local culture", "festivals", "literature"],
        "food": ["fine dining", "local cuisine", "wine tasting", "craft beer",
                "cooking", "farmers markets", "food trucks", "cafes"],
        "entertainment": ["movies", "gaming", "sports", "concerts", "comedy shows",
                         "amusement parks", "shopping", "nightlife"],
        "educational": ["science", "technology", "nature", "astronomy", "geology",
                       "biology", "anthropology", "archaeology"],
        "family": ["playgrounds", "zoos", "aquariums", "beaches", "picnics",
                  "family activities", "educational experiences", "easy hikes"],
        "wellness": ["yoga", "meditation", "spas", "wellness retreats", "fitness"]
    }
    
    ACCESSIBILITY_NEEDS = [
        "wheelchair_accessible",
        "hearing_impaired",
        "vision_impaired", 
        "mobility_limited",
        "dietary_restrictions",
        "sensory_friendly",
        "service_animal"
    ]
    
    def __init__(self):
        self.user_counter = 0
        
    def generate_user(self, persona_type: Optional[str] = None) -> UserProfile:
        """Generate a complete user profile"""
        self.user_counter += 1
        
        # Determine gender for name generation
        gender = random.choice(["male", "female"])
        first_name = random.choice(self.FIRST_NAMES[gender])
        last_name = random.choice(self.LAST_NAMES)
        
        # Generate age based on persona
        if persona_type == "family":
            age = random.randint(28, 45)
        elif persona_type == "young_professional":
            age = random.randint(24, 35)
        elif persona_type == "retiree":
            age = random.randint(60, 75)
        elif persona_type == "student":
            age = random.randint(18, 25)
        else:
            age = random.randint(25, 65)
            
        # Generate occupation
        if age < 25:
            occupation = "Student"
        elif age > 65:
            occupation = "Retired"
        else:
            category = random.choice(list(self.OCCUPATIONS.keys()))
            occupation = random.choice(self.OCCUPATIONS[category])
            
        # Create base profile
        user = UserProfile(
            id=f"user_{self.user_counter}_{int(datetime.now().timestamp())}",
            name=f"{first_name} {last_name}",
            email=f"{first_name.lower()}.{last_name.lower()}@example.com",
            age=age,
            occupation=occupation
        )
        
        # Add family members if applicable
        if persona_type == "family" or (age > 30 and random.random() < 0.6):
            user.family_members = self._generate_family(user.age, gender)
            
        # Generate interests based on profile
        user.interests = self._generate_interests(user, persona_type)
        
        # Set travel frequency
        if occupation in ["Consultant", "Sales Manager", "Entrepreneur"]:
            user.travel_frequency = "frequent"
        elif age > 60 or "family" in persona_type:
            user.travel_frequency = random.choice(["occasional", "rare"])
        else:
            user.travel_frequency = random.choice(["frequent", "occasional", "rare"])
            
        # Tech savviness based on age and occupation
        if "Engineer" in occupation or "Developer" in occupation or "Data" in occupation:
            user.tech_savviness = random.uniform(0.8, 1.0)
        elif age < 30:
            user.tech_savviness = random.uniform(0.7, 0.95)
        elif age > 60:
            user.tech_savviness = random.uniform(0.3, 0.7)
        else:
            user.tech_savviness = random.uniform(0.5, 0.85)
            
        # Budget level
        high_income_jobs = ["Doctor", "Lawyer", "Software Engineer", "Financial Analyst",
                           "Product Manager", "Consultant", "Architect"]
        if occupation in high_income_jobs:
            user.budget_level = random.choice(["moderate", "premium", "premium"])
        elif occupation == "Student":
            user.budget_level = "budget"
        else:
            user.budget_level = random.choice(["budget", "moderate", "moderate"])
            
        # Accessibility needs (10% chance)
        if random.random() < 0.1:
            user.accessibility_needs = [random.choice(self.ACCESSIBILITY_NEEDS)]
            
        # Language preferences
        user.language_preferences = ["en"]  # Default English
        if random.random() < 0.2:  # 20% multilingual
            additional_langs = random.sample(["es", "fr", "de", "zh", "ja"], 
                                           k=random.randint(1, 2))
            user.language_preferences.extend(additional_langs)
            
        # Device type
        if user.tech_savviness > 0.7:
            user.device_type = random.choice(["smartphone", "smartphone", "tablet"])
        else:
            user.device_type = "smartphone"
            
        # Subscription tier based on budget and travel frequency
        if user.budget_level == "premium" and user.travel_frequency == "frequent":
            user.subscription_tier = "premium"
        elif user.budget_level != "budget" and random.random() < 0.3:
            user.subscription_tier = "basic"
        else:
            user.subscription_tier = "free"
            
        return user
        
    def _generate_family(self, parent_age: int, parent_gender: str) -> List[FamilyMember]:
        """Generate family members"""
        family = []
        
        # Add spouse (70% chance)
        if random.random() < 0.7:
            spouse_gender = "female" if parent_gender == "male" else "male"
            spouse_name = random.choice(self.FIRST_NAMES[spouse_gender])
            spouse_age = parent_age + random.randint(-5, 5)
            family.append(FamilyMember(
                name=spouse_name,
                age=spouse_age,
                role="parent",
                interests=random.sample(
                    self.INTERESTS["cultural"] + self.INTERESTS["outdoor"],
                    k=random.randint(2, 4)
                ),
                attention_span=random.uniform(0.7, 0.9)
            ))
            
        # Add children based on parent age
        if parent_age >= 25:
            max_kids = min(4, (parent_age - 20) // 10 + 1)
            num_kids = random.randint(0, max_kids)
            
            for i in range(num_kids):
                # Calculate realistic child age
                max_child_age = min(parent_age - 20, 18)
                if max_child_age > 0:
                    child_age = random.randint(2, max_child_age)
                    child_gender = random.choice(["male", "female"])
                    child_name = random.choice(self.FIRST_NAMES[child_gender])
                    
                    # Determine role based on age
                    if child_age < 5:
                        role = "toddler"
                        interests = ["playgrounds", "animals", "stories"]
                        attention = random.uniform(0.2, 0.4)
                    elif child_age < 13:
                        role = "child" 
                        interests = random.sample(
                            ["games", "animals", "stories", "science", "sports"],
                            k=random.randint(2, 3)
                        )
                        attention = random.uniform(0.4, 0.6)
                    else:
                        role = "teen"
                        interests = random.sample(
                            self.INTERESTS["entertainment"] + ["social media", "friends"],
                            k=random.randint(2, 4)
                        )
                        attention = random.uniform(0.5, 0.7)
                        
                    family.append(FamilyMember(
                        name=child_name,
                        age=child_age,
                        role=role,
                        interests=interests,
                        attention_span=attention
                    ))
                    
        return family
        
    def _generate_interests(self, user: UserProfile, persona_type: Optional[str]) -> List[str]:
        """Generate interests based on user profile"""
        interests = []
        
        # Base interests on persona type
        if persona_type == "adventure_seeker":
            interests.extend(random.sample(self.INTERESTS["outdoor"], k=4))
            interests.extend(random.sample(self.INTERESTS["cultural"], k=2))
        elif persona_type == "history_buff":
            interests.extend(random.sample(self.INTERESTS["cultural"], k=4))
            interests.extend(random.sample(self.INTERESTS["educational"], k=2))
        elif persona_type == "foodie":
            interests.extend(random.sample(self.INTERESTS["food"], k=4))
            interests.extend(random.sample(self.INTERESTS["cultural"], k=2))
        elif user.family_members:
            interests.extend(random.sample(self.INTERESTS["family"], k=3))
            interests.extend(random.sample(self.INTERESTS["outdoor"], k=2))
        else:
            # Random mix
            for category in self.INTERESTS:
                if random.random() < 0.4:
                    interests.extend(random.sample(self.INTERESTS[category], 
                                                 k=random.randint(1, 3)))
                    
        # Age-based adjustments
        if user.age < 30:
            interests.extend(random.sample(self.INTERESTS["entertainment"], k=2))
        elif user.age > 60:
            interests.extend(random.sample(self.INTERESTS["wellness"], k=2))
            
        # Remove duplicates and limit
        interests = list(set(interests))[:8]
        
        return interests
        
    def generate_batch(self, count: int, distribution: Optional[Dict[str, float]] = None) -> List[UserProfile]:
        """Generate a batch of users with specified distribution"""
        if distribution is None:
            distribution = {
                "family": 0.3,
                "young_professional": 0.2,
                "adventure_seeker": 0.15,
                "retiree": 0.1,
                "student": 0.1,
                "foodie": 0.1,
                "history_buff": 0.05
            }
            
        users = []
        remaining = count
        
        # Generate users according to distribution
        for persona, ratio in distribution.items():
            persona_count = int(count * ratio)
            for _ in range(persona_count):
                users.append(self.generate_user(persona))
                remaining -= 1
                
        # Fill remaining with random personas
        for _ in range(remaining):
            users.append(self.generate_user())
            
        return users
        
    def generate_usage_patterns(self, user: UserProfile) -> Dict[str, Any]:
        """Generate realistic usage patterns for a user"""
        patterns = {
            "preferred_times": self._get_preferred_times(user),
            "session_duration": self._get_session_duration(user),
            "feature_usage": self._get_feature_usage(user),
            "interaction_style": self._get_interaction_style(user),
            "booking_behavior": self._get_booking_behavior(user),
            "voice_usage": self._get_voice_usage(user)
        }
        
        return patterns
        
    def _get_preferred_times(self, user: UserProfile) -> List[Dict[str, Any]]:
        """Get preferred usage times based on profile"""
        times = []
        
        if user.occupation == "Student":
            # Afternoons and weekends
            times.extend([
                {"day": "weekday", "start": time(15, 0), "end": time(22, 0)},
                {"day": "weekend", "start": time(10, 0), "end": time(23, 0)}
            ])
        elif "Manager" in user.occupation or "Engineer" in user.occupation:
            # Commute times and weekends
            times.extend([
                {"day": "weekday", "start": time(7, 0), "end": time(9, 0)},
                {"day": "weekday", "start": time(17, 0), "end": time(19, 0)},
                {"day": "weekend", "start": time(9, 0), "end": time(18, 0)}
            ])
        elif user.occupation == "Retired":
            # Mid-morning and afternoons
            times.extend([
                {"day": "any", "start": time(10, 0), "end": time(16, 0)}
            ])
        elif user.family_members:
            # Family trip times
            times.extend([
                {"day": "weekend", "start": time(8, 0), "end": time(20, 0)},
                {"day": "holiday", "start": time(9, 0), "end": time(18, 0)}
            ])
        else:
            # General patterns
            times.extend([
                {"day": "weekend", "start": time(10, 0), "end": time(18, 0)}
            ])
            
        return times
        
    def _get_session_duration(self, user: UserProfile) -> Dict[str, int]:
        """Get typical session durations in minutes"""
        if user.travel_frequency == "frequent":
            return {
                "commute": random.randint(20, 60),
                "weekend": random.randint(120, 360),
                "vacation": random.randint(240, 480)
            }
        elif user.family_members:
            return {
                "commute": random.randint(15, 30),
                "weekend": random.randint(60, 240),
                "vacation": random.randint(180, 360)
            }
        else:
            return {
                "commute": random.randint(20, 45),
                "weekend": random.randint(90, 180),
                "vacation": random.randint(120, 300)
            }
            
    def _get_feature_usage(self, user: UserProfile) -> Dict[str, float]:
        """Get feature usage probabilities"""
        base_usage = {
            "navigation": 0.9,
            "stories": 0.5,
            "voice_commands": 0.3,
            "bookings": 0.2,
            "games": 0.1,
            "ar_features": 0.05,
            "side_quests": 0.15,
            "music": 0.4
        }
        
        # Adjust based on profile
        if user.tech_savviness > 0.7:
            base_usage["voice_commands"] += 0.3
            base_usage["ar_features"] += 0.1
            
        if user.family_members:
            base_usage["games"] += 0.4
            base_usage["stories"] += 0.2
            
        if "history" in user.interests or "culture" in user.interests:
            base_usage["stories"] += 0.3
            
        if user.budget_level == "premium":
            base_usage["bookings"] += 0.3
            
        if user.age < 30:
            base_usage["music"] += 0.2
            base_usage["ar_features"] += 0.1
            
        # Normalize to max 1.0
        for key in base_usage:
            base_usage[key] = min(base_usage[key], 1.0)
            
        return base_usage
        
    def _get_interaction_style(self, user: UserProfile) -> Dict[str, Any]:
        """Get interaction style preferences"""
        return {
            "voice_preference": "high" if user.tech_savviness > 0.7 else "medium",
            "detail_level": "comprehensive" if "history" in user.interests else "balanced",
            "interruption_tolerance": "low" if user.family_members else "medium",
            "exploration_willingness": "high" if "adventure" in str(user.interests) else "medium",
            "planning_preference": "detailed" if user.travel_frequency == "frequent" else "flexible"
        }
        
    def _get_booking_behavior(self, user: UserProfile) -> Dict[str, Any]:
        """Get booking behavior patterns"""
        return {
            "advance_booking": user.travel_frequency == "frequent",
            "price_sensitivity": user.budget_level == "budget",
            "restaurant_bookings": "food" in str(user.interests),
            "attraction_bookings": user.family_members or "culture" in str(user.interests),
            "spontaneous_bookings": user.age < 35 and user.budget_level != "budget",
            "group_size": len(user.family_members) + 1 if user.family_members else random.randint(1, 2)
        }
        
    def _get_voice_usage(self, user: UserProfile) -> Dict[str, Any]:
        """Get voice interaction patterns"""
        return {
            "preferred_personality": self._select_voice_personality(user),
            "command_complexity": "complex" if user.tech_savviness > 0.7 else "simple",
            "conversation_length": "extended" if not user.family_members else "brief",
            "accent_preference": "neutral",  # Could be expanded
            "speed_preference": "normal" if user.age < 60 else "slow"
        }
        
    def _select_voice_personality(self, user: UserProfile) -> str:
        """Select appropriate voice personality"""
        if user.family_members:
            return "enthusiastic_guide"
        elif "history" in user.interests:
            return "educational_expert"
        elif user.age < 30:
            return "witty_companion"
        elif user.age > 60:
            return "calm_narrator"
        else:
            return random.choice(["calm_narrator", "witty_companion"])
            
    def export_users(self, users: List[UserProfile], filename: str = "simulated_users.json"):
        """Export users to JSON file"""
        data = []
        for user in users:
            user_dict = {
                "profile": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "age": user.age,
                    "occupation": user.occupation,
                    "interests": user.interests,
                    "travel_frequency": user.travel_frequency,
                    "tech_savviness": user.tech_savviness,
                    "budget_level": user.budget_level,
                    "accessibility_needs": user.accessibility_needs,
                    "language_preferences": user.language_preferences,
                    "device_type": user.device_type,
                    "subscription_tier": user.subscription_tier,
                    "created_at": user.created_at.isoformat()
                },
                "family": [
                    {
                        "name": member.name,
                        "age": member.age,
                        "role": member.role,
                        "interests": member.interests,
                        "attention_span": member.attention_span
                    } for member in user.family_members
                ],
                "usage_patterns": self.generate_usage_patterns(user)
            }
            data.append(user_dict)
            
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
            
        print(f"Exported {len(users)} users to {filename}")


def main():
    """Example usage"""
    simulator = UserSimulator()
    
    # Generate individual users
    print("Generating individual users...")
    family_user = simulator.generate_user("family")
    print(f"\nFamily User: {family_user.name}")
    print(f"  Age: {family_user.age}")
    print(f"  Occupation: {family_user.occupation}")
    print(f"  Family: {len(family_user.family_members)} members")
    print(f"  Interests: {', '.join(family_user.interests)}")
    
    business_user = simulator.generate_user("young_professional")
    print(f"\nBusiness User: {business_user.name}")
    print(f"  Age: {business_user.age}")
    print(f"  Occupation: {business_user.occupation}")
    print(f"  Travel Frequency: {business_user.travel_frequency}")
    print(f"  Tech Savviness: {business_user.tech_savviness:.2f}")
    
    # Generate batch of users
    print("\n\nGenerating batch of 100 users...")
    users = simulator.generate_batch(100)
    
    # Show distribution
    persona_counts = {}
    for user in users:
        key = "family" if user.family_members else user.occupation.split()[0]
        persona_counts[key] = persona_counts.get(key, 0) + 1
        
    print("\nUser Distribution:")
    for persona, count in sorted(persona_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {persona}: {count}")
        
    # Export users
    simulator.export_users(users)
    
    # Show usage patterns for a sample user
    print(f"\n\nUsage Patterns for {users[0].name}:")
    patterns = simulator.generate_usage_patterns(users[0])
    print(json.dumps(patterns, indent=2, default=str))


if __name__ == "__main__":
    main()