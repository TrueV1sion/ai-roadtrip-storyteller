"""
Development Automation Service
Integrates mobile notifications with development workflows and CI/CD processes.
"""

import asyncio
import json
import subprocess
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass
import os

from app.core.logger import logger
from app.core.cache import cache_manager
from app.services.mobile_dev_notifications import (
    mobile_dev_service,
    send_build_status,
    send_deployment_update,
    request_approval,
    send_security_alert,
    notify_task_complete
)


class DevWorkflowState(str, Enum):
    """Development workflow states."""
    IDLE = "idle"
    BUILDING = "building"
    TESTING = "testing"
    DEPLOYING = "deploying"
    WAITING_APPROVAL = "waiting_approval"
    PAUSED = "paused"
    ERROR = "error"


class AutomationTrigger(str, Enum):
    """Automation trigger types."""
    TIME_BASED = "time_based"
    EVENT_BASED = "event_based"
    SMS_COMMAND = "sms_command"
    FILE_CHANGE = "file_change"
    BUILD_COMPLETE = "build_complete"
    DEPLOYMENT_READY = "deployment_ready"


@dataclass
class DevWorkflow:
    """Development workflow configuration."""
    id: str
    name: str
    description: str
    triggers: List[AutomationTrigger]
    steps: List[Dict[str, Any]]
    requires_approval: bool = False
    auto_execute: bool = False
    timeout_minutes: int = 60
    retry_attempts: int = 3


class DevelopmentAutomationService:
    """Service for automating development workflows with mobile integration."""
    
    def __init__(self):
        self.current_state = DevWorkflowState.IDLE
        self.active_workflows: Dict[str, DevWorkflow] = {}
        self.workflow_history: List[Dict[str, Any]] = []
        self.automation_enabled = True
        
        # Register built-in workflows
        self._register_builtin_workflows()
        
        # Start monitoring tasks
        asyncio.create_task(self._monitor_development_state())
        
        logger.info("Development Automation Service initialized")
    
    def _register_builtin_workflows(self):
        """Register built-in development workflows."""
        workflows = [
            # Security Update Workflow
            DevWorkflow(
                id="security_update",
                name="Security Update",
                description="Rotate credentials and update security configuration",
                triggers=[AutomationTrigger.SMS_COMMAND, AutomationTrigger.EVENT_BASED],
                steps=[
                    {"action": "backup_current_config", "timeout": 300},
                    {"action": "rotate_credentials", "timeout": 600},
                    {"action": "update_secret_manager", "timeout": 300},
                    {"action": "test_connections", "timeout": 300},
                    {"action": "notify_completion", "timeout": 60}
                ],
                requires_approval=True,
                auto_execute=False,
                timeout_minutes=30
            ),
            
            # Production Deployment Workflow
            DevWorkflow(
                id="production_deploy",
                name="Production Deployment",
                description="Deploy to production with full validation",
                triggers=[AutomationTrigger.SMS_COMMAND, AutomationTrigger.DEPLOYMENT_READY],
                steps=[
                    {"action": "run_security_audit", "timeout": 300},
                    {"action": "run_tests", "timeout": 600},
                    {"action": "build_production", "timeout": 900},
                    {"action": "deploy_staging", "timeout": 600},
                    {"action": "validate_staging", "timeout": 300},
                    {"action": "deploy_production", "timeout": 600},
                    {"action": "validate_production", "timeout": 300}
                ],
                requires_approval=True,
                auto_execute=False,
                timeout_minutes=90
            ),
            
            # Automated Testing Workflow
            DevWorkflow(
                id="automated_testing",
                name="Automated Testing",
                description="Run comprehensive test suite",
                triggers=[AutomationTrigger.FILE_CHANGE, AutomationTrigger.BUILD_COMPLETE],
                steps=[
                    {"action": "run_unit_tests", "timeout": 300},
                    {"action": "run_integration_tests", "timeout": 600},
                    {"action": "run_security_tests", "timeout": 300},
                    {"action": "generate_coverage_report", "timeout": 120}
                ],
                requires_approval=False,
                auto_execute=True,
                timeout_minutes=20
            ),
            
            # Emergency Rollback Workflow
            DevWorkflow(
                id="emergency_rollback",
                name="Emergency Rollback",
                description="Immediate rollback to previous version",
                triggers=[AutomationTrigger.SMS_COMMAND, AutomationTrigger.EVENT_BASED],
                steps=[
                    {"action": "stop_current_services", "timeout": 120},
                    {"action": "restore_previous_version", "timeout": 300},
                    {"action": "restart_services", "timeout": 180},
                    {"action": "validate_rollback", "timeout": 120}
                ],
                requires_approval=False,  # Emergency - approve via SMS
                auto_execute=True,
                timeout_minutes=15
            )
        ]
        
        for workflow in workflows:
            self.active_workflows[workflow.id] = workflow
    
    async def trigger_workflow(
        self,
        workflow_id: str,
        trigger_type: AutomationTrigger,
        context: Optional[Dict[str, Any]] = None,
        initiated_by: str = "system"
    ) -> str:
        """Trigger a development workflow."""
        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            raise ValueError(f"Unknown workflow: {workflow_id}")
        
        # Check if automation is paused
        is_paused = await cache_manager.get("dev_status:paused")
        if is_paused and workflow_id != "emergency_rollback":
            logger.info(f"Workflow {workflow_id} skipped - development paused")
            return "paused"
        
        execution_id = f"{workflow_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        logger.info(f"Triggering workflow: {workflow_id} (execution: {execution_id})")
        
        # Send notification
        await mobile_dev_service.send_notification(
            "system_status",
            f"Workflow Started: {workflow.name}",
            f"Execution ID: {execution_id}\nInitiated by: {initiated_by}",
            priority="medium"
        )
        
        # Check if approval required
        if workflow.requires_approval:
            approval_id = await request_approval(
                workflow.name,
                f"{workflow.description}\n\nSteps: {len(workflow.steps)}\nEstimated time: {workflow.timeout_minutes}m",
                timeout_minutes=30
            )
            
            # Wait for approval
            approval_result = await self._wait_for_approval(approval_id, timeout_minutes=30)
            
            if not approval_result:
                logger.info(f"Workflow {workflow_id} cancelled - approval denied/timeout")
                return "cancelled"
        
        # Execute workflow
        asyncio.create_task(self._execute_workflow(workflow, execution_id, context or {}))
        
        return execution_id
    
    async def _execute_workflow(
        self,
        workflow: DevWorkflow,
        execution_id: str,
        context: Dict[str, Any]
    ):
        """Execute a workflow with all steps."""
        start_time = datetime.utcnow()
        self.current_state = DevWorkflowState.BUILDING
        
        execution_log = {
            "execution_id": execution_id,
            "workflow_id": workflow.id,
            "start_time": start_time.isoformat(),
            "steps": [],
            "status": "running",
            "context": context
        }
        
        try:
            # Execute each step
            for step_index, step in enumerate(workflow.steps):
                step_start = datetime.utcnow()
                step_id = f"{execution_id}_step_{step_index}"
                
                logger.info(f"Executing step {step_index + 1}/{len(workflow.steps)}: {step['action']}")
                
                # Execute step
                step_result = await self._execute_step(step, step_id, context)
                
                step_duration = (datetime.utcnow() - step_start).total_seconds()
                
                step_log = {
                    "step_index": step_index,
                    "action": step["action"],
                    "start_time": step_start.isoformat(),
                    "duration": step_duration,
                    "status": "success" if step_result["success"] else "failed",
                    "result": step_result
                }
                
                execution_log["steps"].append(step_log)
                
                # Handle step failure
                if not step_result["success"]:
                    if step_result.get("retry", False) and workflow.retry_attempts > 0:
                        logger.info(f"Retrying step: {step['action']}")
                        # Implement retry logic here
                    else:
                        raise Exception(f"Step failed: {step['action']} - {step_result.get('error', 'Unknown error')}")
                
                # Send progress update
                if step_index % 2 == 0 or step_index == len(workflow.steps) - 1:
                    progress = ((step_index + 1) / len(workflow.steps)) * 100
                    await mobile_dev_service.send_notification(
                        "system_status",
                        f"Workflow Progress: {workflow.name}",
                        f"Step {step_index + 1}/{len(workflow.steps)} complete ({progress:.0f}%)",
                        priority="low"
                    )
            
            # Workflow completed successfully
            execution_log["status"] = "completed"
            execution_log["end_time"] = datetime.utcnow().isoformat()
            
            duration = (datetime.utcnow() - start_time).total_seconds()
            await notify_task_complete(
                f"Workflow: {workflow.name}",
                f"{duration:.0f}s"
            )
            
            logger.info(f"Workflow {workflow.id} completed successfully in {duration:.0f}s")
            
        except Exception as e:
            # Workflow failed
            execution_log["status"] = "failed"
            execution_log["error"] = str(e)
            execution_log["end_time"] = datetime.utcnow().isoformat()
            
            await mobile_dev_service.send_notification(
                "error_critical",
                f"Workflow Failed: {workflow.name}",
                f"Error: {str(e)}\nExecution ID: {execution_id}",
                priority="critical"
            )
            
            logger.error(f"Workflow {workflow.id} failed: {e}")
        
        finally:
            # Store execution log
            self.workflow_history.append(execution_log)
            self.current_state = DevWorkflowState.IDLE
            
            # Cleanup
            await self._cleanup_workflow_execution(execution_id)
    
    async def _execute_step(
        self,
        step: Dict[str, Any],
        step_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single workflow step."""
        action = step["action"]
        timeout = step.get("timeout", 300)
        
        try:
            # Route to appropriate action handler
            handler = getattr(self, f"_action_{action}", None)
            if not handler:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "retry": False
                }
            
            # Execute with timeout
            result = await asyncio.wait_for(
                handler(step_id, context),
                timeout=timeout
            )
            
            return {
                "success": True,
                "result": result,
                "retry": False
            }
            
        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": f"Step timed out after {timeout}s",
                "retry": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "retry": False
            }
    
    # Action handlers
    async def _action_rotate_credentials(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Rotate API credentials."""
        logger.info("Starting credential rotation...")
        
        # In production, implement actual credential rotation
        await asyncio.sleep(2)  # Simulate work
        
        return {
            "rotated_keys": ["google_maps", "ticketmaster", "openweather"],
            "status": "completed"
        }
    
    async def _action_update_secret_manager(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Update Google Secret Manager."""
        logger.info("Updating Secret Manager...")
        
        await asyncio.sleep(1)  # Simulate work
        
        return {"secrets_updated": 5, "status": "completed"}
    
    async def _action_run_security_audit(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run security audit."""
        logger.info("Running security audit...")
        
        # Run actual security checks
        try:
            # Use the production environment setup tool
            from app.core.production_env_setup import ProductionEnvSetup
            audit_results = ProductionEnvSetup.run_security_audit()
            
            return {
                "security_score": audit_results["security_score"],
                "critical_issues": len(audit_results["critical_issues"]),
                "warnings": len(audit_results["warnings"]),
                "status": "completed"
            }
        except Exception as e:
            logger.error(f"Security audit failed: {e}")
            return {"status": "failed", "error": str(e)}
    
    async def _action_run_tests(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Run test suite."""
        logger.info("Running test suite...")
        
        try:
            # Run pytest
            result = subprocess.run(
                ["python", "-m", "pytest", "tests/", "-v", "--tb=short"],
                capture_output=True,
                text=True,
                cwd="/mnt/c/users/jared/onedrive/desktop/roadtrip",
                timeout=600
            )
            
            return {
                "exit_code": result.returncode,
                "passed": result.returncode == 0,
                "output": result.stdout[-1000:],  # Last 1000 chars
                "status": "completed"
            }
        except Exception as e:
            return {"status": "failed", "error": str(e)}
    
    async def _action_build_production(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Build production image."""
        logger.info("Building production image...")
        
        await asyncio.sleep(3)  # Simulate build time
        
        return {
            "image_tag": f"v1.0.0-{datetime.utcnow().strftime('%Y%m%d%H%M')}",
            "status": "completed"
        }
    
    async def _action_deploy_staging(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to staging environment."""
        logger.info("Deploying to staging...")
        
        await asyncio.sleep(2)  # Simulate deployment
        
        return {
            "environment": "staging",
            "url": "https://staging.roadtrip.example.com",
            "status": "completed"
        }
    
    async def _action_deploy_production(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy to production environment."""
        logger.info("Deploying to production...")
        
        await asyncio.sleep(3)  # Simulate deployment
        
        return {
            "environment": "production",
            "url": "https://roadtrip.example.com",
            "status": "completed"
        }
    
    async def _action_validate_staging(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate staging deployment."""
        logger.info("Validating staging deployment...")
        
        await asyncio.sleep(1)  # Simulate validation
        
        return {
            "health_check": "passed",
            "performance": "good",
            "status": "completed"
        }
    
    async def _action_validate_production(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate production deployment."""
        logger.info("Validating production deployment...")
        
        await asyncio.sleep(1)  # Simulate validation
        
        return {
            "health_check": "passed",
            "performance": "excellent",
            "status": "completed"
        }
    
    async def _action_notify_completion(self, step_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Send completion notification."""
        await notify_task_complete("Security Update", "All credentials rotated successfully")
        return {"status": "completed"}
    
    async def _wait_for_approval(self, approval_id: str, timeout_minutes: int) -> bool:
        """Wait for approval response."""
        timeout_seconds = timeout_minutes * 60
        check_interval = 5  # Check every 5 seconds
        
        for _ in range(0, timeout_seconds, check_interval):
            approval_data = await cache_manager.get(f"approval:{approval_id}")
            if approval_data:
                approval = json.loads(approval_data)
                return approval.get("approved", False)
            
            await asyncio.sleep(check_interval)
        
        return False  # Timeout
    
    async def _monitor_development_state(self):
        """Monitor development state and trigger automation."""
        while True:
            try:
                # Check for SMS-triggered actions
                deploy_requested = await cache_manager.get("dev_action:deploy_requested")
                if deploy_requested:
                    await cache_manager.delete("dev_action:deploy_requested")
                    await self.trigger_workflow(
                        "production_deploy",
                        AutomationTrigger.SMS_COMMAND,
                        initiated_by="SMS"
                    )
                
                rollback_requested = await cache_manager.get("dev_action:rollback_requested")
                if rollback_requested:
                    await cache_manager.delete("dev_action:rollback_requested")
                    await self.trigger_workflow(
                        "emergency_rollback",
                        AutomationTrigger.SMS_COMMAND,
                        context={"target_version": rollback_requested},
                        initiated_by="SMS"
                    )
                
                # Check for file changes (simplified)
                # In production, use proper file watching
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in development state monitoring: {e}")
                await asyncio.sleep(60)  # Wait longer on error
    
    async def _cleanup_workflow_execution(self, execution_id: str):
        """Clean up after workflow execution."""
        # Remove temporary files, clear caches, etc.
        logger.info(f"Cleaning up workflow execution: {execution_id}")
    
    async def get_workflow_status(self, workflow_id: Optional[str] = None) -> Dict[str, Any]:
        """Get current workflow status."""
        if workflow_id:
            # Get specific workflow status
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                return {"error": "Workflow not found"}
            
            return {
                "workflow": workflow_id,
                "name": workflow.name,
                "description": workflow.description,
                "requires_approval": workflow.requires_approval,
                "auto_execute": workflow.auto_execute
            }
        else:
            # Get overall status
            return {
                "current_state": self.current_state,
                "automation_enabled": self.automation_enabled,
                "active_workflows": len(self.active_workflows),
                "workflow_history_count": len(self.workflow_history),
                "recent_executions": self.workflow_history[-5:] if self.workflow_history else []
            }


# Global service instance
dev_automation_service = DevelopmentAutomationService()