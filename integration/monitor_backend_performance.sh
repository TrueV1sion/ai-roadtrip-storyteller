#!/bin/bash
# Monitor backend performance during testing

# Configuration
SERVICE_NAME="roadtrip-mvp"
REGION="us-central1"
DURATION=${1:-300}  # Default 5 minutes

echo "📊 Monitoring AI Road Trip Backend Performance"
echo "============================================"
echo "Service: $SERVICE_NAME"
echo "Region: $REGION"
echo "Duration: ${DURATION}s"
echo ""

# Function to get current metrics
get_metrics() {
    echo "⏱️  $(date '+%H:%M:%S') - Fetching metrics..."
    
    # Get Cloud Run metrics
    echo ""
    echo "Cloud Run Metrics:"
    gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format="table(
            status.latestReadyRevisionName,
            status.traffic[0].percent,
            spec.template.spec.containers[0].resources.limits
        )"
    
    # Get recent request count
    echo ""
    echo "Recent Requests (last 5 minutes):"
    gcloud logging read "
        resource.type=\"cloud_run_revision\"
        AND resource.labels.service_name=\"$SERVICE_NAME\"
        AND httpRequest.requestMethod=\"POST\"
        AND timestamp>=\"$(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%S')Z\"
    " --limit=50 --format="value(httpRequest.latency,httpRequest.status)" | \
    awk '{
        count++;
        gsub(/[s]/, "", $1);
        total+=$1;
        if($2>=500) errors++;
    } END {
        if(count>0) {
            printf "  Total Requests: %d\n", count;
            printf "  Average Latency: %.2fs\n", total/count;
            printf "  Error Rate: %.1f%%\n", (errors/count)*100;
        } else {
            print "  No recent requests";
        }
    }'
    
    # Get memory usage
    echo ""
    echo "Resource Usage:"
    gcloud monitoring read \
        "resource.type=\"cloud_run_revision\" 
         AND resource.labels.service_name=\"$SERVICE_NAME\"
         AND metric.type=\"run.googleapis.com/container/memory/utilizations\"" \
        --start-time="$(date -u -d '5 minutes ago' '+%Y-%m-%dT%H:%M:%S')Z" \
        --end-time="$(date -u '+%Y-%m-%dT%H:%M:%S')Z" \
        --format="table(
            point.value.double_value.mean(),
            point.value.double_value.max()
        )" 2>/dev/null || echo "  Memory metrics not available yet"
    
    echo ""
    echo "---"
}

# Function to run a synthetic test
run_synthetic_test() {
    echo ""
    echo "🧪 Running synthetic test..."
    
    SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
        --region=$REGION \
        --format="value(status.url)")
    
    if [ -z "$SERVICE_URL" ]; then
        echo "❌ Could not get service URL"
        return
    fi
    
    # Make a test request
    START_TIME=$(date +%s.%N)
    
    RESPONSE=$(curl -s -w "\n%{http_code}" -X POST "$SERVICE_URL/api/voice-assistant/interact" \
        -H "Content-Type: application/json" \
        -d '{
            "user_input": "Performance test - what is nearby?",
            "context": {
                "current_location": {
                    "lat": 37.7749,
                    "lng": -122.4194
                }
            }
        }' 2>/dev/null)
    
    END_TIME=$(date +%s.%N)
    
    # Extract status code (last line)
    STATUS_CODE=$(echo "$RESPONSE" | tail -n 1)
    
    # Calculate response time
    RESPONSE_TIME=$(echo "$END_TIME - $START_TIME" | bc)
    
    echo "  Status: $STATUS_CODE"
    printf "  Response Time: %.2fs\n" $RESPONSE_TIME
    
    if [ "$STATUS_CODE" = "200" ]; then
        echo "  ✅ Test passed"
    else
        echo "  ❌ Test failed"
    fi
}

# Function to show real-time logs
show_logs() {
    echo ""
    echo "📜 Recent Logs (errors only):"
    gcloud run logs read \
        --service=$SERVICE_NAME \
        --region=$REGION \
        --limit=5 \
        --filter="severity>=ERROR" \
        --format="value(text)" | head -20
}

# Main monitoring loop
echo "Starting monitoring for ${DURATION}s..."
echo "Press Ctrl+C to stop"
echo ""

END_TIME=$(($(date +%s) + DURATION))

while [ $(date +%s) -lt $END_TIME ]; do
    clear
    echo "📊 AI Road Trip Backend Performance Monitor"
    echo "=========================================="
    echo "Time Remaining: $((END_TIME - $(date +%s)))s"
    echo ""
    
    get_metrics
    run_synthetic_test
    show_logs
    
    # Wait 30 seconds before next check
    sleep 30
done

echo ""
echo "✅ Monitoring complete!"
echo ""

# Generate summary report
echo "📋 Generating performance summary..."

# Get aggregated metrics for the monitoring period
echo "Performance Summary" > performance_summary.txt
echo "==================" >> performance_summary.txt
echo "Service: $SERVICE_NAME" >> performance_summary.txt
echo "Duration: ${DURATION}s" >> performance_summary.txt
echo "Time: $(date)" >> performance_summary.txt
echo "" >> performance_summary.txt

# Get request metrics
gcloud logging read "
    resource.type=\"cloud_run_revision\"
    AND resource.labels.service_name=\"$SERVICE_NAME\"
    AND httpRequest.requestMethod=\"POST\"
    AND timestamp>=\"$(date -u -d \"$DURATION seconds ago\" '+%Y-%m-%dT%H:%M:%S')Z\"
" --limit=1000 --format="value(httpRequest.latency,httpRequest.status)" | \
awk '{
    count++;
    gsub(/[s]/, "", $1);
    total+=$1;
    if($1>max || max=="") max=$1;
    if($1<min || min=="") min=$1;
    if($1<1) under1s++;
    if($1<3) under3s++;
    if($2>=500) errors++;
    if($2==200) success++;
} END {
    if(count>0) {
        print "Request Statistics:";
        print "- Total Requests:", count;
        print "- Successful (200):", success;
        print "- Errors (5xx):", errors;
        print "- Success Rate:", sprintf("%.1f%%", (success/count)*100);
        print "";
        print "Latency Statistics:";
        print "- Average:", sprintf("%.2fs", total/count);
        print "- Min:", sprintf("%.2fs", min);
        print "- Max:", sprintf("%.2fs", max);
        print "- Under 1s:", sprintf("%.1f%%", (under1s/count)*100);
        print "- Under 3s:", sprintf("%.1f%%", (under3s/count)*100);
    } else {
        print "No requests during monitoring period";
    }
}' >> performance_summary.txt

echo "" >> performance_summary.txt
echo "✅ Summary saved to: performance_summary.txt"
cat performance_summary.txt