"""
backend/agents/processor_agent/__init__.py

Processor Agent Package.
Exposes the authoritative run_processor_workflow entrypoint for multi-agent procurement.
"""

from .workflow import run_processor_workflow

__all__ = ["run_processor_workflow"]
