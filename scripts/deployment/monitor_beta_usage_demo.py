#!/usr/bin/env python3
"""
Monitor Beta Usage - Demo Version
Simulates real-time monitoring of beta launch metrics
"""
import asyncio
import json
from datetime import datetime
import sys
import random
import math

class BetaUsageMonitorDemo:
    """Simulates beta launch monitoring"""
    
    def __init__(self):
        self.monitoring_interval = 5  # seconds
        self.start_time = datetime.now()
        self.metrics_history = []
        
    def generate_metrics(self, elapsed_minutes: int) -> dict:
        """Generate realistic metrics based on time elapsed"""
        # Simulate gradual user adoption
        adoption_curve = 1 - math.exp(-elapsed_minutes / 30)  # Exponential growth
        
        # Base metrics
        total_beta_users = 100
        base_active_rate = 0.15  # Start with 15% active
        
        # Calculate active users (grows over time)
        active_rate = min(0.65, base_active_rate + (adoption_curve * 0.5))
        active_users = int(total_beta_users * active_rate)
        
        # New signups (higher at start, then tapers)
        new_signups = max(0, int(12 * math.exp(-elapsed_minutes / 60)))
        
        # Active sessions
        active_sessions = int(active_users * 0.7)
        
        # API metrics (increases with usage)
        base_rpm = 50
        requests_per_minute = int(base_rpm + (active_users * 8))
        
        # Voice commands (realistic usage pattern)
        voice_commands = int(200 + (elapsed_minutes * 30) + random.randint(-50, 50))
        
        # Bookings (conversion improves over time)
        base_conversion = 0.08
        conversion_rate = min(0.20, base_conversion + (elapsed_minutes * 0.002))
        searches = int(20 + (active_users * 2.5))
        bookings_attempted = int(searches * conversion_rate)
        bookings_completed = int(bookings_attempted * 0.85)
        
        # Calculate revenue
        avg_booking_value = 85.25
        commission_rate = 0.08
        revenue = bookings_completed * avg_booking_value * commission_rate
        
        return {
            "timestamp": datetime.now().isoformat(),
            "users": {
                "total_beta_users": total_beta_users,
                "active_users_24h": active_users,
                "activation_rate": active_rate,
                "new_signups_today": new_signups,
                "active_sessions": active_sessions,
                "platform_breakdown": {
                    "ios": int(active_users * 0.55),
                    "android": int(active_users * 0.40),
                    "web": int(active_users * 0.05)
                },
                "category_activity": {
                    "family_travelers": int(active_users * 0.28),
                    "business_travelers": int(active_users * 0.22),
                    "event_attendees": int(active_users * 0.26),
                    "rideshare_drivers": int(active_users * 0.24)
                }
            },
            "api": {
                "requests_per_minute": requests_per_minute,
                "response_time_p50": 45 + random.randint(-10, 10),
                "response_time_p95": 120 + random.randint(-20, 20),
                "response_time_p99": 180 + random.randint(-30, 30),
                "error_rate": max(0, 0.012 + random.uniform(-0.005, 0.005)),
                "availability": min(1.0, 0.998 + random.uniform(-0.002, 0.001))
            },
            "voice": {
                "total_commands_today": voice_commands,
                "recognition_accuracy": 0.92 + random.uniform(-0.02, 0.02),
                "avg_response_time": 95 + random.randint(-10, 10),
                "edge_processing_rate": 0.68 + random.uniform(-0.05, 0.05)
            },
            "bookings": {
                "searches_today": searches,
                "bookings_attempted": bookings_attempted,
                "bookings_completed": bookings_completed,
                "conversion_rate": conversion_rate,
                "estimated_revenue": revenue,
                "avg_booking_value": avg_booking_value
            },
            "performance": {
                "cpu_usage": 0.42 + random.uniform(-0.1, 0.1),
                "memory_usage": 0.68 + random.uniform(-0.05, 0.05),
                "cache_hit_rate": 0.84 + random.uniform(-0.02, 0.02)
            },
            "errors": {
                "app_crashes_today": max(0, 3 + random.randint(-2, 1)),
                "crash_rate": 0.007 + random.uniform(-0.003, 0.003),
                "api_errors_today": max(0, 89 + random.randint(-20, 20))
            }
        }
    
    def generate_dashboard(self, metrics: dict, elapsed_time: str):
        """Generate monitoring dashboard display"""
        print("\033[2J\033[H")  # Clear screen
        print("🚀 AI ROAD TRIP STORYTELLER - BETA MONITORING DASHBOARD")
        print("=" * 80)
        print(f"Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Uptime: {elapsed_time}")
        print()
        
        # User Metrics
        print("👥 USER METRICS")
        print("-" * 40)
        user_metrics = metrics["users"]
        print(f"Total Beta Users:     {user_metrics['total_beta_users']}")
        print(f"Active (24h):         {user_metrics['active_users_24h']} ({user_metrics['activation_rate']:.1%})")
        print(f"New Signups Today:    {user_metrics['new_signups_today']}")
        print(f"Active Sessions:      {user_metrics['active_sessions']}")
        
        # Platform breakdown bar chart
        platforms = user_metrics["platform_breakdown"]
        print("\nPlatform Usage:")
        for platform, count in platforms.items():
            bar_length = int((count / user_metrics['active_users_24h']) * 20) if user_metrics['active_users_24h'] > 0 else 0
            print(f"  {platform:<8} {'█' * bar_length} {count}")
        print()
        
        # API Performance
        print("⚡ API PERFORMANCE")
        print("-" * 40)
        api_metrics = metrics["api"]
        print(f"Requests/min:         {api_metrics['requests_per_minute']}")
        print(f"Response Time (P50):  {api_metrics['response_time_p50']}ms")
        print(f"Response Time (P95):  {api_metrics['response_time_p95']}ms")
        print(f"Error Rate:           {api_metrics['error_rate']:.2%}")
        print(f"Availability:         {api_metrics['availability']:.3%}")
        print()
        
        # Voice Metrics
        print("🎤 VOICE INTERACTIONS")
        print("-" * 40)
        voice_metrics = metrics["voice"]
        print(f"Commands Today:       {voice_metrics['total_commands_today']}")
        print(f"Recognition Accuracy: {voice_metrics['recognition_accuracy']:.1%}")
        print(f"Avg Response Time:    {voice_metrics['avg_response_time']}ms")
        print(f"Edge Processing:      {voice_metrics['edge_processing_rate']:.1%}")
        print()
        
        # Booking Metrics
        print("💰 BOOKINGS & REVENUE")
        print("-" * 40)
        booking_metrics = metrics["bookings"]
        print(f"Searches:             {booking_metrics['searches_today']}")
        print(f"Completed:            {booking_metrics['bookings_completed']}/{booking_metrics['bookings_attempted']}")
        print(f"Conversion Rate:      {booking_metrics['conversion_rate']:.1%}")
        print(f"Est. Revenue Today:   ${booking_metrics['estimated_revenue']:.2f}")
        print()
        
        # System Health with visual indicators
        print("🔧 SYSTEM HEALTH")
        print("-" * 40)
        perf_metrics = metrics["performance"]
        
        # CPU gauge
        cpu = perf_metrics["cpu_usage"]
        cpu_bar = int(cpu * 20)
        cpu_color = "🟢" if cpu < 0.7 else "🟡" if cpu < 0.85 else "🔴"
        print(f"CPU Usage:    {cpu_color} [{'█' * cpu_bar}{' ' * (20 - cpu_bar)}] {cpu:.1%}")
        
        # Memory gauge
        mem = perf_metrics["memory_usage"]
        mem_bar = int(mem * 20)
        mem_color = "🟢" if mem < 0.8 else "🟡" if mem < 0.9 else "🔴"
        print(f"Memory Usage: {mem_color} [{'█' * mem_bar}{' ' * (20 - mem_bar)}] {mem:.1%}")
        
        # Cache hit rate
        cache = perf_metrics["cache_hit_rate"]
        print(f"Cache Hit Rate:       {cache:.1%}")
        print()
        
        # Status Summary
        error_rate = metrics["api"]["error_rate"]
        if error_rate < 0.02 and cpu < 0.8 and mem < 0.85:
            print("✅ All systems operating normally")
        else:
            print("⚠️  Some metrics need attention")
    
    async def monitor_loop(self):
        """Main monitoring loop"""
        print("Starting beta monitoring dashboard...")
        print("Press Ctrl+C to stop")
        await asyncio.sleep(2)
        
        while True:
            try:
                # Calculate elapsed time
                elapsed = datetime.now() - self.start_time
                elapsed_minutes = elapsed.total_seconds() / 60
                elapsed_str = f"{int(elapsed.total_seconds() // 3600):02d}:{int((elapsed.total_seconds() % 3600) // 60):02d}:{int(elapsed.total_seconds() % 60):02d}"
                
                # Generate metrics
                metrics = self.generate_metrics(int(elapsed_minutes))
                self.metrics_history.append(metrics)
                
                # Display dashboard
                self.generate_dashboard(metrics, elapsed_str)
                
                # Save snapshot every minute
                if len(self.metrics_history) % 12 == 0:  # Every 60 seconds
                    self.save_snapshot(metrics)
                
                # Wait for next update
                await asyncio.sleep(self.monitoring_interval)
                
            except KeyboardInterrupt:
                print("\n\nMonitoring stopped by user")
                self.print_summary()
                break
    
    def save_snapshot(self, metrics: dict):
        """Save metrics snapshot"""
        filename = f"beta_metrics_snapshot_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        with open(filename, "w") as f:
            json.dump({
                "snapshot": metrics,
                "history_length": len(self.metrics_history)
            }, f, indent=2)
    
    def print_summary(self):
        """Print monitoring summary"""
        if not self.metrics_history:
            return
        
        print("\n" + "=" * 80)
        print("BETA MONITORING SUMMARY")
        print("=" * 80)
        
        # Calculate averages
        total_metrics = len(self.metrics_history)
        avg_active_users = sum(m["users"]["active_users_24h"] for m in self.metrics_history) / total_metrics
        avg_rpm = sum(m["api"]["requests_per_minute"] for m in self.metrics_history) / total_metrics
        total_revenue = sum(m["bookings"]["estimated_revenue"] for m in self.metrics_history)
        
        print(f"Monitoring Duration: {(datetime.now() - self.start_time).total_seconds() / 60:.1f} minutes")
        print(f"Average Active Users: {avg_active_users:.0f}")
        print(f"Average Requests/min: {avg_rpm:.0f}")
        print(f"Total Revenue Generated: ${total_revenue:.2f}")
        print("\nBeta launch monitoring complete!")


async def main():
    """Main function"""
    monitor = BetaUsageMonitorDemo()
    
    try:
        await monitor.monitor_loop()
    except Exception as e:
        print(f"\n❌ Monitoring error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())