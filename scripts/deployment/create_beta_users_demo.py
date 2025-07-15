#!/usr/bin/env python3
"""
Create Beta User Accounts - Demo Version
Simulates creating beta user accounts for demonstration
"""
import json
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict, Any

class BetaUserGeneratorDemo:
    """Generates beta user accounts (demo version)"""
    
    def __init__(self):
        self.user_categories = {
            "family_travelers": {
                "count": 25,
                "preferences": {
                    "travel_style": "family",
                    "interests": ["education", "entertainment", "adventure"],
                    "voice_preference": "Mickey Mouse"
                }
            },
            "business_travelers": {
                "count": 25,
                "preferences": {
                    "travel_style": "business",
                    "interests": ["efficiency", "productivity", "comfort"],
                    "voice_preference": "Professional Assistant"
                }
            },
            "event_attendees": {
                "count": 25,
                "preferences": {
                    "travel_style": "events",
                    "interests": ["concerts", "sports", "festivals"],
                    "voice_preference": "DJ Voice"
                }
            },
            "rideshare_drivers": {
                "count": 25,
                "preferences": {
                    "travel_style": "rideshare",
                    "interests": ["efficiency", "passenger_comfort", "earnings"],
                    "voice_preference": "Captain"
                }
            }
        }
        
        self.created_users = []
    
    def generate_unique_email(self, category: str, index: int) -> str:
        """Generate unique email for beta user"""
        return f"beta_{category}_{index}@roadtrip-beta.com"
    
    def generate_username(self, category: str, index: int) -> str:
        """Generate unique username"""
        return f"beta_{category}_{index:03d}"
    
    def generate_beta_code(self) -> str:
        """Generate unique beta access code"""
        return f"BETA-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
    
    def create_user_batch(self, category: str, count: int, preferences: Dict[str, Any]):
        """Create a batch of users for a category"""
        print(f"\n📝 Creating {count} {category.replace('_', ' ').title()} users...")
        
        users_created = 0
        
        for i in range(count):
            # Generate user data
            email = self.generate_unique_email(category, i + 1)
            username = self.generate_username(category, i + 1)
            beta_code = self.generate_beta_code()
            
            # Store user info
            self.created_users.append({
                "id": f"demo_{category}_{i+1}",
                "email": email,
                "username": username,
                "beta_code": beta_code,
                "category": category,
                "preferences": preferences,
                "created_at": datetime.utcnow().isoformat(),
                "beta_expires_at": (datetime.utcnow() + timedelta(days=90)).isoformat()
            })
            
            users_created += 1
            
            # Progress indicator
            if (i + 1) % 5 == 0:
                print(f"  Created {i + 1}/{count} users...")
        
        print(f"  ✅ Created {users_created} {category} users")
        return users_created
    
    def create_all_beta_users(self, total_count: int = 100):
        """Create all beta users"""
        print("🚀 CREATING BETA USER ACCOUNTS (DEMO)")
        print("=" * 50)
        print(f"Target: {total_count} beta users")
        
        total_created = 0
        
        # Adjust counts if total is different than 100
        scale_factor = total_count / 100
        
        for category, config in self.user_categories.items():
            adjusted_count = int(config["count"] * scale_factor)
            if adjusted_count > 0:
                created = self.create_user_batch(
                    category,
                    adjusted_count,
                    config["preferences"]
                )
                total_created += created
        
        # Save user list
        self.save_user_list()
        
        # Generate invitation data
        self.generate_invitation_data()
        
        print(f"\n✅ Total beta users created: {total_created}")
        
        return total_created
    
    def save_user_list(self):
        """Save created user list to file"""
        filename = f"beta_users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w") as f:
            json.dump({
                "created_at": datetime.now().isoformat(),
                "total_users": len(self.created_users),
                "users": self.created_users
            }, f, indent=2)
        
        print(f"\n📄 Beta user list saved to: {filename}")
    
    def generate_invitation_data(self):
        """Generate invitation data for email sending"""
        invitations = []
        
        for user in self.created_users:
            invitation = {
                "to_email": user["email"],
                "beta_code": user["beta_code"],
                "category": user["category"],
                "template_variables": {
                    "username": user["username"],
                    "beta_code": user["beta_code"],
                    "app_download_link": "https://roadtrip.app/download",
                    "support_email": "beta@roadtrip.app",
                    "beta_end_date": (datetime.utcnow() + timedelta(days=90)).strftime("%B %d, %Y")
                }
            }
            invitations.append(invitation)
        
        # Save invitation data
        filename = f"beta_invitations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w") as f:
            json.dump({
                "generated_at": datetime.now().isoformat(),
                "total_invitations": len(invitations),
                "invitations": invitations
            }, f, indent=2)
        
        print(f"📧 Invitation data saved to: {filename}")
    
    def generate_welcome_materials(self):
        """Generate welcome materials for beta users"""
        welcome_guide = """
# Welcome to AI Road Trip Storyteller Beta!

Thank you for joining our exclusive beta program. You're among the first to experience the magic of AI-powered road trips.

## Getting Started

1. **Download the App**
   - iOS: [App Store Link]
   - Android: [Google Play Link]

2. **Login with Your Beta Code**
   - Email: {email}
   - Password: {beta_code}
   - You'll be prompted to set a new password on first login

3. **Complete Onboarding**
   - Grant necessary permissions
   - Select your preferred voice personality
   - Set your travel preferences

## Beta Features to Test

### 🎯 Core Features
- Voice-first navigation
- Real-time story generation
- Smart booking assistance
- Family mode with games
- Event journey planning

### 🆕 New in Beta
- 20+ voice personalities
- Predictive suggestions
- Offline mode (limited)
- AR landmarks (iOS only)

## Providing Feedback

Your feedback is crucial! Please report:
- 🐛 Bugs or crashes
- 💡 Feature suggestions
- 🎨 UI/UX improvements
- 🗣️ Voice recognition issues

**Feedback channels:**
- In-app feedback button
- Email: beta@roadtrip.app
- Discord: [Join Beta Community]

## Beta Guidelines

- ✅ Test in various conditions (city, highway, weather)
- ✅ Try different voice commands
- ✅ Explore all features
- ✅ Share with family (up to 5 devices)
- ❌ Don't share beta code publicly
- ❌ Don't use for commercial purposes yet

## Support

Need help? We're here:
- 📧 Email: support@roadtrip.app
- 💬 In-app chat (9 AM - 6 PM PST)
- 📚 Help Center: help.roadtrip.app

## Beta Rewards

Active beta testers receive:
- 🎁 3 months free premium after launch
- 🏆 Beta tester badge in profile
- 🎟️ Early access to new features
- 💰 25% lifetime discount

Thank you for helping us create something magical!

The Road Trip Team
"""
        
        # Save welcome guide
        with open("beta_welcome_guide.md", "w") as f:
            f.write(welcome_guide)
        
        print("📚 Welcome guide generated: beta_welcome_guide.md")


def main():
    """Main function"""
    import argparse
    parser = argparse.ArgumentParser(description="Create beta user accounts (demo)")
    parser.add_argument("--count", type=int, default=100, help="Number of beta users to create")
    args = parser.parse_args()
    
    generator = BetaUserGeneratorDemo()
    
    # Create users
    total_created = generator.create_all_beta_users(args.count)
    
    # Generate welcome materials
    generator.generate_welcome_materials()
    
    print("\n" + "=" * 50)
    print("✅ BETA USER CREATION COMPLETE (DEMO)")
    print("=" * 50)
    print(f"Total users created: {total_created}")
    print("\nNext steps:")
    print("1. Review beta_users_*.json file")
    print("2. Send invitations using: python scripts/send_beta_invitations.py")
    print("3. Monitor signups in dashboard")


if __name__ == "__main__":
    main()