"""
tests/test_workflow_modes_matrix.py

Comprehensive Validation of Workflow Modes & Full Supply Chain Branch Matrix.
Strictly addresses Audit Gaps #10 and #11:
1. Tests all 4 Single-Agent Modular Workflow Modes:
   - BUYER_ONLY
   - TRANSPORT_ONLY
   - WAREHOUSE_ONLY
   - PROCESSOR_ONLY
2. Tests Full Supply Chain Matrix of All 6 Resource Combinations:
   - [Own Transport, No Warehouse, No Processor]
   - [3rd-party Transport, No Warehouse, No Processor]
   - [3rd-party Transport, Warehouse, No Processor]
   - [3rd-party Transport, No Warehouse, Processor]
   - [3rd-party Transport, Warehouse, Processor]
   - [Own Transport, Warehouse, Processor]
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.agents.graph_orchestrator import dynamic_routing_node, NegotiationState
from backend.core.constants import WorkflowMode, get_allowed_agents

@pytest.fixture
def base_state() -> NegotiationState:
    return {
        "listing_id": "matrix_test_001",
        "crop": "Onion",
        "quantity": 1000.0,
        "base_price": 20.0,
        "min_price": 18.0,
        "market_price": 22.0,
        "spoilage_days": 10,
        "location": "Nashik",
        "current_round": 1,
        "max_rounds": 3,
        "status": "DEAL",
        "farmer_id": "farmer_01",
        "deal": {"price": 23.50, "quantity": 1000.0, "status": "DEAL"},
        "selected_buyer": {"id": "b_pune", "name": "Pune Wholesaler", "location": "Pune"},
        "logs": [],
        "permitted_agents": ["dynamic_routing_agent"],
    }

# ==============================================================================
# SECTION 1: Single-Agent Scope Mode Enforcement (#10)
# ==============================================================================

@pytest.mark.asyncio
async def test_scope_buyer_only(base_state):
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.BUYER_ONLY
    state["permitted_agents"] = ["buyer_agent"]
    
    result = await dynamic_routing_node(state)
    deal = result["deal"]
    assert "transport_plan" not in deal, "BUYER_ONLY must not initiate transport"
    assert "warehouse_option" not in deal, "BUYER_ONLY must not initiate warehouse"
    assert "processor_option" not in deal, "BUYER_ONLY must not initiate processor"
    assert any("Scope is BUYER_ONLY" in log for log in result["logs"])

@pytest.mark.asyncio
async def test_scope_transport_only(base_state):
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.TRANSPORT_ONLY
    state["has_transport"] = True  # Farmer self-transport
    
    result = await dynamic_routing_node(state)
    deal = result["deal"]
    assert "transport_plan" in deal, "TRANSPORT_ONLY must evaluate transport"
    assert deal["transport_plan"]["type"] == "SELF_TRANSPORT"
    assert "warehouse_option" not in deal, "TRANSPORT_ONLY must skip warehouse"
    assert "processor_option" not in deal, "TRANSPORT_ONLY must skip processor"

@pytest.mark.asyncio
async def test_scope_warehouse_only(base_state):
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.WAREHOUSE_ONLY
    state["has_storage"] = False
    state["requires_storage"] = True
    
    # Mock warehouse bids
    mock_bid = {"name": "Nashik Cold Hub", "bid": 1.5, "score": 10.0, "reason": "Close to farm"}
    with patch("backend.agents.stakeholders.warehouse_agent.WarehouseAgent.generate_bid", return_value=mock_bid):
        result = await dynamic_routing_node(state)
        deal = result["deal"]
        assert "warehouse_option" in deal, "WAREHOUSE_ONLY must evaluate warehouse when requested"
        assert "transport_plan" not in deal, "WAREHOUSE_ONLY must skip transport"
        assert "processor_option" not in deal, "WAREHOUSE_ONLY must skip processor"

@pytest.mark.asyncio
async def test_scope_processor_only(base_state):
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.PROCESSOR_ONLY
    state["requires_processing"] = True
    
    mock_pbid = {"name": "Dehydration Corp", "salvage_bid": 15.0, "reason": "Grade B onion processing"}
    with patch("backend.agents.stakeholders.processor_agent.ProcessorAgent.generate_salvage_bid", return_value=mock_pbid):
        result = await dynamic_routing_node(state)
        deal = result["deal"]
        assert "processor_option" in deal, "PROCESSOR_ONLY must evaluate processor when requested"
        assert "transport_plan" not in deal, "PROCESSOR_ONLY must skip transport"
        assert "warehouse_option" not in deal, "PROCESSOR_ONLY must skip warehouse"

# ==============================================================================
# SECTION 2: Full Supply Chain 6-Branch Matrix (#11)
# ==============================================================================

@pytest.mark.asyncio
async def test_full_matrix_branch_1_own_transport_no_wh_no_proc(base_state):
    # Branch 1: Own transport, no storage needed, no processing
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.FULL_SUPPLY_CHAIN
    state["has_transport"] = True
    state["has_storage"] = True
    state["requires_storage"] = False
    state["spoilage_days"] = 15
    state["requires_processing"] = False
    
    result = await dynamic_routing_node(state)
    deal = result["deal"]
    assert deal["transport_plan"]["type"] == "SELF_TRANSPORT"
    assert "warehouse_option" not in deal
    assert "processor_option" not in deal

@pytest.mark.asyncio
async def test_full_matrix_branch_2_third_party_transport_no_wh_no_proc(base_state):
    # Branch 2: 3rd party transport, no storage, no processor
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.FULL_SUPPLY_CHAIN
    state["has_transport"] = False
    state["has_storage"] = True
    state["requires_storage"] = False
    state["spoilage_days"] = 15
    state["requires_processing"] = False
    
    mock_transport_plan = {
        "status": "CONFIRMED",
        "vehicle_name": "Tata 407",
        "vehicle_type": "Truck",
        "pickup_location": "Nashik",
        "delivery_location": "Pune",
        "distance_km": 210.0,
        "agreed_price": 3500.0,
    }
    with patch("backend.agents.transport_agent.graph.run_transport_workflow", return_value={"status": "CONFIRMED", "final_transport_plan": mock_transport_plan}):
        result = await dynamic_routing_node(state)
        deal = result["deal"]
        assert deal["transport_plan"]["agreed_price"] == 3500.0
        assert "warehouse_option" not in deal
        assert "processor_option" not in deal

@pytest.mark.asyncio
async def test_full_matrix_branch_3_third_party_transport_with_wh_no_proc(base_state):
    # Branch 3: 3rd party transport, warehouse needed, no processor
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.FULL_SUPPLY_CHAIN
    state["has_transport"] = False
    state["has_storage"] = False
    state["requires_storage"] = True
    state["requires_processing"] = False
    
    mock_transport_plan = {"status": "CONFIRMED", "agreed_price": 3500.0, "vehicle_name": "Eicher Pro"}
    mock_warehouse_bid = {"name": "Nashik Agri Cold Storage", "bid": 1.2, "score": 5.0, "reason": "Optimal RH"}
    
    with patch("backend.agents.transport_agent.graph.run_transport_workflow", return_value={"status": "CONFIRMED", "final_transport_plan": mock_transport_plan}), \
         patch("backend.agents.stakeholders.warehouse_agent.WarehouseAgent.generate_bid", return_value=mock_warehouse_bid):
        
        result = await dynamic_routing_node(state)
        deal = result["deal"]
        assert deal["transport_plan"]["agreed_price"] == 3500.0
        assert deal["warehouse_option"]["name"] == "Nashik Agri Cold Storage"
        assert "processor_option" not in deal

@pytest.mark.asyncio
async def test_full_matrix_branch_4_third_party_transport_no_wh_with_proc(base_state):
    # Branch 4: 3rd party transport, no warehouse, processor needed
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.FULL_SUPPLY_CHAIN
    state["has_transport"] = False
    state["has_storage"] = True
    state["requires_storage"] = False
    state["spoilage_days"] = 14
    state["requires_processing"] = True
    
    mock_transport_plan = {"status": "CONFIRMED", "agreed_price": 2800.0}
    mock_pbid = {"name": "MahaPure Processing", "salvage_bid": 16.5, "reason": "Bulk paste conversion"}
    
    with patch("backend.agents.transport_agent.graph.run_transport_workflow", return_value={"status": "CONFIRMED", "final_transport_plan": mock_transport_plan}), \
         patch("backend.agents.stakeholders.processor_agent.ProcessorAgent.generate_salvage_bid", return_value=mock_pbid):
        
        result = await dynamic_routing_node(state)
        deal = result["deal"]
        assert deal["transport_plan"]["agreed_price"] == 2800.0
        assert "warehouse_option" not in deal
        assert deal["processor_option"]["name"] == "MahaPure Processing"

@pytest.mark.asyncio
async def test_full_matrix_branch_5_third_party_transport_with_wh_and_proc(base_state):
    # Branch 5: 3rd party transport, warehouse needed, processor needed
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.FULL_SUPPLY_CHAIN
    state["has_transport"] = False
    state["has_storage"] = False
    state["requires_storage"] = True
    state["requires_processing"] = True
    
    mock_transport_plan = {"status": "CONFIRMED", "agreed_price": 4000.0}
    mock_wbid = {"name": "Central Hub Cold Storage", "bid": 1.1, "score": 3.0, "reason": "Pre-cooling available"}
    mock_pbid = {"name": "AgroTech Processors", "salvage_bid": 17.0, "reason": "High capacity"}
    
    with patch("backend.agents.transport_agent.graph.run_transport_workflow", return_value={"status": "CONFIRMED", "final_transport_plan": mock_transport_plan}), \
         patch("backend.agents.stakeholders.warehouse_agent.WarehouseAgent.generate_bid", return_value=mock_wbid), \
         patch("backend.agents.stakeholders.processor_agent.ProcessorAgent.generate_salvage_bid", return_value=mock_pbid):
        
        result = await dynamic_routing_node(state)
        deal = result["deal"]
        assert deal["transport_plan"]["agreed_price"] == 4000.0
        assert deal["warehouse_option"]["name"] == "Central Hub Cold Storage"
        assert deal["processor_option"]["name"] == "AgroTech Processors"

@pytest.mark.asyncio
async def test_full_matrix_branch_6_own_transport_with_wh_and_proc(base_state):
    # Branch 6: Own transport, warehouse needed, processor needed
    state = dict(base_state)
    state["workflow_mode"] = WorkflowMode.FULL_SUPPLY_CHAIN
    state["has_transport"] = True
    state["has_storage"] = False
    state["requires_storage"] = True
    state["requires_processing"] = True
    
    mock_wbid = {"name": "Local APMC Warehouse", "bid": 0.8, "score": 2.0, "reason": "Subsidized"}
    mock_pbid = {"name": "Kisan Processors", "salvage_bid": 18.0, "reason": "Certified Organic"}
    
    with patch("backend.agents.stakeholders.warehouse_agent.WarehouseAgent.generate_bid", return_value=mock_wbid), \
         patch("backend.agents.stakeholders.processor_agent.ProcessorAgent.generate_salvage_bid", return_value=mock_pbid):
        
        result = await dynamic_routing_node(state)
        deal = result["deal"]
        assert deal["transport_plan"]["type"] == "SELF_TRANSPORT"
        assert deal["warehouse_option"]["name"] == "Local APMC Warehouse"
        assert deal["processor_option"]["name"] == "Kisan Processors"
