"""
Core package — LLM client, budgets, resilience, usage, types, exceptions.

Dependency rule (ADR-001): core depends on NO internal package, only
third-party. Everything else may depend on core.
"""

__version__ = "2.0.0"
