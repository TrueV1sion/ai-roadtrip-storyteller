#!/bin/bash

# Load testing script for AI Road Trip Storyteller
# This script runs various load testing scenarios using Locust

echo "======================================"
echo "AI Road Trip Storyteller Load Testing"
echo "======================================"

# Configuration
HOST="${HOST:-http://localhost:8000}"
RESULTS_DIR="load_test_results"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Create results directory
mkdir -p $RESULTS_DIR

# Function to run a load test scenario
run_scenario() {
    local name=$1
    local users=$2
    local spawn_rate=$3
    local run_time=$4
    local user_classes=$5
    
    echo ""
    echo "Running scenario: $name"
    echo "Users: $users, Spawn rate: $spawn_rate, Duration: $run_time"
    echo "----------------------------------------"
    
    locust \
        --headless \
        --host=$HOST \
        --users=$users \
        --spawn-rate=$spawn_rate \
        --run-time=$run_time \
        --csv=$RESULTS_DIR/${name}_${TIMESTAMP} \
        --html=$RESULTS_DIR/${name}_${TIMESTAMP}.html \
        --logfile=$RESULTS_DIR/${name}_${TIMESTAMP}.log \
        -f locustfile.py \
        $user_classes
    
    echo "Scenario $name completed"
}

# Check if Locust is installed
if ! command -v locust &> /dev/null; then
    echo "Locust is not installed. Installing..."
    pip install locust
fi

# Scenario 1: Baseline Performance Test
echo ""
echo "======= SCENARIO 1: BASELINE PERFORMANCE ======="
run_scenario "baseline" 50 5 "5m" ""

# Wait between scenarios
sleep 30

# Scenario 2: Normal Load Test
echo ""
echo "======= SCENARIO 2: NORMAL LOAD ======="
run_scenario "normal_load" 200 20 "10m" ""

# Wait between scenarios
sleep 30

# Scenario 3: Peak Load Test
echo ""
echo "======= SCENARIO 3: PEAK LOAD ======="
run_scenario "peak_load" 500 50 "15m" ""

# Wait between scenarios
sleep 30

# Scenario 4: Stress Test
echo ""
echo "======= SCENARIO 4: STRESS TEST ======="
run_scenario "stress_test" 1000 100 "10m" ""

# Wait between scenarios
sleep 30

# Scenario 5: Spike Test
echo ""
echo "======= SCENARIO 5: SPIKE TEST ======="
run_scenario "spike_test" 2000 500 "5m" ""

# Wait between scenarios
sleep 30

# Scenario 6: Endurance Test (Long running)
echo ""
echo "======= SCENARIO 6: ENDURANCE TEST ======="
echo "Note: This test runs for 1 hour"
run_scenario "endurance_test" 100 10 "1h" ""

# Generate summary report
echo ""
echo "======================================"
echo "Generating Summary Report"
echo "======================================"

python3 << EOF
import os
import csv
import json
from datetime import datetime

results_dir = "$RESULTS_DIR"
timestamp = "$TIMESTAMP"
scenarios = ["baseline", "normal_load", "peak_load", "stress_test", "spike_test", "endurance_test"]

summary = {
    "test_run": timestamp,
    "host": "$HOST",
    "scenarios": {}
}

for scenario in scenarios:
    stats_file = f"{results_dir}/{scenario}_{timestamp}_stats.csv"
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            reader = csv.DictReader(f)
            stats = list(reader)
            
            # Get aggregated stats
            total_stats = next((s for s in stats if s['Name'] == 'Aggregated'), None)
            if total_stats:
                summary["scenarios"][scenario] = {
                    "total_requests": int(total_stats.get('Request Count', 0)),
                    "failure_rate": float(total_stats.get('Failure Count', 0)) / max(int(total_stats.get('Request Count', 1)), 1),
                    "avg_response_time": float(total_stats.get('Average Response Time', 0)),
                    "min_response_time": float(total_stats.get('Min Response Time', 0)),
                    "max_response_time": float(total_stats.get('Max Response Time', 0)),
                    "rps": float(total_stats.get('Requests/s', 0))
                }

# Save summary
with open(f"{results_dir}/summary_{timestamp}.json", 'w') as f:
    json.dump(summary, f, indent=2)

# Print summary
print("\nLOAD TEST SUMMARY")
print("=" * 50)
for scenario, data in summary["scenarios"].items():
    print(f"\n{scenario.upper()}:")
    print(f"  Total Requests: {data['total_requests']:,}")
    print(f"  Failure Rate: {data['failure_rate']:.2%}")
    print(f"  Avg Response Time: {data['avg_response_time']:.2f}ms")
    print(f"  Requests/Second: {data['rps']:.2f}")
EOF

echo ""
echo "======================================"
echo "Load Testing Complete"
echo "======================================"
echo "Results saved in: $RESULTS_DIR"
echo "Summary report: $RESULTS_DIR/summary_$TIMESTAMP.json"

# Open HTML reports if on desktop
if [[ "$OSTYPE" == "darwin"* ]]; then
    open $RESULTS_DIR/*_${TIMESTAMP}.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    xdg-open $RESULTS_DIR/*_${TIMESTAMP}.html 2>/dev/null || echo "HTML reports generated"
fi