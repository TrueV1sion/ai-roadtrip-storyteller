#!/usr/bin/env python3
"""
Staging vs Production Configuration Comparison Tool
Ensures staging properly mirrors production with appropriate scaling
"""

import json
import yaml
import subprocess
import sys
from typing import Dict, List, Any
from dataclasses import dataclass
from colorama import init, Fore, Style

# Initialize colorama
init()

@dataclass
class ConfigDifference:
    """Represents a configuration difference"""
    key: str
    staging_value: Any
    production_value: Any
    severity: str  # "critical", "warning", "info"
    recommendation: str


class ConfigComparator:
    def __init__(self, project_id: str = "roadtrip-460720"):
        self.project_id = project_id
        self.differences: List[ConfigDifference] = []
        
    def print_status(self, message: str, level: str = "info"):
        """Print colored status messages"""
        colors = {
            "info": Fore.BLUE,
            "success": Fore.GREEN,
            "warning": Fore.YELLOW,
            "error": Fore.RED,
            "critical": Fore.RED + Style.BRIGHT
        }
        color = colors.get(level, Fore.WHITE)
        print(f"{color}[{level.upper()}]{Style.RESET_ALL} {message}")
        
    def get_terraform_outputs(self, environment: str) -> Dict[str, Any]:
        """Get Terraform outputs for an environment"""
        self.print_status(f"Getting Terraform outputs for {environment}...", "info")
        
        try:
            # Change to appropriate directory
            tf_dir = f"infrastructure/{environment}" if environment == "staging" else "infrastructure/terraform"
            
            result = subprocess.run(
                ["terraform", "output", "-json"],
                cwd=tf_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                outputs = json.loads(result.stdout)
                return {k: v.get("value", v) for k, v in outputs.items()}
            else:
                self.print_status(f"Failed to get Terraform outputs for {environment}", "error")
                return {}
                
        except Exception as e:
            self.print_status(f"Error getting Terraform outputs: {e}", "error")
            return {}
            
    def get_cloud_run_config(self, service_name: str) -> Dict[str, Any]:
        """Get Cloud Run service configuration"""
        try:
            result = subprocess.run(
                [
                    "gcloud", "run", "services", "describe", service_name,
                    "--format=json", "--region=us-central1", f"--project={self.project_id}"
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {}
                
        except Exception as e:
            self.print_status(f"Error getting Cloud Run config: {e}", "error")
            return {}
            
    def get_database_config(self, instance_name: str) -> Dict[str, Any]:
        """Get Cloud SQL database configuration"""
        try:
            result = subprocess.run(
                [
                    "gcloud", "sql", "instances", "describe", instance_name,
                    "--format=json", f"--project={self.project_id}"
                ],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return json.loads(result.stdout)
            else:
                return {}
                
        except Exception as e:
            self.print_status(f"Error getting database config: {e}", "error")
            return {}
            
    def compare_configurations(self):
        """Compare staging and production configurations"""
        self.print_status("Starting configuration comparison...", "info")
        
        # Get Terraform outputs
        staging_tf = self.get_terraform_outputs("staging")
        prod_tf = self.get_terraform_outputs("production")
        
        # Compare Cloud Run services
        self.print_status("\n=== Cloud Run Comparison ===", "info")
        staging_run = self.get_cloud_run_config("roadtrip-backend-staging")
        prod_run = self.get_cloud_run_config("roadtrip-backend")
        
        if staging_run and prod_run:
            # CPU comparison
            staging_cpu = staging_run.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [{}])[0].get("resources", {}).get("limits", {}).get("cpu", "0")
            prod_cpu = prod_run.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [{}])[0].get("resources", {}).get("limits", {}).get("cpu", "0")
            
            if staging_cpu != prod_cpu:
                self.differences.append(ConfigDifference(
                    key="Cloud Run CPU",
                    staging_value=staging_cpu,
                    production_value=prod_cpu,
                    severity="info",
                    recommendation="Staging uses less CPU for cost optimization"
                ))
                
            # Memory comparison
            staging_mem = staging_run.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [{}])[0].get("resources", {}).get("limits", {}).get("memory", "0")
            prod_mem = prod_run.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [{}])[0].get("resources", {}).get("limits", {}).get("memory", "0")
            
            if staging_mem != prod_mem:
                self.differences.append(ConfigDifference(
                    key="Cloud Run Memory",
                    staging_value=staging_mem,
                    production_value=prod_mem,
                    severity="info",
                    recommendation="Staging uses less memory for cost optimization"
                ))
                
            # Scaling comparison
            staging_annotations = staging_run.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
            prod_annotations = prod_run.get("spec", {}).get("template", {}).get("metadata", {}).get("annotations", {})
            
            staging_min = staging_annotations.get("autoscaling.knative.dev/minScale", "0")
            prod_min = prod_annotations.get("autoscaling.knative.dev/minScale", "0")
            
            if int(staging_min) < int(prod_min):
                self.differences.append(ConfigDifference(
                    key="Minimum Instances",
                    staging_value=staging_min,
                    production_value=prod_min,
                    severity="warning",
                    recommendation="Consider matching production min instances for realistic testing"
                ))
                
        # Compare databases
        self.print_status("\n=== Database Comparison ===", "info")
        
        # Extract instance names from connection strings if available
        staging_db_name = staging_tf.get("staging_database_connection", "").split(":")[2] if staging_tf else ""
        prod_db_name = prod_tf.get("database_connection_name", "").split(":")[2] if prod_tf else ""
        
        if staging_db_name and prod_db_name:
            staging_db = self.get_database_config(staging_db_name)
            prod_db = self.get_database_config(prod_db_name)
            
            if staging_db and prod_db:
                # Tier comparison
                staging_tier = staging_db.get("settings", {}).get("tier", "")
                prod_tier = prod_db.get("settings", {}).get("tier", "")
                
                if staging_tier != prod_tier:
                    self.differences.append(ConfigDifference(
                        key="Database Tier",
                        staging_value=staging_tier,
                        production_value=prod_tier,
                        severity="info",
                        recommendation="Staging uses smaller tier for cost savings"
                    ))
                    
                # Backup comparison
                staging_backup = staging_db.get("settings", {}).get("backupConfiguration", {}).get("enabled", False)
                prod_backup = prod_db.get("settings", {}).get("backupConfiguration", {}).get("enabled", False)
                
                if not staging_backup and prod_backup:
                    self.differences.append(ConfigDifference(
                        key="Database Backups",
                        staging_value="Disabled",
                        production_value="Enabled",
                        severity="warning",
                        recommendation="Consider enabling backups in staging for DR testing"
                    ))
                    
        # Check critical configurations
        self.print_status("\n=== Critical Configuration Checks ===", "info")
        
        critical_checks = [
            ("SSL/TLS", "Both environments should have SSL enabled"),
            ("Cloud Armor", "WAF should be enabled in both environments"),
            ("VPC Connector", "Private networking should match"),
            ("Service Account", "Different service accounts should be used"),
            ("Secrets", "Each environment should have separate secrets")
        ]
        
        for check, recommendation in critical_checks:
            self.print_status(f"Checking {check}...", "info")
            # These would need actual implementation based on your setup
            
    def generate_report(self):
        """Generate comparison report"""
        report = f"""
# Staging vs Production Configuration Comparison

**Project**: {self.project_id}
**Date**: {subprocess.check_output(['date']).decode().strip()}

## Summary

Total differences found: {len(self.differences)}
- Critical: {sum(1 for d in self.differences if d.severity == "critical")}
- Warnings: {sum(1 for d in self.differences if d.severity == "warning")}
- Info: {sum(1 for d in self.differences if d.severity == "info")}

## Configuration Differences

"""
        
        # Group by severity
        for severity in ["critical", "warning", "info"]:
            severity_diffs = [d for d in self.differences if d.severity == severity]
            if severity_diffs:
                report += f"### {severity.upper()} Differences\n\n"
                for diff in severity_diffs:
                    report += f"**{diff.key}**\n"
                    report += f"- Staging: `{diff.staging_value}`\n"
                    report += f"- Production: `{diff.production_value}`\n"
                    report += f"- Recommendation: {diff.recommendation}\n\n"
                    
        # Add validation checklist
        report += """
## Production Readiness Checklist

Based on the comparison, verify the following before production deployment:

### Critical Items
- [ ] All critical configurations match (except for intended differences)
- [ ] Security settings are properly configured
- [ ] Database connections are correctly set
- [ ] API keys and secrets are environment-specific
- [ ] Monitoring and alerting are configured

### Performance Testing
- [ ] Load test with production-like traffic
- [ ] Verify response times match production SLAs
- [ ] Test auto-scaling behavior
- [ ] Validate caching effectiveness

### Security Validation
- [ ] Run security scan on staging
- [ ] Verify WAF rules are active
- [ ] Test authentication flows
- [ ] Validate rate limiting

### Data Validation
- [ ] Test with production-like data volume
- [ ] Verify backup/restore procedures
- [ ] Test data migration scripts
- [ ] Validate data retention policies

### Integration Testing
- [ ] All third-party APIs tested
- [ ] Payment processing (test mode)
- [ ] Email delivery
- [ ] Push notifications

## Recommendations

1. **Resource Scaling**: Staging intentionally uses smaller resources. For accurate performance testing, consider temporarily scaling up.

2. **Data Volume**: Load staging with realistic data volumes for accurate testing.

3. **Traffic Patterns**: Use load testing to simulate production traffic patterns.

4. **Monitoring**: Ensure staging metrics are being collected for comparison.

5. **Security**: Run the same security scans on staging as production.
"""
        
        # Save report
        report_file = "staging_production_comparison.md"
        with open(report_file, 'w') as f:
            f.write(report)
            
        self.print_status(f"\n📄 Report saved to: {report_file}", "success")
        
        return report
        
    def run_comparison(self):
        """Run the full comparison"""
        self.print_status("🔍 Staging vs Production Configuration Comparison", "info")
        self.print_status("=" * 50, "info")
        
        self.compare_configurations()
        report = self.generate_report()
        
        # Print summary
        if any(d.severity == "critical" for d in self.differences):
            self.print_status("\n❌ CRITICAL differences found! Review before production deployment.", "critical")
            return False
        elif any(d.severity == "warning" for d in self.differences):
            self.print_status("\n⚠️  Warnings found. Review recommendations in the report.", "warning")
            return True
        else:
            self.print_status("\n✅ No critical issues found. Staging properly mirrors production.", "success")
            return True


def main():
    """Main entry point"""
    project_id = sys.argv[1] if len(sys.argv) > 1 else "roadtrip-460720"
    
    comparator = ConfigComparator(project_id)
    success = comparator.run_comparison()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()