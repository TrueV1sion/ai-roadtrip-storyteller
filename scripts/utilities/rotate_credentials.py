#!/usr/bin/env python3
"""
Emergency Security Response - Credential Rotation Script
This script generates new secure credentials for immediate use
"""

import os
import secrets
import string
import json
from datetime import datetime
from pathlib import Path


def generate_secure_password(length=32):
    """Generate a cryptographically secure password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_secure_key(length=32):
    """Generate a secure key for JWT/SECRET_KEY"""
    return secrets.token_urlsafe(length)


def create_new_credentials():
    """Generate all new credentials"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    credentials = {
        "timestamp": timestamp,
        "database": {
            "username": "roadtrip_prod",
            "password": generate_secure_password(32),
            "database": "roadtrip_production"
        },
        "redis": {
            "password": generate_secure_password(24)
        },
        "security": {
            "secret_key": generate_secure_key(32),
            "jwt_secret_key": generate_secure_key(32)
        },
        "admin": {
            "grafana_password": generate_secure_password(16)
        }
    }
    
    return credentials


def save_credentials(credentials):
    """Save credentials to a secure location"""
    output_dir = Path("./credentials_backup")
    output_dir.mkdir(exist_ok=True)
    
    # Save to JSON file
    output_file = output_dir / f"new_credentials_{credentials['timestamp']}.json"
    with open(output_file, 'w') as f:
        json.dump(credentials, f, indent=2)
    
    # Create .env.new file
    env_file = output_dir / f".env.new_{credentials['timestamp']}"
    with open(env_file, 'w') as f:
        f.write(f"""# Generated on {credentials['timestamp']}
# CRITICAL: Update these in Google Secret Manager immediately

# Database
DATABASE_URL=postgresql://{credentials['database']['username']}:{credentials['database']['password']}@localhost:5432/{credentials['database']['database']}

# Redis
REDIS_URL=redis://:{credentials['redis']['password']}@localhost:6379

# Security Keys
SECRET_KEY={credentials['security']['secret_key']}
JWT_SECRET_KEY={credentials['security']['jwt_secret_key']}

# Admin Passwords
GRAFANA_ADMIN_PASSWORD={credentials['admin']['grafana_password']}
""")
    
    print(f"✅ New credentials generated and saved to:")
    print(f"   - {output_file}")
    print(f"   - {env_file}")
    
    return output_file, env_file


def generate_sql_commands(credentials):
    """Generate SQL commands to update database credentials"""
    sql_file = Path("./credentials_backup") / f"update_db_credentials_{credentials['timestamp']}.sql"
    
    with open(sql_file, 'w') as f:
        f.write(f"""-- Execute these commands to update database credentials
-- Generated on {credentials['timestamp']}

-- Update user password
ALTER USER {credentials['database']['username']} WITH PASSWORD '{credentials['database']['password']}';

-- If user doesn't exist, create it
-- CREATE USER {credentials['database']['username']} WITH PASSWORD '{credentials['database']['password']}';
-- GRANT ALL PRIVILEGES ON DATABASE {credentials['database']['database']} TO {credentials['database']['username']};

-- Verify the change
-- \\du {credentials['database']['username']}
""")
    
    print(f"✅ SQL commands saved to: {sql_file}")
    return sql_file


def create_security_checklist():
    """Create a checklist for manual tasks"""
    checklist_file = Path("./credentials_backup") / "SECURITY_ROTATION_CHECKLIST.md"
    
    with open(checklist_file, 'w') as f:
        f.write("""# Security Credential Rotation Checklist

## Immediate Actions Required

### 1. API Key Rotation (Manual - Do Now!)

#### Google Maps API
- [ ] Log into https://console.cloud.google.com
- [ ] Navigate to APIs & Services > Credentials
- [ ] Create new API key with name "roadtrip-prod-{date}"
- [ ] Set application restrictions (HTTP referrers)
- [ ] Copy new key to secure location
- [ ] Delete/disable old key: AIzaSyAuduVqyKAf47TAZkCd9j4dnDd87oaLXYQ

#### Ticketmaster API
- [ ] Log into https://developer.ticketmaster.com
- [ ] Navigate to My Apps
- [ ] Generate new API key
- [ ] Copy new key and secret
- [ ] Disable old key: 5X13jI3ZPzAdU3kp3trYFf4VWqSVySgo

#### OpenWeatherMap API
- [ ] Log into https://openweathermap.org/api
- [ ] Generate new API key
- [ ] Copy new key
- [ ] Delete old key: d7aa0dc75ed0dae38f627ed48d3e3bf1

### 2. Database Credentials
- [ ] Execute SQL commands from update_db_credentials_*.sql
- [ ] Update all application connection strings
- [ ] Test database connections
- [ ] Update backup scripts with new credentials

### 3. Redis Password
- [ ] Update redis.conf with new password
- [ ] Restart Redis service
- [ ] Update all application Redis URLs
- [ ] Test Redis connections

### 4. Application Secrets
- [ ] Update SECRET_KEY in all environments
- [ ] Update JWT_SECRET_KEY in all environments
- [ ] Force logout all users (security measure)
- [ ] Update documentation

### 5. Google Secret Manager Migration
- [ ] Enable Secret Manager API in GCP
- [ ] Create all secrets in Secret Manager
- [ ] Update application to use Secret Manager
- [ ] Remove local .env files

### 6. Repository Cleanup
- [ ] Remove .env from git history using BFG
- [ ] Force push to all branches
- [ ] Notify all developers to re-clone

### 7. Monitoring
- [ ] Update Grafana admin password
- [ ] Configure alerts for unauthorized access
- [ ] Enable audit logging
- [ ] Review access logs

## Verification Steps
- [ ] All services operational with new credentials
- [ ] No references to old credentials in codebase
- [ ] Security scan shows no exposed secrets
- [ ] Team notified of changes

## Emergency Contacts
- Security Lead: [UPDATE WITH ACTUAL CONTACT]
- DevOps On-Call: [UPDATE WITH ACTUAL CONTACT]
- Executive Escalation: [UPDATE WITH ACTUAL CONTACT]

Generated on: {timestamp}
""".format(date=datetime.now().strftime("%Y%m%d"), timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    print(f"✅ Security checklist saved to: {checklist_file}")
    return checklist_file


def main():
    print("🔐 AI Road Trip Storyteller - Emergency Credential Rotation")
    print("=" * 60)
    
    # Generate new credentials
    print("\n📝 Generating new secure credentials...")
    credentials = create_new_credentials()
    
    # Save credentials
    json_file, env_file = save_credentials(credentials)
    
    # Generate SQL commands
    sql_file = generate_sql_commands(credentials)
    
    # Create checklist
    checklist = create_security_checklist()
    
    print("\n" + "=" * 60)
    print("⚠️  CRITICAL SECURITY ACTIONS REQUIRED:")
    print("1. Manually rotate all API keys (see checklist)")
    print("2. Update database password using SQL commands")
    print("3. Configure Redis password")
    print("4. Migrate to Google Secret Manager")
    print("5. Clean git history of exposed secrets")
    print("\n🚨 All old credentials should be considered COMPROMISED")
    print("=" * 60)
    
    # Create a secure backup notice
    notice_file = Path("./credentials_backup") / "DO_NOT_COMMIT_THIS_FOLDER.txt"
    with open(notice_file, 'w') as f:
        f.write("This folder contains sensitive credentials.\n")
        f.write("NEVER commit this folder to version control.\n")
        f.write("Move these credentials to a password manager immediately.\n")


if __name__ == "__main__":
    main()