#!/usr/bin/env python3
"""
Set up alert notification channels for production monitoring.
This script configures Slack, PagerDuty, and email notifications.
"""
import os
import sys
import json
import argparse
from google.cloud import secretmanager
from pathlib import Path
import yaml


def create_notification_secrets(project_id: str, dry_run: bool = False):
    """Create secrets for notification channels in Google Secret Manager."""
    
    secrets_to_create = {
        "roadtrip-smtp-password": {
            "description": "SMTP password for alert emails",
            "value": os.getenv("SMTP_PASSWORD", "PLACEHOLDER_SMTP_PASSWORD")
        },
        "roadtrip-slack-webhook": {
            "description": "Slack webhook URL for alerts",
            "value": os.getenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/YOUR/WEBHOOK/URL")
        },
        "roadtrip-pagerduty-key": {
            "description": "PagerDuty service key for critical alerts",
            "value": os.getenv("PAGERDUTY_SERVICE_KEY", "PLACEHOLDER_PAGERDUTY_KEY")
        }
    }
    
    if not dry_run:
        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{project_id}"
    
    created_secrets = []
    
    for secret_id, config in secrets_to_create.items():
        if dry_run:
            print(f"[DRY RUN] Would create secret: {secret_id}")
            print(f"  Description: {config['description']}")
            created_secrets.append(secret_id)
        else:
            try:
                secret_name = f"{parent}/secrets/{secret_id}"
                
                # Try to get the secret first
                try:
                    client.get_secret(request={"name": secret_name})
                    print(f"Secret {secret_id} already exists")
                    continue
                except Exception:
                    pass
                
                # Create the secret
                secret = client.create_secret(
                    request={
                        "parent": parent,
                        "secret_id": secret_id,
                        "secret": {
                            "replication": {"automatic": {}},
                            "labels": {
                                "app": "roadtrip",
                                "purpose": "monitoring",
                                "service": "alerting"
                            }
                        },
                    }
                )
                
                # Add the secret version
                version = client.add_secret_version(
                    request={
                        "parent": secret.name,
                        "payload": {"data": config['value'].encode("UTF-8")},
                    }
                )
                
                print(f"Created secret: {secret_id}")
                created_secrets.append(secret_id)
                
            except Exception as e:
                print(f"Error creating secret {secret_id}: {e}")
    
    return created_secrets


def create_alertmanager_config(project_id: str, output_path: str):
    """Create AlertManager configuration with proper secret references."""
    
    config = {
        "global": {
            "smtp_smarthost": "smtp.gmail.com:587",
            "smtp_from": "alerts@roadtrip.app",
            "smtp_auth_username": "alerts@roadtrip.app",
            "smtp_auth_password_file": "/etc/alertmanager/secrets/smtp-password",
            "smtp_require_tls": True,
            "slack_api_url_file": "/etc/alertmanager/secrets/slack-webhook",
            "resolve_timeout": "5m"
        },
        "templates": ["/etc/alertmanager/templates/*.tmpl"],
        "route": {
            "receiver": "default",
            "group_by": ["alertname", "cluster", "service"],
            "group_wait": "30s",
            "group_interval": "5m",
            "repeat_interval": "12h",
            "routes": [
                {
                    "match": {"severity": "critical"},
                    "receiver": "pagerduty-critical",
                    "group_wait": "10s",
                    "repeat_interval": "30m"
                },
                {
                    "match": {"service": "security"},
                    "receiver": "security-team",
                    "group_wait": "10s",
                    "repeat_interval": "1h"
                },
                {
                    "match": {"service": "business"},
                    "receiver": "business-team",
                    "repeat_interval": "6h"
                },
                {
                    "match": {"service": "infrastructure"},
                    "receiver": "devops-team"
                },
                {
                    "match": {"service": "database"},
                    "receiver": "database-team",
                    "group_wait": "1m"
                }
            ]
        },
        "inhibit_rules": [
            {
                "source_match": {"severity": "critical"},
                "target_match": {"severity": "warning"},
                "equal": ["alertname", "dev", "instance"]
            }
        ],
        "receivers": [
            {
                "name": "default",
                "slack_configs": [{
                    "channel": "#roadtrip-alerts",
                    "title": "AI Road Trip Alert",
                    "icon_emoji": ":rotating_light:",
                    "send_resolved": True
                }]
            },
            {
                "name": "pagerduty-critical",
                "pagerduty_configs": [{
                    "service_key_file": "/etc/alertmanager/secrets/pagerduty-key",
                    "description": "{{ .GroupLabels.alertname }}: {{ .Annotations.summary }}",
                    "severity": "critical",
                    "client": "AI Road Trip Storyteller"
                }],
                "slack_configs": [{
                    "channel": "#roadtrip-critical",
                    "title": "CRITICAL: {{ .GroupLabels.alertname }}",
                    "color": "danger"
                }]
            },
            {
                "name": "security-team",
                "email_configs": [{
                    "to": "security@roadtrip.app",
                    "headers": {"Subject": "Security Alert: {{ .GroupLabels.alertname }}"}
                }],
                "slack_configs": [{
                    "channel": "#security-alerts",
                    "title": "Security: {{ .GroupLabels.alertname }}",
                    "color": "warning"
                }]
            },
            {
                "name": "business-team",
                "slack_configs": [{
                    "channel": "#business-metrics",
                    "title": "Business Alert: {{ .GroupLabels.alertname }}",
                    "send_resolved": True
                }]
            },
            {
                "name": "devops-team",
                "slack_configs": [{
                    "channel": "#devops",
                    "title": "Infrastructure: {{ .GroupLabels.alertname }}",
                    "send_resolved": True
                }]
            },
            {
                "name": "database-team",
                "email_configs": [{
                    "to": "dba@roadtrip.app",
                    "headers": {"Subject": "Database Alert: {{ .GroupLabels.alertname }}"}
                }],
                "slack_configs": [{
                    "channel": "#database-alerts",
                    "title": "Database: {{ .GroupLabels.alertname }}",
                    "color": "danger"
                }]
            }
        ]
    }
    
    # Write configuration
    with open(output_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    print(f"Created AlertManager configuration at: {output_path}")


def create_notification_test_script(output_path: str):
    """Create a script to test notification channels."""
    
    test_script = '''#!/bin/bash
# Test notification channels for AI Road Trip Storyteller

echo "Testing notification channels..."

# Test Slack webhook
echo "Testing Slack..."
curl -X POST $SLACK_WEBHOOK_URL \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "Test alert from AI Road Trip Storyteller monitoring setup",
    "channel": "#roadtrip-alerts",
    "username": "AlertManager Test",
    "icon_emoji": ":white_check_mark:"
  }'

# Test email (requires SMTP configured)
echo -e "\\nTesting email..."
echo "Subject: Test Alert - AI Road Trip Storyteller\\n\\nThis is a test alert from the monitoring setup." | \
  sendmail -f alerts@roadtrip.app security@roadtrip.app

# Test PagerDuty (if configured)
if [ ! -z "$PAGERDUTY_SERVICE_KEY" ]; then
  echo -e "\\nTesting PagerDuty..."
  curl -X POST https://events.pagerduty.com/v2/enqueue \
    -H 'Content-Type: application/json' \
    -d "{
      \\"routing_key\\": \\"$PAGERDUTY_SERVICE_KEY\\",
      \\"event_action\\": \\"trigger\\",
      \\"payload\\": {
        \\"summary\\": \\"Test alert from AI Road Trip Storyteller\\",
        \\"severity\\": \\"info\\",
        \\"source\\": \\"monitoring-setup\\"
      }
    }"
fi

echo -e "\\n\\nNotification channel tests completed!"
'''
    
    with open(output_path, 'w') as f:
        f.write(test_script)
    
    os.chmod(output_path, 0o755)
    print(f"Created notification test script at: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='Set up alert notification channels')
    parser.add_argument('--project-id', required=True, help='GCP Project ID')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be done')
    parser.add_argument('--skip-secrets', action='store_true', help='Skip creating secrets')
    args = parser.parse_args()
    
    print("Setting up alert notification channels...")
    
    # Create notification secrets
    if not args.skip_secrets:
        secrets = create_notification_secrets(args.project_id, args.dry_run)
        print(f"\nCreated {len(secrets)} notification secrets")
    
    # Create AlertManager configuration
    if not args.dry_run:
        config_path = "infrastructure/monitoring/alertmanager-config-production.yaml"
        create_alertmanager_config(args.project_id, config_path)
        
        # Create test script
        test_script_path = "scripts/monitoring/test_notifications.sh"
        create_notification_test_script(test_script_path)
    
    print("\n=== Next Steps ===")
    print("1. Update the placeholder values in Google Secret Manager:")
    print("   - roadtrip-smtp-password: Your SMTP password")
    print("   - roadtrip-slack-webhook: Your Slack webhook URL") 
    print("   - roadtrip-pagerduty-key: Your PagerDuty service key")
    print("\n2. Deploy AlertManager with the new configuration")
    print("\n3. Test notifications:")
    print("   export SLACK_WEBHOOK_URL='your-webhook-url'")
    print("   export PAGERDUTY_SERVICE_KEY='your-service-key'")
    print("   ./scripts/monitoring/test_notifications.sh")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())