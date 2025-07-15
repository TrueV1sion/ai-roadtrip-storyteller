"""
Execute load tests and analyze results for AI Road Trip Storyteller
"""
import subprocess
import time
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Configure matplotlib for better looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")


class LoadTestExecutor:
    """Execute and analyze load tests"""
    
    def __init__(self, host: str = "http://localhost:8000"):
        self.host = host
        self.results_dir = Path("load_test_results")
        self.results_dir.mkdir(exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def check_dependencies(self) -> bool:
        """Check if required dependencies are installed"""
        try:
            import locust
            import matplotlib
            import pandas
            import seaborn
            return True
        except ImportError as e:
            print(f"Missing dependency: {e}")
            print("Installing required packages...")
            subprocess.run([sys.executable, "-m", "pip", "install", 
                          "locust", "matplotlib", "pandas", "seaborn"])
            return True
            
    def run_scenario(self, name: str, users: int, spawn_rate: int, 
                    run_time: str, user_classes: str = "") -> Dict[str, Any]:
        """Run a single load test scenario"""
        print(f"\n{'='*60}")
        print(f"Running scenario: {name}")
        print(f"Users: {users}, Spawn rate: {spawn_rate}, Duration: {run_time}")
        print(f"{'='*60}\n")
        
        csv_prefix = self.results_dir / f"{name}_{self.timestamp}"
        html_file = self.results_dir / f"{name}_{self.timestamp}.html"
        log_file = self.results_dir / f"{name}_{self.timestamp}.log"
        
        cmd = [
            "locust",
            "--headless",
            f"--host={self.host}",
            f"--users={users}",
            f"--spawn-rate={spawn_rate}",
            f"--run-time={run_time}",
            f"--csv={csv_prefix}",
            f"--html={html_file}",
            f"--logfile={log_file}",
            "-f", "tests/load/locustfile.py"
        ]
        
        if user_classes:
            cmd.extend(user_classes.split())
        
        # Run locust
        start_time = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = time.time() - start_time
        
        # Parse results
        stats_file = f"{csv_prefix}_stats.csv"
        if os.path.exists(stats_file):
            df = pd.read_csv(stats_file)
            aggregated = df[df['Name'] == 'Aggregated'].iloc[0]
            
            return {
                "scenario": name,
                "users": users,
                "spawn_rate": spawn_rate,
                "duration": duration,
                "total_requests": int(aggregated['Request Count']),
                "failure_count": int(aggregated['Failure Count']),
                "failure_rate": float(aggregated['Failure Count']) / max(int(aggregated['Request Count']), 1),
                "avg_response_time": float(aggregated['Average Response Time']),
                "min_response_time": float(aggregated['Min Response Time']),
                "max_response_time": float(aggregated['Max Response Time']),
                "median_response_time": float(aggregated['Median Response Time']),
                "p90_response_time": float(aggregated['90%']),
                "p95_response_time": float(aggregated['95%']),
                "p99_response_time": float(aggregated['99%']),
                "rps": float(aggregated['Requests/s']),
                "avg_content_size": float(aggregated['Average Content Size'])
            }
        else:
            print(f"Warning: No stats file found for {name}")
            return {"scenario": name, "error": "No stats file generated"}
    
    def run_all_scenarios(self) -> List[Dict[str, Any]]:
        """Run all load test scenarios"""
        scenarios = [
            {
                "name": "baseline",
                "users": 50,
                "spawn_rate": 5,
                "run_time": "2m",
                "description": "Baseline performance with light load"
            },
            {
                "name": "normal_load",
                "users": 200,
                "spawn_rate": 20,
                "run_time": "5m",
                "description": "Normal expected load"
            },
            {
                "name": "peak_load",
                "users": 500,
                "spawn_rate": 50,
                "run_time": "5m",
                "description": "Peak traffic hours"
            },
            {
                "name": "stress_test",
                "users": 1000,
                "spawn_rate": 100,
                "run_time": "5m",
                "description": "System under stress"
            },
            {
                "name": "spike_test",
                "users": 2000,
                "spawn_rate": 500,
                "run_time": "2m",
                "description": "Sudden traffic spike"
            }
        ]
        
        results = []
        for scenario in scenarios:
            result = self.run_scenario(
                scenario["name"],
                scenario["users"],
                scenario["spawn_rate"],
                scenario["run_time"]
            )
            result["description"] = scenario["description"]
            results.append(result)
            
            # Cool down between scenarios
            print(f"\nCooling down for 30 seconds...")
            time.sleep(30)
        
        return results
    
    def analyze_results(self, results: List[Dict[str, Any]]):
        """Analyze and visualize load test results"""
        # Convert to DataFrame
        df = pd.DataFrame(results)
        
        # Create visualizations
        fig, axes = plt.subplots(2, 3, figsize=(18, 12))
        fig.suptitle('Load Test Results Analysis', fontsize=16)
        
        # 1. Response times by scenario
        ax1 = axes[0, 0]
        scenarios = df['scenario']
        x_pos = range(len(scenarios))
        
        ax1.bar(x_pos, df['avg_response_time'], label='Average', alpha=0.7)
        ax1.bar(x_pos, df['p95_response_time'], label='95th Percentile', alpha=0.7)
        ax1.bar(x_pos, df['p99_response_time'], label='99th Percentile', alpha=0.7)
        
        ax1.set_xticks(x_pos)
        ax1.set_xticklabels(scenarios, rotation=45)
        ax1.set_ylabel('Response Time (ms)')
        ax1.set_title('Response Times by Scenario')
        ax1.legend()
        
        # 2. Throughput (RPS)
        ax2 = axes[0, 1]
        ax2.plot(scenarios, df['rps'], marker='o', markersize=10, linewidth=2)
        ax2.set_xlabel('Scenario')
        ax2.set_ylabel('Requests per Second')
        ax2.set_title('Throughput (RPS)')
        ax2.tick_params(axis='x', rotation=45)
        
        # 3. Failure Rate
        ax3 = axes[0, 2]
        ax3.bar(x_pos, df['failure_rate'] * 100)
        ax3.set_xticks(x_pos)
        ax3.set_xticklabels(scenarios, rotation=45)
        ax3.set_ylabel('Failure Rate (%)')
        ax3.set_title('Failure Rate by Scenario')
        ax3.axhline(y=1, color='r', linestyle='--', label='1% threshold')
        ax3.legend()
        
        # 4. Users vs Response Time
        ax4 = axes[1, 0]
        ax4.scatter(df['users'], df['avg_response_time'], s=100, alpha=0.7, label='Avg Response Time')
        ax4.scatter(df['users'], df['p95_response_time'], s=100, alpha=0.7, label='95th Percentile')
        ax4.set_xlabel('Number of Users')
        ax4.set_ylabel('Response Time (ms)')
        ax4.set_title('Users vs Response Time')
        ax4.legend()
        
        # 5. Performance Distribution
        ax5 = axes[1, 1]
        response_times = ['avg_response_time', 'p90_response_time', 'p95_response_time', 'p99_response_time']
        for i, scenario in enumerate(df.to_dict('records')):
            if 'error' not in scenario:
                values = [scenario[rt] for rt in response_times]
                ax5.plot(['Avg', 'P90', 'P95', 'P99'], values, marker='o', label=scenario['scenario'])
        ax5.set_ylabel('Response Time (ms)')
        ax5.set_title('Response Time Distribution')
        ax5.legend()
        
        # 6. Summary Statistics
        ax6 = axes[1, 2]
        ax6.axis('tight')
        ax6.axis('off')
        
        summary_text = "Performance Summary:\n\n"
        for _, row in df.iterrows():
            if 'error' not in row:
                summary_text += f"{row['scenario']}:\n"
                summary_text += f"  Total Requests: {row['total_requests']:,}\n"
                summary_text += f"  Failure Rate: {row['failure_rate']:.2%}\n"
                summary_text += f"  Avg Response: {row['avg_response_time']:.0f}ms\n"
                summary_text += f"  RPS: {row['rps']:.1f}\n\n"
        
        ax6.text(0.1, 0.9, summary_text, transform=ax6.transAxes,
                fontsize=10, verticalalignment='top', fontfamily='monospace')
        
        plt.tight_layout()
        plt.savefig(self.results_dir / f'load_test_analysis_{self.timestamp}.png', dpi=300)
        plt.show()
        
        # Save detailed results
        self.save_results(results, df)
        
        # Print performance assessment
        self.print_performance_assessment(df)
    
    def save_results(self, results: List[Dict[str, Any]], df: pd.DataFrame):
        """Save results to files"""
        # Save raw results as JSON
        with open(self.results_dir / f'results_{self.timestamp}.json', 'w') as f:
            json.dump({
                'timestamp': self.timestamp,
                'host': self.host,
                'results': results
            }, f, indent=2)
        
        # Save as CSV
        df.to_csv(self.results_dir / f'results_{self.timestamp}.csv', index=False)
        
        # Generate HTML report
        self.generate_html_report(results, df)
    
    def generate_html_report(self, results: List[Dict[str, Any]], df: pd.DataFrame):
        """Generate HTML report"""
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Load Test Report - {self.timestamp}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1, h2 {{ color: #333; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .good {{ color: green; }}
                .warning {{ color: orange; }}
                .bad {{ color: red; }}
                .summary {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>Load Test Report</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>Host: {self.host}</p>
            
            <h2>Summary</h2>
            <div class="summary">
                <p>Total Scenarios: {len(results)}</p>
                <p>Max RPS Achieved: {df['rps'].max():.1f}</p>
                <p>Average Failure Rate: {df['failure_rate'].mean():.2%}</p>
            </div>
            
            <h2>Detailed Results</h2>
            <table>
                <tr>
                    <th>Scenario</th>
                    <th>Users</th>
                    <th>Total Requests</th>
                    <th>RPS</th>
                    <th>Avg Response (ms)</th>
                    <th>P95 Response (ms)</th>
                    <th>P99 Response (ms)</th>
                    <th>Failure Rate</th>
                    <th>Status</th>
                </tr>
        """
        
        for _, row in df.iterrows():
            if 'error' not in row:
                # Determine status
                if row['failure_rate'] < 0.01 and row['avg_response_time'] < 200:
                    status = '<span class="good">✓ Good</span>'
                elif row['failure_rate'] < 0.05 and row['avg_response_time'] < 500:
                    status = '<span class="warning">⚠ Warning</span>'
                else:
                    status = '<span class="bad">✗ Poor</span>'
                
                html += f"""
                <tr>
                    <td>{row['scenario']}</td>
                    <td>{row['users']}</td>
                    <td>{row['total_requests']:,}</td>
                    <td>{row['rps']:.1f}</td>
                    <td>{row['avg_response_time']:.0f}</td>
                    <td>{row['p95_response_time']:.0f}</td>
                    <td>{row['p99_response_time']:.0f}</td>
                    <td>{row['failure_rate']:.2%}</td>
                    <td>{status}</td>
                </tr>
                """
        
        html += """
            </table>
            
            <h2>Performance Thresholds</h2>
            <ul>
                <li><span class="good">Good:</span> < 200ms avg response, < 1% failure rate</li>
                <li><span class="warning">Warning:</span> < 500ms avg response, < 5% failure rate</li>
                <li><span class="bad">Poor:</span> > 500ms avg response or > 5% failure rate</li>
            </ul>
        </body>
        </html>
        """
        
        with open(self.results_dir / f'report_{self.timestamp}.html', 'w') as f:
            f.write(html)
    
    def print_performance_assessment(self, df: pd.DataFrame):
        """Print performance assessment"""
        print("\n" + "="*60)
        print("PERFORMANCE ASSESSMENT")
        print("="*60)
        
        # Overall assessment
        avg_failure_rate = df['failure_rate'].mean()
        max_rps = df['rps'].max()
        avg_response = df['avg_response_time'].mean()
        
        print(f"\nOverall Metrics:")
        print(f"  Average Failure Rate: {avg_failure_rate:.2%}")
        print(f"  Maximum RPS: {max_rps:.1f}")
        print(f"  Average Response Time: {avg_response:.0f}ms")
        
        # Determine overall status
        if avg_failure_rate < 0.01 and avg_response < 200:
            print("\n✅ EXCELLENT: System performs very well under load")
        elif avg_failure_rate < 0.05 and avg_response < 500:
            print("\n⚠️  ACCEPTABLE: System handles load but could be optimized")
        else:
            print("\n❌ POOR: System struggles under load, optimization needed")
        
        # Specific recommendations
        print("\nRecommendations:")
        
        if avg_failure_rate > 0.01:
            print("  - Investigate and fix causes of request failures")
        
        if avg_response > 300:
            print("  - Optimize slow endpoints to reduce response times")
            print("  - Consider implementing caching for frequently accessed data")
        
        if max_rps < 100:
            print("  - Scale up infrastructure to handle more concurrent requests")
            print("  - Optimize database queries and connection pooling")
        
        # Find bottlenecks
        stress_test = df[df['scenario'] == 'stress_test'].iloc[0] if 'stress_test' in df['scenario'].values else None
        if stress_test is not None and 'error' not in stress_test:
            if stress_test['failure_rate'] > 0.1:
                print("  - System fails under stress - investigate resource limits")
            if stress_test['p99_response_time'] > 5000:
                print("  - Very high P99 latency under stress - check for resource contention")


def main():
    """Main execution function"""
    print("AI Road Trip Storyteller - Load Testing Suite")
    print("=" * 60)
    
    # Initialize executor
    executor = LoadTestExecutor()
    
    # Check dependencies
    if not executor.check_dependencies():
        print("Failed to install dependencies")
        return
    
    # Run load tests
    print("\nStarting load test scenarios...")
    results = executor.run_all_scenarios()
    
    # Analyze results
    print("\nAnalyzing results...")
    executor.analyze_results(results)
    
    print(f"\nAll results saved in: {executor.results_dir}")
    print("Load testing complete!")


if __name__ == "__main__":
    main()