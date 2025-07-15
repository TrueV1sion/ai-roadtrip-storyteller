#!/bin/bash
# Mobile Testing Checklist Script
# Interactive script to guide through mobile testing

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BLUE='\033[0;34m'

# Test results
PASSED=0
FAILED=0
TOTAL=0

echo "🚗 AI Road Trip MVP - Mobile Testing Checklist"
echo "=============================================="
echo ""

# Get tester info
read -p "Tester Name: " TESTER_NAME
read -p "Device Type (iOS/Android): " DEVICE_TYPE
read -p "Device Model: " DEVICE_MODEL
read -p "OS Version: " OS_VERSION
read -p "Backend URL: " BACKEND_URL

echo ""
echo "Test Date: $(date)"
echo "Device: $DEVICE_TYPE - $DEVICE_MODEL ($OS_VERSION)"
echo "Backend: $BACKEND_URL"
echo ""
echo "Starting tests..."
echo ""

# Function to run a test
run_test() {
    local test_name="$1"
    local test_desc="$2"
    
    echo -e "${BLUE}Test $((TOTAL + 1)): $test_name${NC}"
    echo "Description: $test_desc"
    echo ""
    
    read -p "Did the test pass? (y/n/s to skip): " result
    
    case $result in
        [Yy]* )
            echo -e "${GREEN}✓ PASSED${NC}"
            ((PASSED++))
            ((TOTAL++))
            echo "$test_name: PASSED" >> test_results.log
            ;;
        [Nn]* )
            echo -e "${RED}✗ FAILED${NC}"
            read -p "Enter failure reason: " reason
            echo "$test_name: FAILED - $reason" >> test_results.log
            ((FAILED++))
            ((TOTAL++))
            ;;
        [Ss]* )
            echo -e "${YELLOW}⊘ SKIPPED${NC}"
            echo "$test_name: SKIPPED" >> test_results.log
            ;;
    esac
    
    echo ""
    echo "---"
    echo ""
}

# Initialize log file
echo "AI Road Trip MVP Mobile Test Results" > test_results.log
echo "====================================" >> test_results.log
echo "Tester: $TESTER_NAME" >> test_results.log
echo "Date: $(date)" >> test_results.log
echo "Device: $DEVICE_TYPE - $DEVICE_MODEL ($OS_VERSION)" >> test_results.log
echo "Backend: $BACKEND_URL" >> test_results.log
echo "" >> test_results.log

# Test 1: App Launch
run_test "App Launch" \
"1. Fresh install the app
2. Launch the app
3. Measure time to interactive
4. Check for crashes

Target: <3 seconds launch time"

# Test 2: Permissions
run_test "Permission Handling" \
"1. Accept location permission when prompted
2. Accept microphone permission when prompted
3. Verify permissions are saved
4. Check app behavior if denied

Both permissions should be requested appropriately"

# Test 3: Initial UI
run_test "Initial UI State" \
"1. Map shows current location
2. Voice button is visible and centered
3. UI elements are not cut off
4. No loading indicators stuck

All UI elements should be properly displayed"

# Test 4: Voice Recognition
run_test "Voice Recognition Activation" \
"1. Tap the voice button
2. See 'Listening...' indicator
3. Button changes color/state
4. Microphone activates

Voice recognition should start within 500ms"

# Test 5: Simple Navigation
run_test "Navigation Command" \
"1. Tap voice button
2. Say: 'Navigate to the nearest coffee shop'
3. Release button or wait for auto-stop
4. Observe processing indicator

Should show 'Processing your request...'"

# Test 6: Response Time
run_test "Backend Response Time" \
"1. Time from end of speech to response
2. Story text should appear
3. Audio should start playing
4. Map should show route

Target: <3 seconds total response time"

# Test 7: Story Quality
run_test "Story Content Quality" \
"1. Story is relevant to request
2. Text is readable and formatted
3. Story length is appropriate
4. Content is engaging

Story should be relevant and interesting"

# Test 8: Audio Playback
run_test "Audio Playback" \
"1. Audio plays automatically
2. Audio matches displayed text
3. Stop button works
4. Audio quality is clear

Audio should work through speaker and headphones"

# Test 9: Map Functionality
run_test "Map Route Display" \
"1. Route appears on map
2. Start and end markers visible
3. Route line is clear
4. Map can be panned/zoomed

Route should be accurate and visible"

# Test 10: Location Tracking
run_test "GPS Location Updates" \
"1. Walk/drive a short distance
2. Map updates location
3. Blue dot follows movement
4. No lag or jumping

Location should update smoothly"

# Test 11: Story Request
run_test "Non-Navigation Story" \
"1. Tap voice button
2. Say: 'Tell me about the history of this area'
3. Wait for response
4. Check story relevance

Should receive location-specific historical story"

# Test 12: Error Handling - No Internet
run_test "Offline Behavior" \
"1. Turn on airplane mode
2. Try a voice command
3. Check error message
4. Turn internet back on and retry

Should show clear error message"

# Test 13: Invalid Input
run_test "Invalid Command Handling" \
"1. Say gibberish or unclear command
2. Check response
3. App should not crash
4. Should ask for clarification

Should handle gracefully with helpful response"

# Test 14: Multiple Requests
run_test "Sequential Requests" \
"1. Make 5 different voice requests
2. Mix navigation and story requests
3. Check each response
4. Monitor app performance

All requests should be handled correctly"

# Test 15: Background/Foreground
run_test "App State Transitions" \
"1. Start audio playing
2. Switch to another app
3. Return to Road Trip app
4. Check if audio continued

App should handle backgrounding properly"

# Test 16: Memory Usage
run_test "Extended Usage Test" \
"1. Use app for 10 minutes continuously
2. Make various requests
3. Monitor for slowdowns
4. Check for crashes

App should remain responsive"

# Test 17: Voice Recognition Accuracy
run_test "Voice Recognition Quality" \
"1. Test with different accents
2. Test in quiet environment
3. Test with background noise
4. Test while driving

Should maintain >90% accuracy in quiet conditions"

# Test 18: Safety Features
run_test "Auto-Pause Safety" \
"1. Play a story
2. Make sudden movements/turns
3. Check if audio pauses
4. Check if it resumes when stable

Audio should pause during critical movements"

# Test 19: UI Responsiveness
run_test "UI Performance" \
"1. Tap buttons rapidly
2. Pan/zoom map while story plays
3. Switch between features quickly
4. Check for UI freezes

UI should remain smooth and responsive"

# Test 20: Battery Usage
run_test "Battery Efficiency" \
"1. Note battery % at start
2. Use app for 30 minutes
3. Note battery % at end
4. Calculate drain rate

Should not drain battery excessively"

# Summary
echo ""
echo "📊 Test Summary"
echo "=============="
echo -e "Total Tests Run: $TOTAL"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"

if [ $TOTAL -gt 0 ]; then
    SUCCESS_RATE=$((PASSED * 100 / TOTAL))
    echo "Success Rate: $SUCCESS_RATE%"
    
    echo "" >> test_results.log
    echo "Summary" >> test_results.log
    echo "-------" >> test_results.log
    echo "Total: $TOTAL" >> test_results.log
    echo "Passed: $PASSED" >> test_results.log
    echo "Failed: $FAILED" >> test_results.log
    echo "Success Rate: $SUCCESS_RATE%" >> test_results.log
    
    if [ $SUCCESS_RATE -eq 100 ]; then
        echo -e "\n${GREEN}✅ All tests passed! Ready for beta deployment.${NC}"
        echo "Result: READY FOR BETA" >> test_results.log
    elif [ $SUCCESS_RATE -ge 80 ]; then
        echo -e "\n${YELLOW}⚠️  Most tests passed. Review failures before deployment.${NC}"
        echo "Result: CONDITIONAL PASS" >> test_results.log
    else
        echo -e "\n${RED}❌ Too many failures. Fix issues before deployment.${NC}"
        echo "Result: NOT READY" >> test_results.log
    fi
fi

echo ""
echo "Test results saved to: test_results.log"
echo ""

# Generate detailed report
cat > mobile_test_report_$(date +%Y%m%d_%H%M%S).md << EOF
# AI Road Trip MVP - Mobile Test Report

## Test Information
- **Tester:** $TESTER_NAME
- **Date:** $(date)
- **Device:** $DEVICE_TYPE - $DEVICE_MODEL
- **OS Version:** $OS_VERSION
- **Backend URL:** $BACKEND_URL

## Test Results
- **Total Tests:** $TOTAL
- **Passed:** $PASSED
- **Failed:** $FAILED
- **Success Rate:** $SUCCESS_RATE%

## Detailed Results
$(cat test_results.log)

## Recommendation
$(if [ $SUCCESS_RATE -eq 100 ]; then
    echo "✅ **READY FOR BETA DEPLOYMENT**"
elif [ $SUCCESS_RATE -ge 80 ]; then
    echo "⚠️ **CONDITIONAL PASS** - Review and fix failures before wide deployment"
else
    echo "❌ **NOT READY** - Significant issues need to be resolved"
fi)

## Sign-off
**Tested by:** $TESTER_NAME  
**Date:** $(date)  
**Signature:** _______________
EOF

echo "Detailed report saved to: mobile_test_report_$(date +%Y%m%d_%H%M%S).md"