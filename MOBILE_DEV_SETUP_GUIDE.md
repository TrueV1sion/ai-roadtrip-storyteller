# Mobile Development Control Setup Guide

## 🎯 Overview

The Mobile Development Control system allows you to monitor and control development progress remotely via SMS. You can receive notifications about build status, deployment progress, security alerts, and respond with commands to approve actions, pause/resume development, or trigger deployments.

## 📱 Features

### **Notifications You'll Receive**
- 🚀 **Build Status** - Success/failure notifications
- 🔒 **Security Alerts** - Critical security issues
- 📋 **Task Completion** - When development tasks finish
- ⚠️ **Approval Requests** - Actions requiring your approval
- 📊 **System Status** - Health and performance updates
- 🚨 **Critical Errors** - Immediate attention required

### **SMS Commands You Can Send**
- `status` - Get current development status
- `approve` or `yes` - Approve pending actions
- `reject` or `no` - Reject pending actions  
- `pause` or `stop` - Pause development
- `resume` - Resume development
- `deploy` - Trigger production deployment
- `rollback` - Rollback to previous version
- `help` - Show available commands

## 🔧 Setup Instructions

### **Step 1: Configure Your Phone Number**

Add your phone number to the environment configuration:

```bash
# Add to your .env file
DEV_AUTHORIZED_PHONES="+1234567890,+0987654321"  # Your phone number(s)
```

### **Step 2: Choose SMS Provider**

Select one of the supported SMS providers:

#### **Option A: Twilio (Recommended)**
```bash
# Add to .env
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

**Setup Steps:**
1. Sign up at [twilio.com](https://twilio.com)
2. Get a phone number
3. Configure webhook URL: `https://yourdomain.com/api/mobile-dev/webhook/twilio-sms`

#### **Option B: AWS SNS**
```bash
# Add to .env
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

**Setup Steps:**
1. Configure AWS SNS in your region
2. Set up SMS topic
3. Configure webhook URL: `https://yourdomain.com/api/mobile-dev/webhook/aws-sns`

#### **Option C: Google Cloud SMS**
```bash
# Add to .env
GOOGLE_CLOUD_PROJECT=your-project-id
# Uses existing Google Cloud credentials
```

### **Step 3: Configure Webhooks**

Set up webhooks to receive SMS responses:

#### **Twilio Webhook Setup**
1. Go to Twilio Console → Phone Numbers
2. Select your SMS number
3. Set webhook URL: `https://yourdomain.com/api/mobile-dev/webhook/twilio-sms`
4. Set HTTP method: `POST`

#### **AWS SNS Webhook Setup**
1. Create SNS topic for SMS responses
2. Subscribe webhook URL: `https://yourdomain.com/api/mobile-dev/webhook/aws-sns`
3. Confirm subscription

### **Step 4: Test the System**

Send a test notification:

```bash
curl -X POST https://yourdomain.com/api/mobile-dev/test-notification \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "system_status",
    "title": "Test Mobile Notification",
    "message": "This is a test notification. Reply with \"status\" to test SMS commands.",
    "priority": "medium",
    "phone_number": "+1234567890"
  }'
```

## 🔄 Usage Examples

### **Typical Development Flow**

#### **1. Receive Build Notification**
```
🚨 Build Failed

Unit tests failed in payment processing module. 
3 tests failing, 2 new errors detected.

Reply with action or 'help' for options
```

#### **2. Check Status**
Send: `status`

Receive:
```
🚀 Development Status:
• Environment: development
• Last Deploy: 2024-01-15 10:30 UTC
• Active Tasks: 2
• System Health: healthy
• Pending Approvals: 1
```

#### **3. Receive Approval Request**
```
⚠️ Approval Required: Production Deployment

Deploy v1.2.0 to production environment.
Security audit passed, all tests green.
Estimated downtime: 2 minutes.

Reply 'approve' or 'reject' (timeout: 30m)
```

#### **4. Approve Deployment**
Send: `approve`

Receive:
```
✅ Approved: Production Deployment

Deployment initiated. You'll receive status updates.
```

#### **5. Monitor Deployment**
```
📊 Workflow Progress: Production Deployment
Step 3/7 complete (43%)

Current: Building production image
Next: Deploy to staging
```

#### **6. Deployment Complete**
```
🎉 Task Complete

Workflow: Production Deployment completed successfully (took 8m 32s)

Production URL: https://roadtrip.com
Health check: ✅ All systems operational
```

### **Emergency Scenarios**

#### **Critical Security Alert**
```
🔥 Security Alert: Exposed API Keys

Google Maps API key detected in public repository.
Immediate action required - credential rotation recommended.

Reply 'approve' to start automatic rotation
```

#### **Emergency Rollback**
```
🚨 Critical Error: Database Connection Failed

Production system experiencing database connectivity issues.
Current error rate: 95%

Reply 'rollback' for immediate rollback to v1.1.9
```

Send: `rollback`

Receive:
```
🔄 Rollback to previous initiated.

Stopping current services...
Restoring previous version...
All systems restored. Error rate: 0%
```

## 🛠️ Advanced Configuration

### **Custom Notification Mapping**
```bash
# Map phone numbers to email addresses for fallback
DEV_PHONE_EMAIL_MAPPING='{""+1234567890"": ""dev@company.com""}'
```

### **Priority Filtering**
```bash
# Only send high/critical priority notifications
DEV_NOTIFICATION_MIN_PRIORITY=high
```

### **Response Timeouts**
```bash
# Default timeout for approval requests (minutes)
DEV_APPROVAL_TIMEOUT=30
```

### **Development Hours**
```bash
# Only send notifications during these hours (24h format)
DEV_NOTIFICATION_HOURS=09:00-18:00
DEV_NOTIFICATION_TIMEZONE=America/New_York
```

## 📊 Monitoring & Logs

### **Check Service Status**
```bash
curl -X GET https://yourdomain.com/api/mobile-dev/status \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### **View Notification History**
```bash
# Check logs for sent notifications
docker logs roadtrip-api | grep "Development notification sent"
```

### **Test SMS Commands**
```bash
# Simulate SMS response for testing
curl -X POST https://yourdomain.com/api/mobile-dev/simulate-sms-response \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+1234567890",
    "message": "status"
  }'
```

## 🔒 Security Considerations

### **Phone Number Verification**
- Only authorized phone numbers can send commands
- Commands from unknown numbers are logged and ignored
- Consider implementing 2FA for sensitive commands

### **Webhook Security**
- Verify webhook signatures (Twilio) or use HTTPS
- Implement rate limiting on webhook endpoints
- Log all incoming messages for audit trails

### **Command Restrictions**
- Critical commands (deploy, rollback) require approval
- Emergency commands bypass normal approval workflows
- All commands are logged with timestamps and source

## 🚨 Troubleshooting

### **Not Receiving SMS Notifications**
1. Check phone number format (include country code)
2. Verify SMS provider credentials
3. Check webhook configuration
4. Review application logs for errors

### **SMS Commands Not Working**
1. Verify your number is in `DEV_AUTHORIZED_PHONES`
2. Check webhook URL is accessible
3. Test with simple commands like `help` first
4. Review webhook logs for parsing errors

### **Provider-Specific Issues**

#### **Twilio Issues**
- Verify account has SMS enabled
- Check message logs in Twilio console
- Ensure webhook URL uses HTTPS

#### **AWS SNS Issues**
- Verify IAM permissions for SNS
- Check SNS topic configuration
- Ensure region matches configuration

### **Emergency Fallback**
If SMS system fails, you can still control development via:
1. Direct API calls with admin token
2. Server SSH access
3. Cloud console interfaces
4. Email notifications (if configured)

## 📞 Support

If you encounter issues:
1. Check the application logs: `docker logs roadtrip-api`
2. Verify webhook connectivity: Test webhook URLs
3. Test with curl commands for API debugging
4. Check SMS provider status pages

---

**Remember**: This system gives you powerful remote control over your development environment. Use commands carefully, especially `deploy` and `rollback` in production environments.

The mobile development control system ensures you stay connected to your development progress even when away from your laptop, allowing for continuous development momentum and quick response to critical issues.