#!/usr/bin/env python3
"""
Production Readiness Runner

This script orchestrates all agents to achieve production readiness
while maintaining codebase coherence and quality standards.
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import json
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.production_readiness.orchestration_framework import (
    Task, TaskPriority, TaskStatus, SharedContext, ContextCoordinatorAgent
)
from scripts.production_readiness.specialized_agents import (
    CodebaseAnalyzerAgent,
    TestGeneratorAgent,
    ImplementationFixerAgent,
    ConfigurationAgent
)

# Configure logging with detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_readiness.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def create_comprehensive_task_list() -> List[Task]:
    """Create comprehensive task list for production readiness"""
    
    tasks = []
    
    # Phase 1: Analysis and Understanding
    tasks.extend([
        Task(
            id="analyze-codebase-patterns",
            name="analyze_patterns",
            description="Analyze codebase patterns and conventions",
            priority=TaskPriority.CRITICAL,
            agent_type="analyzer"
        ),
        Task(
            id="analyze-api-structure",
            name="analyze_api_structure",
            description="Analyze API endpoint structure",
            priority=TaskPriority.CRITICAL,
            agent_type="analyzer"
        ),
        Task(
            id="analyze-dependencies",
            name="analyze_dependencies",
            description="Analyze service dependencies",
            priority=TaskPriority.CRITICAL,
            agent_type="analyzer"
        ),
    ])
    
    # Phase 2: Testing Infrastructure
    tasks.extend([
        Task(
            id="fix-jest-mobile",
            name="fix_jest_config",
            description="Fix Jest/Babel configuration for mobile tests",
            priority=TaskPriority.CRITICAL,
            agent_type="configuration",
            dependencies=["analyze-codebase-patterns"]
        ),
        Task(
            id="analyze-test-coverage",
            name="analyze_coverage",
            description="Analyze current test coverage gaps",
            priority=TaskPriority.CRITICAL,
            agent_type="test_generator",
            dependencies=["fix-jest-mobile"]
        ),
        Task(
            id="generate-unit-tests",
            name="generate_unit_tests",
            description="Generate unit tests for uncovered code",
            priority=TaskPriority.CRITICAL,
            agent_type="test_generator",
            dependencies=["analyze-test-coverage"]
        ),
        Task(
            id="generate-mvp-tests",
            name="generate_mvp_tests",
            description="Generate comprehensive MVP test suite",
            priority=TaskPriority.CRITICAL,
            agent_type="test_generator",
            dependencies=["analyze-test-coverage"]
        ),
    ])
    
    # Phase 3: Implementation Fixes
    tasks.extend([
        Task(
            id="find-placeholders",
            name="find_placeholders",
            description="Find all placeholder implementations",
            priority=TaskPriority.HIGH,
            agent_type="implementation",
            dependencies=["analyze-codebase-patterns"]
        ),
        Task(
            id="implement-booking-agent",
            name="implement_booking_agent",
            description="Implement booking agent service",
            priority=TaskPriority.HIGH,
            agent_type="implementation",
            dependencies=["find-placeholders", "analyze-api-structure"]
        ),
        Task(
            id="implement-video-service",
            name="implement_journey_video",
            description="Implement journey video service",
            priority=TaskPriority.HIGH,
            agent_type="implementation",
            dependencies=["find-placeholders", "analyze-dependencies"]
        ),
    ])
    
    # Phase 4: Configuration and Deployment
    tasks.extend([
        Task(
            id="update-production-env",
            name="update_env_production",
            description="Update production environment configuration",
            priority=TaskPriority.CRITICAL,
            agent_type="configuration"
        ),
        Task(
            id="update-cicd",
            name="update_cicd_config",
            description="Update CI/CD pipeline for Google Cloud",
            priority=TaskPriority.CRITICAL,
            agent_type="configuration",
            dependencies=["update-production-env"]
        ),
    ])
    
    # Phase 5: Code Quality
    tasks.extend([
        Task(
            id="lint-backend-code",
            name="lint_backend",
            description="Run backend linting and auto-fix issues",
            priority=TaskPriority.HIGH,
            agent_type="quality",
            dependencies=["implement-booking-agent", "implement-video-service"]
        ),
        Task(
            id="lint-mobile-code",
            name="lint_mobile",
            description="Run mobile linting and auto-fix issues",
            priority=TaskPriority.HIGH,
            agent_type="quality",
            dependencies=["fix-jest-mobile"]
        ),
        Task(
            id="type-check-backend",
            name="type_check",
            description="Run type checking on backend code",
            priority=TaskPriority.HIGH,
            agent_type="quality",
            dependencies=["lint-backend-code"]
        ),
        Task(
            id="security-scan-backend",
            name="security_scan",
            description="Run security scanning on backend",
            priority=TaskPriority.HIGH,
            agent_type="quality",
            dependencies=["lint-backend-code"]
        ),
    ])
    
    # Phase 6: Integration Testing
    tasks.extend([
        Task(
            id="run-unit-tests-final",
            name="run_unit_tests",
            description="Run all unit tests with coverage check",
            priority=TaskPriority.CRITICAL,
            agent_type="testing",
            dependencies=["generate-unit-tests", "lint-backend-code"]
        ),
        Task(
            id="run-integration-tests-final",
            name="run_integration_tests",
            description="Run all integration tests",
            priority=TaskPriority.CRITICAL,
            agent_type="testing",
            dependencies=["run-unit-tests-final"]
        ),
        Task(
            id="check-coverage-final",
            name="check_coverage",
            description="Verify 80% test coverage requirement",
            priority=TaskPriority.CRITICAL,
            agent_type="testing",
            dependencies=["run-unit-tests-final"]
        ),
    ])
    
    # Phase 7: Infrastructure Setup
    tasks.extend([
        Task(
            id="setup-monitoring-infra",
            name="setup_monitoring",
            description="Setup monitoring and alerting infrastructure",
            priority=TaskPriority.MEDIUM,
            agent_type="infrastructure",
            dependencies=["update-cicd"]
        ),
        Task(
            id="configure-secrets-prod",
            name="configure_secrets",
            description="Configure production secrets in Secret Manager",
            priority=TaskPriority.CRITICAL,
            agent_type="infrastructure",
            dependencies=["update-production-env"]
        ),
    ])
    
    return tasks

class ProductionReadinessOrchestrator:
    """Main orchestrator for production readiness"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.project_root = Path("/mnt/c/users/jared/onedrive/desktop/roadtrip")
        
    async def run(self):
        """Run the complete production readiness process"""
        
        logger.info("=" * 80)
        logger.info("Starting Production Readiness Orchestration")
        logger.info("=" * 80)
        
        # Initialize shared context
        context = SharedContext(
            project_root=self.project_root,
            codebase_standards={
                "backend_framework": "FastAPI",
                "frontend_framework": "React Native",
                "test_framework": "pytest",
                "mobile_test_framework": "jest",
                "style_guide": "black + flake8",
                "type_checking": "mypy",
                "min_coverage": 80,
                "ai_provider": "Google Vertex AI",
                "deployment_platform": "Google Cloud Run"
            },
            production_requirements={
                "test_coverage": 80,
                "security_scan": True,
                "monitoring": True,
                "documentation": True,
                "ci_cd": True,
                "canary_deployment": True,
                "auto_scaling": True,
                "backup_strategy": True
            },
            completed_tasks=set(),
            discovered_issues=[],
            code_metrics={},
            test_coverage={}
        )
        
        # Initialize coordinator
        coordinator = ContextCoordinatorAgent(context)
        
        # Register all specialized agents
        logger.info("Registering specialized agents...")
        
        # Import code quality agent from orchestration_framework
        from orchestration_framework import (
            CodeQualityAgent, TestingAgent, InfrastructureAgent, ImplementationAgent
        )
        
        coordinator.register_agent("analyzer", CodebaseAnalyzerAgent(context))
        coordinator.register_agent("test_generator", TestGeneratorAgent(context))
        coordinator.register_agent("implementation", ImplementationFixerAgent(context))
        coordinator.register_agent("configuration", ConfigurationAgent(context))
        coordinator.register_agent("quality", CodeQualityAgent("CodeQuality", context))
        coordinator.register_agent("testing", TestingAgent("Testing", context))
        coordinator.register_agent("infrastructure", InfrastructureAgent("Infrastructure", context))
        
        # Create comprehensive task list
        logger.info("Creating comprehensive task list...")
        tasks = create_comprehensive_task_list()
        coordinator.task_queue = tasks
        
        logger.info(f"Total tasks to execute: {len(tasks)}")
        
        # Execute orchestration
        try:
            await coordinator.orchestrate()
        except Exception as e:
            logger.error(f"Orchestration failed: {e}")
            raise
            
        # Generate comprehensive report
        await self.generate_report(coordinator, context)
        
    async def generate_report(self, coordinator: ContextCoordinatorAgent, context: SharedContext):
        """Generate comprehensive production readiness report"""
        
        logger.info("\n" + "=" * 80)
        logger.info("PRODUCTION READINESS REPORT")
        logger.info("=" * 80)
        
        # Calculate statistics
        total_tasks = len(coordinator.execution_history)
        completed_tasks = len([t for t in coordinator.execution_history if t.status == TaskStatus.COMPLETED])
        failed_tasks = len([t for t in coordinator.execution_history if t.status == TaskStatus.FAILED])
        
        success_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        
        # Time statistics
        elapsed_time = datetime.now() - self.start_time
        
        logger.info(f"\nExecution Summary:")
        logger.info(f"  Total Tasks: {total_tasks}")
        logger.info(f"  Completed: {completed_tasks} ({success_rate:.1f}%)")
        logger.info(f"  Failed: {failed_tasks}")
        logger.info(f"  Execution Time: {elapsed_time}")
        
        # Failed tasks details
        if failed_tasks > 0:
            logger.warning("\nFailed Tasks:")
            for task in coordinator.execution_history:
                if task.status == TaskStatus.FAILED:
                    logger.warning(f"  - {task.name}: {task.error}")
                    
        # Discovered issues
        if context.discovered_issues:
            logger.warning(f"\nDiscovered Issues ({len(context.discovered_issues)}):")
            for issue in context.discovered_issues[:10]:  # Show first 10
                logger.warning(f"  - {issue}")
                
        # Code metrics
        if context.code_metrics:
            logger.info("\nCode Metrics:")
            for metric, value in context.code_metrics.items():
                logger.info(f"  - {metric}: {value}")
                
        # Test coverage
        if context.test_coverage:
            logger.info("\nTest Coverage:")
            avg_coverage = sum(context.test_coverage.values()) / len(context.test_coverage)
            logger.info(f"  Average Coverage: {avg_coverage:.1f}%")
            logger.info(f"  Files Meeting 80% Requirement: {len([c for c in context.test_coverage.values() if c >= 80])}/{len(context.test_coverage)}")
            
        # Production readiness assessment
        readiness_score = self.calculate_readiness_score(coordinator, context)
        
        logger.info(f"\n{'=' * 80}")
        logger.info(f"PRODUCTION READINESS SCORE: {readiness_score:.1f}%")
        logger.info(f"{'=' * 80}")
        
        if readiness_score >= 90:
            logger.info("✅ READY FOR PRODUCTION DEPLOYMENT")
        elif readiness_score >= 70:
            logger.warning("⚠️  NEARLY READY - Address remaining issues before deployment")
        else:
            logger.error("❌ NOT READY FOR PRODUCTION - Significant work required")
            
        # Save detailed report
        report_data = {
            "execution_time": str(elapsed_time),
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "failed": failed_tasks,
                "success_rate": success_rate
            },
            "issues": context.discovered_issues,
            "metrics": context.code_metrics,
            "coverage": context.test_coverage,
            "readiness_score": readiness_score,
            "timestamp": datetime.now().isoformat()
        }
        
        report_path = self.project_root / "production_readiness_report.json"
        with open(report_path, 'w') as f:
            json.dump(report_data, f, indent=2)
            
        logger.info(f"\nDetailed report saved to: {report_path}")
        
        # Generate action items
        await self.generate_action_items(coordinator, context)
        
    def calculate_readiness_score(self, coordinator: ContextCoordinatorAgent, context: SharedContext) -> float:
        """Calculate overall production readiness score"""
        
        scores = []
        
        # Task completion score (30%)
        task_score = len([t for t in coordinator.execution_history if t.status == TaskStatus.COMPLETED]) / len(coordinator.execution_history) * 100
        scores.append(task_score * 0.3)
        
        # Test coverage score (25%)
        if context.test_coverage:
            avg_coverage = sum(context.test_coverage.values()) / len(context.test_coverage)
            coverage_score = min(avg_coverage / 80 * 100, 100)  # 80% is the target
            scores.append(coverage_score * 0.25)
        else:
            scores.append(0)
            
        # Critical tasks completion (25%)
        critical_tasks = [t for t in coordinator.execution_history if t.priority == TaskPriority.CRITICAL]
        critical_completed = len([t for t in critical_tasks if t.status == TaskStatus.COMPLETED])
        critical_score = (critical_completed / len(critical_tasks) * 100) if critical_tasks else 0
        scores.append(critical_score * 0.25)
        
        # No blocking issues (20%)
        blocking_issues = len([i for i in context.discovered_issues if "critical" in str(i).lower() or "blocker" in str(i).lower()])
        issue_score = 100 if blocking_issues == 0 else max(0, 100 - blocking_issues * 20)
        scores.append(issue_score * 0.2)
        
        return sum(scores)
        
    async def generate_action_items(self, coordinator: ContextCoordinatorAgent, context: SharedContext):
        """Generate prioritized action items"""
        
        logger.info("\n📋 ACTION ITEMS:")
        
        # High priority actions
        high_priority = []
        
        # Check for failed critical tasks
        failed_critical = [t for t in coordinator.execution_history 
                         if t.status == TaskStatus.FAILED and t.priority == TaskPriority.CRITICAL]
        
        for task in failed_critical:
            high_priority.append(f"Fix failed critical task: {task.description}")
            
        # Check test coverage
        if context.test_coverage:
            low_coverage_files = [f for f, c in context.test_coverage.items() if c < 80]
            if low_coverage_files:
                high_priority.append(f"Increase test coverage for {len(low_coverage_files)} files below 80%")
                
        # Check for security issues
        security_issues = [i for i in context.discovered_issues if "security" in str(i).lower()]
        if security_issues:
            high_priority.append(f"Address {len(security_issues)} security vulnerabilities")
            
        if high_priority:
            logger.warning("\nHigh Priority:")
            for idx, item in enumerate(high_priority, 1):
                logger.warning(f"  {idx}. {item}")
                
        # Medium priority actions
        medium_priority = []
        
        # Documentation
        if "documentation" not in context.code_metrics:
            medium_priority.append("Complete API documentation with OpenAPI")
            
        # Monitoring
        if "monitoring_configured" not in context.code_metrics:
            medium_priority.append("Configure production monitoring and alerts")
            
        if medium_priority:
            logger.info("\nMedium Priority:")
            for idx, item in enumerate(medium_priority, 1):
                logger.info(f"  {idx}. {item}")
                
        # Low priority enhancements
        logger.info("\nLow Priority Enhancements:")
        logger.info("  1. Add performance benchmarking")
        logger.info("  2. Implement feature flags for gradual rollouts")
        logger.info("  3. Create operational runbooks")
        logger.info("  4. Set up automated dependency updates")

async def main():
    """Main entry point"""
    orchestrator = ProductionReadinessOrchestrator()
    
    try:
        await orchestrator.run()
    except KeyboardInterrupt:
        logger.warning("\nOrchestration interrupted by user")
    except Exception as e:
        logger.error(f"\nOrchestration failed with error: {e}")
        raise

if __name__ == "__main__":
    # Ensure we're in the project root
    os.chdir(Path(__file__).parent.parent.parent)
    
    # Run the orchestration
    asyncio.run(main())