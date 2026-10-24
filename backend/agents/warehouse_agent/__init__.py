"""
backend/agents/warehouse_agent/__init__.py

Warehouse Agent Package.
Exposes the authoritative run_warehouse_workflow entrypoint for multi-agent procurement.
"""

from .workflow import run_warehouse_workflow

__all__ = ["run_warehouse_workflow"]
