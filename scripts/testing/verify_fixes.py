#!/usr/bin/env python3
"""
Verification script for applied fixes
This script checks that all the fixes have been properly applied
"""

import os
import re
from pathlib import Path

def check_file_contains(file_path, search_pattern, description):
    """Check if a file contains a specific pattern"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            if re.search(search_pattern, content, re.MULTILINE | re.DOTALL):
                print(f"✅ {description}")
                return True
            else:
                print(f"❌ {description} - Pattern not found")
                return False
    except Exception as e:
        print(f"❌ {description} - Error reading file: {e}")
        return False

def verify_fixes():
    """Verify all fixes have been applied"""
    print("Verifying Test Fixes...\n")
    
    base_path = Path("/mnt/c/users/jared/onedrive/desktop/roadtrip")
    all_passed = True
    
    # 1. Game Engine Fixes
    print("1. Game Engine Fixes:")
    game_engine_path = base_path / "backend/app/services/game_engine.py"
    
    # Check for generate_question method
    all_passed &= check_file_contains(
        game_engine_path,
        r"async def generate_question\(",
        "   - generate_question method exists"
    )
    
    # Check for fallback question
    all_passed &= check_file_contains(
        game_engine_path,
        r"q_fallback_.*What is the capital of the United States",
        "   - Fallback question implementation"
    )
    
    print()
    
    # 2. Reservation Management Fixes
    print("2. Reservation Management Fixes:")
    reservation_path = base_path / "backend/app/services/reservation_management_service.py"
    
    # Check for party size validation
    all_passed &= check_file_contains(
        reservation_path,
        r"if party_size < 1 or party_size > 20:",
        "   - Party size validation (1-20)"
    )
    
    # Check for timezone handling in modify
    all_passed &= check_file_contains(
        reservation_path,
        r"# Check modification window \(ensure UTC timezone handling\)",
        "   - UTC timezone handling in modify_reservation"
    )
    
    # Check for timezone handling in cancel
    all_passed &= check_file_contains(
        reservation_path,
        r"# Ensure UTC timezone handling",
        "   - UTC timezone handling in cancel_reservation"
    )
    
    print()
    
    # 3. Spotify Service Fixes
    print("3. Spotify Service Fixes:")
    spotify_path = base_path / "backend/app/services/spotify_service.py"
    
    # Check for rate limiting
    all_passed &= check_file_contains(
        spotify_path,
        r"# Implement exponential backoff for rate limiting",
        "   - Rate limiting with exponential backoff"
    )
    
    # Check for premium user check
    all_passed &= check_file_contains(
        spotify_path,
        r"async def is_premium_user\(",
        "   - is_premium_user method exists"
    )
    
    # Check for premium check in playback
    all_passed &= check_file_contains(
        spotify_path,
        r"if not await self\.is_premium_user\(access_token\):",
        "   - Premium check in control_playback"
    )
    
    # Check for large playlist handling
    all_passed &= check_file_contains(
        spotify_path,
        r"max_tracks = 500.*Reasonable limit for journey playlists",
        "   - Large playlist handling with max_tracks limit"
    )
    
    print()
    
    # 4. API Schema Fixes
    print("4. API Schema Fixes:")
    story_schema_path = base_path / "backend/app/schemas/story.py"
    
    # Check for StoryRequest class
    all_passed &= check_file_contains(
        story_schema_path,
        r"class StoryRequest\(BaseModel\):",
        "   - StoryRequest class exists"
    )
    
    # Check for validate_story_preferences
    all_passed &= check_file_contains(
        story_schema_path,
        r"def validate_story_preferences\(cls, v\):",
        "   - validate_story_preferences method exists"
    )
    
    # Check for theme validation
    all_passed &= check_file_contains(
        story_schema_path,
        r"valid_themes = \['adventure', 'historical', 'spooky'",
        "   - Theme validation in preferences"
    )
    
    print()
    
    # 5. Location Service Check
    print("5. Location Service Check:")
    location_path = base_path / "backend/app/services/location_service.py"
    
    # Check for get_nearby_places function
    all_passed &= check_file_contains(
        location_path,
        r"async def get_nearby_places\(",
        "   - get_nearby_places function exists"
    )
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ All fixes have been successfully applied!")
    else:
        print("❌ Some fixes are missing or incomplete.")
    print("="*50)
    
    return all_passed

if __name__ == "__main__":
    verify_fixes()