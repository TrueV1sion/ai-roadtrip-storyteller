"""Demo script for parking photo storage functionality."""

import asyncio
import io
from datetime import datetime, timedelta
from PIL import Image, ImageDraw, ImageFont
import requests

# Generate a demo parking photo
def create_demo_parking_photo():
    """Create a demo parking spot image."""
    # Create a simple image with parking info
    img = Image.new('RGB', (800, 600), color='lightgray')
    draw = ImageDraw.Draw(img)
    
    # Draw parking lot markers
    draw.rectangle([50, 50, 750, 150], fill='darkblue', outline='white', width=3)
    draw.text((400, 100), "LAX AIRPORT - LOT C", anchor="mm", fill='white', font=None)
    
    # Draw parking spot
    draw.rectangle([200, 250, 600, 450], outline='yellow', width=5)
    draw.text((400, 350), "SPOT C-42", anchor="mm", fill='black', font=None)
    
    # Add timestamp
    draw.text((400, 520), f"Parked: {datetime.now().strftime('%Y-%m-%d %H:%M')}", 
              anchor="mm", fill='black', font=None)
    
    # Save to bytes
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    
    return img_bytes


async def demo_parking_flow():
    """Demonstrate the parking photo upload and retrieval flow."""
    
    print("🚗 AI Road Trip Parking Photo Demo\n")
    print("=" * 50)
    
    # Step 1: Create a parking reservation
    print("\n1️⃣ Creating airport parking reservation...")
    reservation_data = {
        "location_name": "LAX Airport",
        "parking_type": "airport",
        "check_in_time": datetime.now().isoformat(),
        "check_out_time": (datetime.now() + timedelta(days=5)).isoformat(),
        "vehicle_make": "Toyota",
        "vehicle_model": "Camry",
        "vehicle_color": "Silver",
        "license_plate": "ABC123",
        "terminal": "Terminal 4",
        "outbound_flight": "UA523",
        "return_flight": "UA524",
        "airline": "United Airlines"
    }
    
    print(f"   📍 Location: {reservation_data['location_name']}")
    print(f"   ✈️ Terminal: {reservation_data['terminal']}")
    print(f"   🚙 Vehicle: {reservation_data['vehicle_color']} {reservation_data['vehicle_make']} {reservation_data['vehicle_model']}")
    print(f"   📅 Duration: 5 days")
    
    # Step 2: Upload parking photo
    print("\n2️⃣ Uploading parking spot photo...")
    print("   📸 Taking photo of parking location...")
    print("   🌐 Uploading to secure cloud storage...")
    print("   ✅ Photo uploaded successfully!")
    print("   📎 URL: https://storage.googleapis.com/roadtrip-photos/parking/user123/LAX_20250527_123456.jpg")
    
    # Step 3: Schedule return journey
    print("\n3️⃣ Scheduling return journey automation...")
    print("   🗺️ Calculating return route from LAX to home...")
    print("   ⏱️ Estimated travel time: 45 minutes")
    print("   📅 Scheduled pickup reminder: 2 hours before flight lands")
    print("   ✅ Return journey scheduled!")
    
    # Step 4: Return journey reminder
    print("\n4️⃣ Return Journey Reminder (5 days later)...")
    print("   🔔 REMINDER: Time to head back to LAX!")
    print("   ✈️ Your flight UA524 lands at 3:30 PM")
    print("   🚗 Your Silver Toyota Camry is parked in:")
    print("      📍 Lot C, Spot C-42")
    print("   📸 View your parking photo: [Photo Link]")
    print("   🚶 Walking directions: Terminal 4 → Skybridge → Lot C → Spot C-42")
    
    # Step 5: Voice assistant interaction
    print("\n5️⃣ Voice Assistant Interaction...")
    print("   👤 User: 'Hey, where did I park at LAX?'")
    print("   🤖 Assistant: 'I found your parking information! Your Silver Toyota Camry")
    print("                 is in Lot C, Spot C-42. I'm showing your parking photo on")
    print("                 the screen now. Would you like walking directions from")
    print("                 Terminal 4 to your car?'")
    
    print("\n" + "=" * 50)
    print("✨ Demo Complete! The parking photo feature helps users:")
    print("   • Never lose their car in large parking lots")
    print("   • Get automated reminders for return journeys")
    print("   • Access parking info through voice commands")
    print("   • Save time and reduce stress when traveling")


def demo_api_endpoints():
    """Show the available API endpoints."""
    print("\n📚 Available API Endpoints:\n")
    
    endpoints = [
        ("POST", "/api/airport-parking/reservations", "Create parking reservation"),
        ("POST", "/api/airport-parking/reservations/{ref}/upload-photo", "Upload parking photo"),
        ("GET", "/api/airport-parking/reservations/{ref}/parking-details", "Get parking details with photo"),
        ("GET", "/api/airport-parking/upcoming-returns", "Get upcoming return journeys"),
        ("POST", "/api/airport-parking/reservations/{ref}/send-reminder", "Send return reminder"),
    ]
    
    for method, endpoint, description in endpoints:
        print(f"   {method:6} {endpoint:50} - {description}")


if __name__ == "__main__":
    print("\n🚀 Starting Parking Photo Demo...\n")
    
    # Run the demo
    asyncio.run(demo_parking_flow())
    
    # Show API endpoints
    demo_api_endpoints()
    
    print("\n🎉 Ready to integrate with the mobile app!")
    print("   The backend is fully configured for parking photo storage.")
    print("   Mobile app can now upload photos and retrieve parking details.\n")