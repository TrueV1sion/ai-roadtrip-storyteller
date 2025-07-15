#!/usr/bin/env python3
"""
Send Beta Invitations - Demo Version
Simulates sending personalized beta invitations
"""
import asyncio
import json
from datetime import datetime
import sys
from pathlib import Path
import glob
import random

class BetaInvitationSenderDemo:
    """Simulates sending beta invitations"""
    
    def __init__(self):
        self.sent_count = 0
        self.failed_count = 0
        self.sent_emails = []
    
    async def send_invitation(self, invitation: dict) -> bool:
        """Simulate sending a single invitation"""
        try:
            # Simulate email sending with small delay
            await asyncio.sleep(0.05)
            
            # Randomly simulate occasional failures (5% failure rate)
            if random.random() < 0.05:
                self.failed_count += 1
                return False
            
            self.sent_count += 1
            self.sent_emails.append({
                "email": invitation["to_email"],
                "category": invitation["category"],
                "sent_at": datetime.now().isoformat()
            })
            
            return True
            
        except Exception as e:
            self.failed_count += 1
            return False
    
    async def send_batch(self, invitations: list, batch_size: int = 10):
        """Send invitations in batches"""
        total = len(invitations)
        print(f"\n📮 Sending {total} invitations in batches of {batch_size}...")
        print("Simulating email delivery...\n")
        
        for i in range(0, total, batch_size):
            batch = invitations[i:i + batch_size]
            batch_num = i//batch_size + 1
            total_batches = (total + batch_size - 1)//batch_size
            
            print(f"Batch {batch_num}/{total_batches}:")
            
            # Show progress for each email in batch
            for j, inv in enumerate(batch):
                status = "✅" if random.random() > 0.05 else "❌"
                print(f"  {status} {inv['to_email']} ({inv['category']})")
            
            # Send batch concurrently
            tasks = [self.send_invitation(inv) for inv in batch]
            await asyncio.gather(*tasks)
            
            # Show batch progress
            progress = ((i + len(batch)) / total) * 100
            print(f"  Progress: {progress:.1f}% complete")
            
            # Rate limiting simulation
            if i + batch_size < total:
                print("  ⏳ Rate limiting delay...")
                await asyncio.sleep(1)
        
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
    # Find invitation file
    files = glob.glob("beta_invitations_*.json")
    if not files:
        print("❌ No invitation file found")
        print("   First run: python scripts/create_beta_users.py")
        sys.exit(1)
    
    # Use most recent file
    invitation_file = max(files)
    print(f"📂 Using invitation file: {invitation_file}")
    
    # Load invitations
    with open(invitation_file, "r") as f:
        data = json.load(f)
    
    invitations = data["invitations"]
    
    print("\n🚀 BETA INVITATION SENDER (DEMO)")
    print("=" * 50)
    print(f"Total invitations to send: {len(invitations)}")
    print(f"Categories:")
    
    # Count by category
    categories = {}
    for inv in invitations:
        cat = inv["category"]
        categories[cat] = categories.get(cat, 0) + 1
    
    for cat, count in categories.items():
        print(f"  • {cat.replace('_', ' ').title()}: {count}")
    
    sender = BetaInvitationSenderDemo()
    
    await sender.send_batch(invitations, batch_size=10)
    
    print("\n" + "=" * 50)
    print("✅ INVITATION SENDING COMPLETE (DEMO)")
    print("=" * 50)
    print(f"Successfully sent: {sender.sent_count}")
    print(f"Failed: {sender.failed_count}")
    print(f"Success rate: {sender.sent_count / len(invitations) * 100:.1f}%")
    print("\nNext step: Monitor beta usage with 'python scripts/monitor_beta_usage.py'")


if __name__ == "__main__":
    asyncio.run(main())