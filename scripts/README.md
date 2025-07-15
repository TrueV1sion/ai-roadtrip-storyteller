# AI Road Trip Storyteller - Simulation System

This directory contains a comprehensive user simulation system for testing the AI Road Trip Storyteller application. The system generates realistic user profiles, journey scenarios, and interaction patterns to validate system performance and user experience.

## Components

### 1. **simulation_engine.py**
The core simulation engine that orchestrates the entire testing process.

Features:
- Generates diverse user personas (families, business travelers, adventure seekers, etc.)
- Creates realistic journey types (commute, weekend trips, cross-country, etc.)
- Simulates voice interactions and booking requests
- Tracks performance metrics and conversion rates
- Supports real-time and accelerated simulation modes

### 2. **user_simulator.py**
Generates realistic user profiles with detailed characteristics.

User Personas:
- Family Vacation
- Business Traveler
- Rideshare Driver
- Adventure Seeker
- History Buff
- Foodie Explorer
- Nature Lover
- Couple Romantic
- Solo Wanderer
- Group Friends

Each user has:
- Demographics (age, occupation)
- Travel preferences
- Tech savviness levels
- Budget constraints
- Voice personality preferences
- Interaction patterns

### 3. **route_simulator.py**
Creates realistic routes with various characteristics.

Route Types:
- Highway
- Scenic
- Coastal
- Mountain
- Desert
- Rural
- Urban
- Historic

Features:
- Real coordinate generation
- Points of interest along routes
- Scenic ratings and difficulty levels
- Weather and traffic conditions
- Multi-day journey support

### 4. **simulation_dashboard.py**
Real-time monitoring dashboard for ongoing simulations.

Display Modes:
- Overview: Current activity and totals
- Details: Interaction breakdown
- Performance: Response times and throughput

Metrics Tracked:
- Active users and journeys
- Interactions per minute
- Response time percentiles
- Booking conversion rates
- Error rates

### 5. **run_simulation.py**
Main entry point with pre-defined test scenarios.

## Usage

### Quick Start

Run with interactive dashboard:
```bash
python run_simulation.py --mode dashboard
```

### Pre-defined Scenarios

1. **Peak Traffic Test**
   ```bash
   python run_simulation.py --scenario peak_traffic
   ```
   Simulates heavy load during commute hours with business travelers and rideshare drivers.

2. **Weekend Leisure**
   ```bash
   python run_simulation.py --scenario weekend_leisure
   ```
   Tests family trips and adventure seekers on weekends.

3. **Voice Stress Test**
   ```bash
   python run_simulation.py --scenario voice_stress
   ```
   High-frequency voice command testing.

4. **Booking Conversion**
   ```bash
   python run_simulation.py --scenario booking_conversion
   ```
   Focuses on users likely to make restaurant and activity bookings.

5. **Multi-Day Journey**
   ```bash
   python run_simulation.py --scenario multi_day
   ```
   Tests long-distance cross-country trips.

6. **Seasonal Variation**
   ```bash
   python run_simulation.py --scenario seasonal
   ```
   Different weather and seasonal conditions.

### Run All Scenarios
```bash
python run_simulation.py --mode all_scenarios
```

### Custom Configuration

1. Create sample config:
   ```bash
   python run_simulation.py --create-sample
   ```

2. Edit `simulation_config_sample.json`

3. Run custom simulation:
   ```bash
   python run_simulation.py --config my_config.json
   ```

### Dashboard Controls

When running in dashboard mode:
- Press `O` for Overview
- Press `D` for Details
- Press `P` for Performance
- Press `Q` to Quit

## Configuration Options

### Command Line Arguments

```bash
python run_simulation.py [options]

Options:
  --mode {dashboard,scenario,all_scenarios,custom}
                        Simulation mode
  --scenario {peak_traffic,weekend_leisure,voice_stress,booking_conversion,multi_day,seasonal}
                        Pre-defined scenario to run
  --config CONFIG       Path to custom configuration file
  --users USERS         Number of users (default: 100)
  --duration DURATION   Duration in minutes (default: 30)
  --concurrent CONCURRENT
                        Concurrent users (default: 25)
  --create-sample       Create sample configuration file
```

### Custom Configuration Format

```json
{
  "name": "Custom Simulation",
  "description": "Description of the test",
  "num_users": 100,
  "duration_minutes": 30,
  "concurrent_users": 25,
  "user_distribution": {
    "family": 0.3,
    "business_traveler": 0.2,
    "adventure_seeker": 0.2,
    "foodie": 0.15,
    "history_buff": 0.15
  },
  "interaction_frequency_multiplier": 1.0,
  "booking_probability_boost": 0.0,
  "api_base_url": "http://localhost:8000"
}
```

## Output Files

The simulation system generates several output files:

1. **simulation_results_[timestamp].json**
   - Complete metrics summary
   - User profiles
   - Journey details
   - Interaction logs

2. **scenario_[name]_[timestamp].json**
   - Scenario-specific results
   - Performance metrics
   - Conversion rates

3. **load_test_results.json**
   - Load test specific metrics
   - Throughput analysis
   - Capacity estimates

## Metrics Explained

### Performance Metrics
- **Response Time**: Time to process user requests
- **P95/P99**: 95th and 99th percentile response times
- **Throughput**: Interactions processed per minute

### Business Metrics
- **Booking Conversion**: Percentage of booking attempts that succeed
- **User Engagement**: Interaction frequency per user
- **Feature Usage**: Which features are used most

### System Metrics
- **Error Rate**: Percentage of failed requests
- **Active Sessions**: Concurrent users and journeys
- **Capacity Utilization**: System load percentage

## Testing Best Practices

1. **Start Small**: Begin with fewer users to validate setup
2. **Monitor Resources**: Watch CPU and memory during tests
3. **Gradual Ramp-up**: Increase load gradually
4. **Multiple Runs**: Run each scenario multiple times
5. **Analyze Patterns**: Look for performance degradation points

## Troubleshooting

### Common Issues

1. **API Connection Failed**
   - Ensure backend is running on specified port
   - Check `api_base_url` in configuration

2. **High Error Rates**
   - Reduce concurrent users
   - Check backend logs for errors
   - Verify API endpoints are working

3. **Dashboard Not Updating**
   - Check refresh interval settings
   - Ensure simulation is generating data

## Requirements

- Python 3.9+
- Dependencies:
  ```bash
  pip install httpx numpy geopy
  ```
- Backend API running (default: http://localhost:8000)

## Future Enhancements

- [ ] Database performance tracking
- [ ] Network latency simulation
- [ ] Mobile device simulation
- [ ] Offline mode testing
- [ ] A/B testing support
- [ ] Integration with monitoring tools
- [ ] Automated performance regression detection