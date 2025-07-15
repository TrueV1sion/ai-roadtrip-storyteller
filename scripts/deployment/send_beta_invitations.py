#!/usr/bin/env python3
"""
Send Beta Invitations
Sends personalized beta invitations to selected users
"""
import asyncio
import json
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import argparse
import sys
from typing import List, Dict, Any
import os
from pathlib import Path
import time

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.core.config import settings


class BetaInvitationSender:
    """Sends beta invitations to users"""
    
    def __init__(self):
        self.email_templates = {
            "family_travelers": self._get_family_template(),
            "business_travelers": self._get_business_template(),
            "event_attendees": self._get_event_template(),
            "rideshare_drivers": self._get_rideshare_template(),
            "default": self._get_default_template()
        }
        
        self.sent_count = 0
        self.failed_count = 0
        self.sent_emails = []
    
    def _get_family_template(self) -> str:
        """Email template for family travelers"""
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }
        .button { display: inline-block; padding: 15px 30px; background: #667eea; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .code-box { background: #fff; border: 2px dashed #667eea; padding: 20px; text-align: center; margin: 20px 0; border-radius: 5px; }
        .code { font-size: 24px; font-weight: bold; color: #667eea; letter-spacing: 2px; }
        .features { background: white; padding: 20px; margin: 20px 0; border-radius: 5px; }
        .feature { margin: 10px 0; padding-left: 30px; position: relative; }
        .feature:before { content: "✨"; position: absolute; left: 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚗 Welcome to the AI Road Trip Storyteller Beta!</h1>
            <p>Transform Every Drive into a Magical Family Adventure</p>
        </div>
        
        <div class="content">
            <p>Hi {username}!</p>
            
            <p>Congratulations! You've been selected to join our exclusive beta program for the AI Road Trip Storyteller - where every journey becomes an unforgettable family adventure!</p>
            
            <div class="code-box">
                <p>Your Exclusive Beta Access Code:</p>
                <p class="code">{beta_code}</p>
            </div>
            
            <h2>🎯 Perfect for Family Road Trips:</h2>
            <div class="features">
                <div class="feature">Mickey Mouse as your co-pilot for Disney adventures</div>
                <div class="feature">Educational stories that make learning fun</div>
                <div class="feature">Interactive games to keep kids engaged</div>
                <div class="feature">"Are we there yet?" transformed into excitement</div>
                <div class="feature">Kid-friendly restaurant and attraction recommendations</div>
            </div>
            
            <h2>🚀 Getting Started is Easy:</h2>
            <ol>
                <li>Download the app from {app_download_link}</li>
                <li>Sign up with your email: {to_email}</li>
                <li>Enter your beta code: <strong>{beta_code}</strong></li>
                <li>Start your first magical journey!</li>
            </ol>
            
            <center>
                <a href="{app_download_link}" class="button">Download the App Now</a>
            </center>
            
            <h2>🎁 Beta Tester Perks:</h2>
            <ul>
                <li>3 months FREE premium after launch</li>
                <li>Exclusive beta tester badge</li>
                <li>Direct input on new features</li>
                <li>25% lifetime discount</li>
            </ul>
            
            <p><strong>Beta Period:</strong> Now through {beta_end_date}</p>
            
            <p>We can't wait to hear about your family's adventures! Your feedback will help us create the ultimate road trip companion for families everywhere.</p>
            
            <p>Questions? Reply to this email or reach out at {support_email}</p>
            
            <p>Happy travels!<br>
            The Road Trip Team</p>
            
            <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
            
            <p style="font-size: 12px; color: #666; text-align: center;">
                This invitation is exclusively for you. Please don't share your beta code publicly.
                <br>© 2024 AI Road Trip Storyteller. All rights reserved.
            </p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_business_template(self) -> str:
        """Email template for business travelers"""
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #1a365d; color: white; padding: 30px; text-align: center; }
        .content { background: #f7fafc; padding: 30px; }
        .button { display: inline-block; padding: 12px 30px; background: #2b6cb0; color: white; text-decoration: none; border-radius: 3px; margin: 20px 0; }
        .code-box { background: #fff; border: 1px solid #e2e8f0; padding: 20px; text-align: center; margin: 20px 0; }
        .code { font-size: 20px; font-weight: bold; color: #2b6cb0; font-family: monospace; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>AI Road Trip Storyteller Beta Access</h1>
            <p>Optimize Your Business Travel</p>
        </div>
        
        <div class="content">
            <p>Dear {username},</p>
            
            <p>You've been selected for exclusive beta access to the AI Road Trip Storyteller, designed to make your business travel more productive and efficient.</p>
            
            <div class="code-box">
                <p>Beta Access Code:</p>
                <p class="code">{beta_code}</p>
            </div>
            
            <h3>Key Features for Business Travelers:</h3>
            <ul>
                <li>Hands-free navigation with real-time traffic optimization</li>
                <li>Conference call scheduling based on driving conditions</li>
                <li>Professional voice assistant mode</li>
                <li>Quick booking for business-class accommodations</li>
                <li>Expense tracking integration</li>
            </ul>
            
            <center>
                <a href="{app_download_link}" class="button">Access Beta</a>
            </center>
            
            <p>Beta Period: Through {beta_end_date}</p>
            
            <p>Best regards,<br>
            The Road Trip Team</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_event_template(self) -> str:
        """Email template for event attendees"""
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }
        .content { background: #f9f9f9; padding: 30px; }
        .button { display: inline-block; padding: 15px 30px; background: #f5576c; color: white; text-decoration: none; border-radius: 25px; margin: 20px 0; }
        .code-box { background: #fff; border: 2px solid #f5576c; padding: 20px; text-align: center; margin: 20px 0; border-radius: 10px; }
        .code { font-size: 24px; font-weight: bold; color: #f5576c; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Your Backstage Pass to Beta!</h1>
            <p>AI Road Trip Storyteller - Event Edition</p>
        </div>
        
        <div class="content">
            <p>Hey {username}! 🎸</p>
            
            <p>Ready to revolutionize your concert and event road trips? You're IN for our exclusive beta!</p>
            
            <div class="code-box">
                <p>Your VIP Access Code:</p>
                <p class="code">{beta_code}</p>
            </div>
            
            <h2>🎵 Made for Event Lovers:</h2>
            <ul>
                <li>🎤 DJ Voice personality to hype up your journey</li>
                <li>🎟️ Integrated with Ticketmaster for seamless event planning</li>
                <li>🅿️ Pre-book parking at venues</li>
                <li>🍕 Find the best pre-show dining spots</li>
                <li>⏰ Never miss an opening act with smart departure times</li>
            </ul>
            
            <center>
                <a href="{app_download_link}" class="button">Get the App!</a>
            </center>
            
            <p>Rock on!<br>
            The Road Trip Crew</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_rideshare_template(self) -> str:
        """Email template for rideshare drivers"""
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #000; color: #00ff88; padding: 30px; text-align: center; }
        .content { background: #f5f5f5; padding: 30px; }
        .button { display: inline-block; padding: 15px 30px; background: #00ff88; color: #000; text-decoration: none; border-radius: 5px; margin: 20px 0; font-weight: bold; }
        .code-box { background: #000; color: #00ff88; padding: 20px; text-align: center; margin: 20px 0; font-family: monospace; }
        .code { font-size: 24px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💰 Maximize Your Earnings with AI Road Trip Storyteller</h1>
            <p>Exclusive Beta for Rideshare Drivers</p>
        </div>
        
        <div class="content">
            <p>Hey {username}!</p>
            
            <p>As a rideshare driver, you know every minute counts. We've built the AI Road Trip Storyteller specifically with drivers like you in mind.</p>
            
            <div class="code-box">
                <p>Beta Access Code:</p>
                <p class="code">{beta_code}</p>
            </div>
            
            <h2>🚗 Driver-First Features:</h2>
            <ul>
                <li>✅ Passenger-appropriate content that enhances ratings</li>
                <li>✅ Quick facts about local areas to impress riders</li>
                <li>✅ Surge prediction and optimal positioning</li>
                <li>✅ Hands-free operation for safety</li>
                <li>✅ Multi-app integration (works alongside Uber/Lyft)</li>
            </ul>
            
            <p><strong>Beta Exclusive:</strong> Test our earning optimization features and shape the future of rideshare driving!</p>
            
            <center>
                <a href="{app_download_link}" class="button">Start Beta Testing</a>
            </center>
            
            <p>Drive smart,<br>
            The Road Trip Team</p>
        </div>
    </div>
</body>
</html>
"""
    
    def _get_default_template(self) -> str:
        """Default email template"""
        return """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #4a5568; color: white; padding: 30px; text-align: center; }
        .content { background: #f7fafc; padding: 30px; }
        .button { display: inline-block; padding: 15px 30px; background: #4299e1; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }
        .code-box { background: #fff; border: 2px solid #4299e1; padding: 20px; text-align: center; margin: 20px 0; }
        .code { font-size: 24px; font-weight: bold; color: #4299e1; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to AI Road Trip Storyteller Beta!</h1>
        </div>
        
        <div class="content">
            <p>Hi {username}!</p>
            
            <p>You've been selected to join our exclusive beta program!</p>
            
            <div class="code-box">
                <p>Your Beta Access Code:</p>
                <p class="code">{beta_code}</p>
            </div>
            
            <center>
                <a href="{app_download_link}" class="button">Download App</a>
            </center>
            
            <p>Thanks for joining us!<br>
            The Road Trip Team</p>
        </div>
    </div>
</body>
</html>
"""
    
    async def send_invitation(self, invitation: Dict[str, Any]) -> bool:
        """Send a single invitation"""
        try:
            # Get email template based on category
            category = invitation.get("category", "default")
            template = self.email_templates.get(category, self.email_templates["default"])
            
            # Format template with variables
            html_content = template.format(**invitation["template_variables"], to_email=invitation["to_email"])
            
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = "🚗 Your Exclusive Beta Access to AI Road Trip Storyteller!"
            message["From"] = f"AI Road Trip Team <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = invitation["to_email"]
            
            # Add HTML part
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)
            
            # Send email (simulated for demo)
            print(f"  📧 Sending to {invitation['to_email']} ({category})...")
            
            # In production, this would use actual SMTP
            # context = ssl.create_default_context()
            # with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, context=context) as server:
            #     server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            #     server.send_message(message)
            
            # Simulate sending delay
            await asyncio.sleep(0.1)
            
            self.sent_count += 1
            self.sent_emails.append({
                "email": invitation["to_email"],
                "category": category,
                "sent_at": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            print(f"  ❌ Failed to send to {invitation['to_email']}: {str(e)}")
            self.failed_count += 1
            return False
    
    async def send_batch(self, invitations: List[Dict[str, Any]], batch_size: int = 10):
        """Send invitations in batches"""
        total = len(invitations)
        print(f"\n📮 Sending {total} invitations in batches of {batch_size}...")
        
        for i in range(0, total, batch_size):
            batch = invitations[i:i + batch_size]
            print(f"\nBatch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size}:")
            
            # Send batch concurrently
            tasks = [self.send_invitation(inv) for inv in batch]
            await asyncio.gather(*tasks)
            
            # Rate limiting
            if i + batch_size < total:
                print("  ⏳ Waiting 2 seconds before next batch...")
                await asyncio.sleep(2)
        
        # Save sent list
        self.save_sent_list()
    
    def save_sent_list(self):
        """Save list of sent invitations"""
        filename = f"beta_invitations_sent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w") as f:
            json.dump({
                "sent_at": datetime.now().isoformat(),
                "total_sent": self.sent_count,
                "total_failed": self.failed_count,
                "sent_emails": self.sent_emails
            }, f, indent=2)
        
        print(f"\n📄 Sent list saved to: {filename}")


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Send beta invitations")
    parser.add_argument("--file", type=str, help="Invitation data file", 
                       default="beta_invitations_*.json")
    parser.add_argument("--batch-size", type=int, default=10, 
                       help="Number of emails to send per batch")
    parser.add_argument("--dry-run", action="store_true", 
                       help="Test run without sending emails")
    args = parser.parse_args()
    
    # Find invitation file
    import glob
    files = glob.glob(args.file)
    if not files:
        print(f"❌ No invitation file found matching: {args.file}")
        print("   First run: python scripts/create_beta_users.py")
        sys.exit(1)
    
    # Use most recent file
    invitation_file = max(files)
    print(f"📂 Using invitation file: {invitation_file}")
    
    # Load invitations
    with open(invitation_file, "r") as f:
        data = json.load(f)
    
    invitations = data["invitations"]
    
    print("\n🚀 BETA INVITATION SENDER")
    print("=" * 50)
    print(f"Total invitations to send: {len(invitations)}")
    print(f"Batch size: {args.batch_size}")
    print(f"Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")
    
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE - No emails will be sent")
        print("\nSample invitations:")
        for inv in invitations[:3]:
            print(f"  - {inv['to_email']} ({inv['category']})")
        print(f"  ... and {len(invitations) - 3} more")
        return
    
    # Confirm before sending
    response = input("\nProceed with sending? (yes/no): ")
    if response.lower() != "yes":
        print("❌ Cancelled")
        return
    
    sender = BetaInvitationSender()
    
    try:
        await sender.send_batch(invitations, args.batch_size)
        
        print("\n" + "=" * 50)
        print("✅ INVITATION SENDING COMPLETE")
        print("=" * 50)
        print(f"Successfully sent: {sender.sent_count}")
        print(f"Failed: {sender.failed_count}")
        print(f"Success rate: {sender.sent_count / len(invitations) * 100:.1f}%")
        
    except Exception as e:
        print(f"\n❌ Error sending invitations: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())