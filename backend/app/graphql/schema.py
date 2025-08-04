"""
Main GraphQL schema definition.
"""

import strawberry
from strawberry.extensions import Extension
from strawberry.extensions.tracing import OpenTelemetryExtension
from typing import Any, Dict

from app.graphql.resolvers import Query, Mutation, Subscription
from app.core.logger import get_logger

logger = get_logger(__name__)


class LoggingExtension(Extension):
    """Custom extension for logging GraphQL operations."""
    
    def on_operation_start(self):
        operation_name = self.execution_context.operation_name
        logger.info(f"GraphQL operation started: {operation_name}")
    
    def on_operation_end(self):
        operation_name = self.execution_context.operation_name
        logger.info(f"GraphQL operation completed: {operation_name}")
    
    def on_request_start(self):
        logger.debug("GraphQL request started")
    
    def on_request_end(self):
        logger.debug("GraphQL request completed")
    
    def on_validation_start(self):
        logger.debug("GraphQL validation started")
    
    def on_validation_end(self):
        logger.debug("GraphQL validation completed")
    
    def on_parse_start(self):
        logger.debug("GraphQL parsing started")
    
    def on_parse_end(self):
        logger.debug("GraphQL parsing completed")


class PerformanceExtension(Extension):
    """Extension for tracking GraphQL performance metrics."""
    
    def __init__(self):
        self.start_times: Dict[str, float] = {}
    
    def on_operation_start(self):
        import time
        operation_name = self.execution_context.operation_name or "anonymous"
        self.start_times[operation_name] = time.time()
    
    def on_operation_end(self):
        import time
        operation_name = self.execution_context.operation_name or "anonymous"
        
        if operation_name in self.start_times:
            duration = (time.time() - self.start_times[operation_name]) * 1000
            logger.info(f"GraphQL operation '{operation_name}' took {duration:.2f}ms")
            
            # In production, this would send metrics to monitoring system
            # metrics.record_graphql_operation(operation_name, duration)


# Create the schema with all extensions
schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    subscription=Subscription,
    extensions=[
        LoggingExtension,
        PerformanceExtension,
        OpenTelemetryExtension,  # For distributed tracing
    ]
)

# Export schema for GraphQL Playground/Apollo Studio
def get_schema_str() -> str:
    """Get the schema as a string for documentation."""
    return str(schema)