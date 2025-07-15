"""
GraphQL API implementation using Strawberry.

This package provides a GraphQL interface for the mobile app with:
- Efficient data fetching (no over/under-fetching)
- Real-time subscriptions for voice interactions
- Type-safe schema definition
- Automatic documentation
"""

from .schema import schema

__all__ = ['schema']