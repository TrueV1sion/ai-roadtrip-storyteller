"""
Simulation Dashboard for AI Road Trip Storyteller
Real-time monitoring and visualization of simulated activity
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import statistics
from collections import deque, defaultdict
from dataclasses import dataclass, field
import os
import sys

# Add scripts directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from simulation_engine import SimulationEngine, UserPersona, JourneyType
from user_simulator import UserSimulator
from route_simulator import RouteSimulator


@dataclass
class MetricSnapshot:
    """Point-in-time metrics snapshot"""
    timestamp: datetime
    active_users: int
    active_journeys: int
    interactions_per_minute: float
    average_response_time: float
    error_rate: float
    bookings_per_hour: float
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    

@dataclass
class DashboardState:
    """Current dashboard state"""
    start_time: datetime
    total_users: int = 0
    total_journeys: int = 0
    total_interactions: int = 0
    total_bookings: int = 0
    total_errors: int = 0
    active_sessions: Dict[str, Any] = field(default_factory=dict)
    metric_history: deque = field(default_factory=lambda: deque(maxlen=60))
    interaction_types: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    persona_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    journey_distribution: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    response_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    

class SimulationDashboard:
    """Real-time dashboard for monitoring simulation activity"""
    
    def __init__(self, refresh_interval: int = 5):
        self.refresh_interval = refresh_interval
        self.state = DashboardState(start_time=datetime.now())
        self.engine: Optional[SimulationEngine] = None
        self.running = False
        self.display_mode = "overview"  # overview, details, performance
        
    async def start(self, engine: SimulationEngine):
        """Start the dashboard"""
        self.engine = engine
        self.running = True
        
        # Start monitoring tasks
        await asyncio.gather(
            self._update_metrics_loop(),
            self._display_loop(),
            self._keyboard_handler()
        )
        
    async def _update_metrics_loop(self):
        """Continuously update metrics"""
        while self.running:
            self._update_metrics()
            await asyncio.sleep(1)
            
    async def _display_loop(self):
        """Continuously update display"""
        while self.running:
            self._clear_screen()
            self._display_dashboard()
            await asyncio.sleep(self.refresh_interval)
            
    async def _keyboard_handler(self):
        """Handle keyboard input for mode switching"""
        # Note: In a real implementation, would use proper async keyboard handling
        # For now, this is a placeholder
        while self.running:
            await asyncio.sleep(0.1)
            
    def _update_metrics(self):
        """Update metrics from simulation engine"""
        if not self.engine:
            return
            
        # Get current metrics
        metrics = self.engine.get_metrics_summary()
        
        # Update state
        self.state.total_users = metrics["summary"]["total_users"]
        self.state.total_journeys = metrics["summary"]["total_journeys"]
        self.state.total_interactions = metrics["summary"]["total_interactions"]
        self.state.total_bookings = metrics["bookings"]["completed"]
        self.state.total_errors = metrics["summary"]["total_errors"]
        
        # Update distributions
        self.state.persona_distribution = metrics.get("persona_distribution", {})
        
        # Calculate rates
        elapsed_minutes = (datetime.now() - self.state.start_time).total_seconds() / 60
        interactions_per_minute = self.state.total_interactions / max(elapsed_minutes, 1)
        bookings_per_hour = (self.state.total_bookings / max(elapsed_minutes, 1)) * 60
        
        # Response times
        if metrics.get("response_times"):
            avg_response_time = metrics["response_times"].get("mean", 0)
            self.state.response_times.append(avg_response_time)
        else:
            avg_response_time = 0
            
        # Error rate
        error_rate = metrics["summary"].get("error_rate", 0)
        
        # Active sessions (simplified)
        active_users = len([u for u in self.engine.users.values() 
                          if (datetime.now() - u.created_at).total_seconds() < 3600])
        active_journeys = len([j for j in self.engine.journeys.values()
                             if (datetime.now() - j.start_time).total_seconds() < 7200])
        
        # Create snapshot
        snapshot = MetricSnapshot(
            timestamp=datetime.now(),
            active_users=active_users,
            active_journeys=active_journeys,
            interactions_per_minute=interactions_per_minute,
            average_response_time=avg_response_time,
            error_rate=error_rate,
            bookings_per_hour=bookings_per_hour
        )
        
        self.state.metric_history.append(snapshot)
        
        # Update interaction types
        for interaction in self.engine.interactions[-100:]:  # Last 100
            self.state.interaction_types[interaction.interaction_type] += 1
            
    def _clear_screen(self):
        """Clear terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
    def _display_dashboard(self):
        """Display the dashboard"""
        if self.display_mode == "overview":
            self._display_overview()
        elif self.display_mode == "details":
            self._display_details()
        elif self.display_mode == "performance":
            self._display_performance()
            
    def _display_overview(self):
        """Display overview dashboard"""
        print("=" * 80)
        print("AI ROAD TRIP STORYTELLER - SIMULATION DASHBOARD".center(80))
        print("=" * 80)
        
        # Runtime
        runtime = datetime.now() - self.state.start_time
        print(f"\nRuntime: {runtime}")
        print(f"Mode: {self.display_mode.upper()} | Press [D]etails [P]erformance [O]verview [Q]uit")
        
        # Current activity
        print("\n" + "CURRENT ACTIVITY".center(80, "-"))
        if self.state.metric_history:
            latest = self.state.metric_history[-1]
            print(f"Active Users:     {latest.active_users:>6}")
            print(f"Active Journeys:  {latest.active_journeys:>6}")
            print(f"Interactions/min: {latest.interactions_per_minute:>6.1f}")
            print(f"Bookings/hour:    {latest.bookings_per_hour:>6.1f}")
            
        # Totals
        print("\n" + "CUMULATIVE TOTALS".center(80, "-"))
        print(f"Total Users:        {self.state.total_users:>8}")
        print(f"Total Journeys:     {self.state.total_journeys:>8}")
        print(f"Total Interactions: {self.state.total_interactions:>8}")
        print(f"Total Bookings:     {self.state.total_bookings:>8}")
        print(f"Total Errors:       {self.state.total_errors:>8}")
        
        # Performance
        print("\n" + "PERFORMANCE METRICS".center(80, "-"))
        if self.state.response_times:
            avg_response = statistics.mean(self.state.response_times)
            p95_response = statistics.quantiles(self.state.response_times, n=20)[18] if len(self.state.response_times) > 20 else avg_response
            print(f"Avg Response Time: {avg_response:>7.2f}s")
            print(f"P95 Response Time: {p95_response:>7.2f}s")
            
        if self.state.metric_history:
            latest = self.state.metric_history[-1]
            print(f"Error Rate:        {latest.error_rate:>7.1%}")
            
        # Persona distribution
        print("\n" + "USER PERSONAS".center(80, "-"))
        if self.state.persona_distribution:
            sorted_personas = sorted(self.state.persona_distribution.items(), 
                                   key=lambda x: x[1], reverse=True)[:5]
            for persona, count in sorted_personas:
                percentage = (count / max(self.state.total_users, 1)) * 100
                bar = "█" * int(percentage / 2)
                print(f"{persona[:20]:<20} {bar:<25} {count:>4} ({percentage:>5.1f}%)")
                
        # Activity graph (simple ASCII)
        print("\n" + "ACTIVITY TREND (Last 60 seconds)".center(80, "-"))
        if len(self.state.metric_history) > 1:
            self._display_activity_graph()
            
    def _display_activity_graph(self):
        """Display simple ASCII activity graph"""
        if len(self.state.metric_history) < 2:
            return
            
        # Get interactions per minute for graph
        values = [m.interactions_per_minute for m in self.state.metric_history]
        if not values:
            return
            
        max_val = max(values) if values else 1
        height = 10
        
        # Scale values
        scaled = []
        for val in values:
            scaled_val = int((val / max_val) * height) if max_val > 0 else 0
            scaled.append(scaled_val)
            
        # Draw graph
        for h in range(height, -1, -1):
            line = ""
            for val in scaled[-60:]:  # Last 60 values
                if val >= h:
                    line += "█"
                else:
                    line += " "
            label = f"{(h/height * max_val):>6.1f} |" if h % 2 == 0 else "       |"
            print(f"{label}{line}")
            
        print("       +" + "-" * min(60, len(scaled)))
        print("        " + "Now" + " " * (min(57, len(scaled)-3)) + "60s ago")
        
    def _display_details(self):
        """Display detailed metrics"""
        print("=" * 80)
        print("DETAILED METRICS".center(80))
        print("=" * 80)
        
        # Interaction breakdown
        print("\n" + "INTERACTION TYPES".center(80, "-"))
        if self.state.interaction_types:
            sorted_types = sorted(self.state.interaction_types.items(), 
                                key=lambda x: x[1], reverse=True)
            for itype, count in sorted_types[:10]:
                percentage = (count / max(sum(self.state.interaction_types.values()), 1)) * 100
                print(f"{itype:<30} {count:>6} ({percentage:>5.1f}%)")
                
        # Recent interactions
        print("\n" + "RECENT INTERACTIONS".center(80, "-"))
        if self.engine and self.engine.interactions:
            for interaction in self.engine.interactions[-10:]:
                time_str = interaction.timestamp.strftime("%H:%M:%S")
                success = "✓" if interaction.success else "✗"
                print(f"{time_str} {success} {interaction.interaction_type:<20} "
                      f"{interaction.response_time:>5.2f}s {interaction.command[:30]}")
                      
        # Journey types
        print("\n" + "JOURNEY TYPES".center(80, "-"))
        journey_types = defaultdict(int)
        if self.engine:
            for journey in self.engine.journeys.values():
                journey_types[journey.journey_type.value] += 1
                
        for jtype, count in sorted(journey_types.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / max(self.state.total_journeys, 1)) * 100
            print(f"{jtype:<25} {count:>4} ({percentage:>5.1f}%)")
            
    def _display_performance(self):
        """Display performance metrics"""
        print("=" * 80)
        print("PERFORMANCE ANALYSIS".center(80))
        print("=" * 80)
        
        # Response time distribution
        print("\n" + "RESPONSE TIME DISTRIBUTION".center(80, "-"))
        if self.state.response_times and len(self.state.response_times) > 10:
            times = list(self.state.response_times)
            percentiles = statistics.quantiles(times, n=10)
            
            print(f"Min:    {min(times):>6.3f}s")
            print(f"P10:    {percentiles[0]:>6.3f}s")
            print(f"P50:    {percentiles[4]:>6.3f}s")
            print(f"P90:    {percentiles[8]:>6.3f}s")
            print(f"P99:    {statistics.quantiles(times, n=100)[98] if len(times) > 100 else percentiles[8]:>6.3f}s")
            print(f"Max:    {max(times):>6.3f}s")
            print(f"Mean:   {statistics.mean(times):>6.3f}s")
            print(f"StdDev: {statistics.stdev(times) if len(times) > 1 else 0:>6.3f}s")
            
        # Throughput over time
        print("\n" + "THROUGHPUT TRENDS".center(80, "-"))
        if len(self.state.metric_history) > 10:
            # Calculate 5-minute windows
            windows = []
            for i in range(0, len(self.state.metric_history), 12):  # 12 * 5s = 1 min
                window = list(self.state.metric_history)[i:i+12]
                if window:
                    avg_ipm = statistics.mean(m.interactions_per_minute for m in window)
                    avg_response = statistics.mean(m.average_response_time for m in window)
                    windows.append((window[0].timestamp, avg_ipm, avg_response))
                    
            print("Time     | Interactions/min | Avg Response")
            print("-" * 45)
            for timestamp, ipm, response in windows[-10:]:
                time_str = timestamp.strftime("%H:%M:%S")
                print(f"{time_str} | {ipm:>15.1f} | {response:>10.3f}s")
                
        # Error analysis
        print("\n" + "ERROR ANALYSIS".center(80, "-"))
        if self.state.total_errors > 0:
            error_rate = (self.state.total_errors / max(self.state.total_interactions, 1)) * 100
            print(f"Total Errors:     {self.state.total_errors}")
            print(f"Error Rate:       {error_rate:.2f}%")
            print(f"Errors/hour:      {(self.state.total_errors / max((datetime.now() - self.state.start_time).total_seconds() / 3600, 1)):.1f}")
            
        # Capacity metrics
        print("\n" + "CAPACITY METRICS".center(80, "-"))
        if self.state.metric_history:
            latest = self.state.metric_history[-1]
            max_concurrent = max(m.active_users for m in self.state.metric_history)
            
            print(f"Current Active Users:    {latest.active_users}")
            print(f"Max Concurrent Users:    {max_concurrent}")
            print(f"Current Active Journeys: {latest.active_journeys}")
            
            # Estimate capacity
            if latest.average_response_time > 0:
                estimated_capacity = int(60 / latest.average_response_time * 10)  # 10 workers
                utilization = (latest.active_users / estimated_capacity) * 100
                print(f"Estimated Capacity:      {estimated_capacity} users")
                print(f"Current Utilization:     {utilization:.1f}%")
                

async def run_simulation_with_dashboard(num_users: int = 100, 
                                      duration_minutes: int = 10,
                                      concurrent_users: int = 20):
    """Run simulation with live dashboard"""
    print("Starting AI Road Trip Storyteller Simulation...")
    print(f"Parameters: {num_users} users, {duration_minutes} minutes, {concurrent_users} concurrent")
    print("\nInitializing...")
    
    # Create simulation engine
    async with SimulationEngine() as engine:
        # Create dashboard
        dashboard = SimulationDashboard(refresh_interval=5)
        
        # Start simulation in background
        simulation_task = asyncio.create_task(
            engine.run_load_test(num_users, duration_minutes, concurrent_users)
        )
        
        # Run dashboard
        dashboard_task = asyncio.create_task(dashboard.start(engine))
        
        try:
            # Wait for simulation to complete
            await simulation_task
            
            # Keep dashboard running for a bit after simulation ends
            await asyncio.sleep(10)
            
            # Stop dashboard
            dashboard.running = False
            
        except KeyboardInterrupt:
            print("\n\nSimulation interrupted by user")
            dashboard.running = False
            
        finally:
            # Final summary
            print("\n" + "=" * 80)
            print("SIMULATION COMPLETE - FINAL SUMMARY".center(80))
            print("=" * 80)
            
            metrics = engine.get_metrics_summary()
            print(f"\nTotal Users:        {metrics['summary']['total_users']}")
            print(f"Total Journeys:     {metrics['summary']['total_journeys']}")
            print(f"Total Interactions: {metrics['summary']['total_interactions']}")
            print(f"Total Bookings:     {metrics['bookings']['completed']}")
            print(f"Booking Conversion: {metrics['bookings']['conversion_rate']:.1%}")
            print(f"Error Rate:         {metrics['summary']['error_rate']:.1%}")
            
            if metrics.get('response_times'):
                print(f"\nResponse Times:")
                print(f"  Mean:   {metrics['response_times']['mean']:.3f}s")
                print(f"  Median: {metrics['response_times']['median']:.3f}s")
                print(f"  P95:    {metrics['response_times']['p95']:.3f}s")
                print(f"  P99:    {metrics['response_times']['p99']:.3f}s")
                
            # Export results
            engine.export_results(f"simulation_results_{int(time.time())}.json")
            

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Road Trip Storyteller Simulation Dashboard")
    parser.add_argument("--users", type=int, default=100, help="Number of users to simulate")
    parser.add_argument("--duration", type=int, default=10, help="Duration in minutes")
    parser.add_argument("--concurrent", type=int, default=20, help="Concurrent users")
    parser.add_argument("--mode", choices=["dashboard", "batch"], default="dashboard",
                       help="Run mode: dashboard (interactive) or batch")
    
    args = parser.parse_args()
    
    if args.mode == "dashboard":
        # Run with dashboard
        asyncio.run(run_simulation_with_dashboard(
            args.users, 
            args.duration,
            args.concurrent
        ))
    else:
        # Run batch mode without dashboard
        async def run_batch():
            async with SimulationEngine() as engine:
                await engine.run_load_test(args.users, args.duration, args.concurrent)
                metrics = engine.get_metrics_summary()
                print(json.dumps(metrics, indent=2))
                engine.export_results()
                
        asyncio.run(run_batch())


if __name__ == "__main__":
    main()