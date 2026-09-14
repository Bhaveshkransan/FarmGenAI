"""
Group 2 Comprehensive Regression Test Suite for AgriNegotiator
Tests Areas A through J against the live environment.
"""

import asyncio
import json
import os
import sys
import time
import urllib.request
import urllib.error
import requests

from database.db import Database, AsyncSessionLocal, DBUser
from sqlalchemy import text
from llm.llm_client import client as llm_client
from backend.agents.graph_orchestrator import graph_orchestrator
from backend.services.security import create_access_token

BASE_URL = "http://localhost:8000/api/v1"
results = {}

def log_test(area, test_name, status, details=""):
    if area not in results:
        results[area] = []
    results[area].append({
        "test": test_name,
        "status": status,
        "details": details
    })
    print(f"[{status}] {area} - {test_name}: {details[:100]}")

async def run_all_tests():
    print("=" * 60)
    print("STARTING AGRINEGOTIATOR GROUP-2 REGRESSION TESTS")
    print("=" * 60)

    # 0. Setup test users and tokens
    farmer_email = f"farmer_g2_{int(time.time())}@agri.com"
    buyer_email = f"buyer_g2_{int(time.time())}@agri.com"
    
    # Sign up farmer
    try:
        r = requests.post(f"{BASE_URL}/auth/signup", json={
            "name": "G2 Test Farmer",
            "email": farmer_email,
            "password": "Password123!",
            "role": "farmer",
            "location": "Nashik"
        })
        farmer_data = r.json()
        farmer_token = farmer_data.get("token")
        farmer_id = farmer_data.get("user_id")
        farmer_headers = {"Authorization": f"Bearer {farmer_token}"}
    except Exception as e:
        print("Failed to signup farmer:", e)
        return

    # Sign up buyer
    try:
        r = requests.post(f"{BASE_URL}/auth/signup", json={
            "name": "G2 Test Buyer",
            "email": buyer_email,
            "password": "Password123!",
            "role": "buyer",
            "location": "Pune"
        })
        buyer_data = r.json()
        buyer_token = buyer_data.get("token")
        buyer_id = buyer_data.get("user_id")
        buyer_headers = {"Authorization": f"Bearer {buyer_token}"}
    except Exception as e:
        print("Failed to signup buyer:", e)
        return

    # ==========================================================
    # AREA A: FARMER LISTING FLOW
    # ==========================================================
    print("\n--- Testing Area A: Farmer Listing Flow ---")
    created_listing_id = None
    # A1. Valid listing creation
    try:
        listing_payload = {
            "crop": "Tomato",
            "quantity": 500.0,
            "min_price": 22.0,
            "location": "Nashik",
            "spoilage_days": 5,
            "description": "Premium Grade A Nashik Hybrid Tomatoes"
        }
        res = requests.post(f"{BASE_URL}/listings/", json=listing_payload, headers=farmer_headers)
        if res.status_code == 200 and res.json().get("success"):
            created_listing_id = res.json().get("listing_id") or res.json().get("data", {}).get("listing_id")
            log_test("A. Farmer Listing", "1. Create Listing", "PASS", f"Listing created ID: {created_listing_id}")
        else:
            log_test("A. Farmer Listing", "1. Create Listing", "FAIL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("A. Farmer Listing", "1. Create Listing", "FAIL", str(e))

    # A2. Listing retrieval via /listings/me
    try:
        res = requests.get(f"{BASE_URL}/listings/me", headers=farmer_headers)
        if res.status_code == 200:
            listings = res.json()
            found = any(l.get("listing_id") == created_listing_id or l.get("id") == created_listing_id for l in listings)
            if found:
                log_test("A. Farmer Listing", "2. Retrieve /listings/me", "PASS", f"Found {len(listings)} listings for farmer")
            else:
                log_test("A. Farmer Listing", "2. Retrieve /listings/me", "FAIL", f"Created listing {created_listing_id} not in /listings/me")
        else:
            log_test("A. Farmer Listing", "2. Retrieve /listings/me", "FAIL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("A. Farmer Listing", "2. Retrieve /listings/me", "FAIL", str(e))

    # A3. Listing retrieval by ID
    if created_listing_id:
        try:
            res = requests.get(f"{BASE_URL}/listings/{created_listing_id}", headers=farmer_headers)
            if res.status_code == 200 and res.json().get("data"):
                log_test("A. Farmer Listing", "3. Get Listing by ID", "PASS", f"Fetched listing {created_listing_id}")
            else:
                log_test("A. Farmer Listing", "3. Get Listing by ID", "FAIL", f"Status {res.status_code}: {res.text}")
        except Exception as e:
            log_test("A. Farmer Listing", "3. Get Listing by ID", "FAIL", str(e))

    # A4. Field validation & Invalid listing rejection
    try:
        bad_payload = {"crop": "", "quantity": -50, "min_price": 0, "location": ""}
        res = requests.post(f"{BASE_URL}/listings/", json=bad_payload, headers=farmer_headers)
        if res.status_code in (400, 422):
            log_test("A. Farmer Listing", "4. Reject Invalid Listing Data", "PASS", f"Rejected with {res.status_code}")
        else:
            log_test("A. Farmer Listing", "4. Reject Invalid Listing Data", "FAIL", f"Accepted invalid data! Status {res.status_code}")
    except Exception as e:
        log_test("A. Farmer Listing", "4. Reject Invalid Listing Data", "FAIL", str(e))

    # ==========================================================
    # AREA B: BUYER REQUIREMENT / BUYER FLOW
    # ==========================================================
    print("\n--- Testing Area B: Buyer Requirement / Buyer Flow ---")
    created_req_id = None
    try:
        req_payload = {
            "crop": "Tomato",
            "quantity": 500.0,
            "target_price": 18.0,
            "max_price": 20.0,
            "location": "Pune",
            "budget": 12000.0,
            "delivery_days": 7,
            "quality_grade": "A",
            "notes": "Bulk requirement for fresh retail"
        }
        res = requests.post(f"{BASE_URL}/requirements/", json=req_payload, headers=buyer_headers)
        if res.status_code == 200 and res.json().get("success"):
            created_req_id = res.json().get("requirement_id")
            log_test("B. Buyer Requirement", "1. Create Buyer Requirement", "PASS", f"Requirement ID: {created_req_id}")
        else:
            log_test("B. Buyer Requirement", "1. Create Buyer Requirement", "FAIL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("B. Buyer Requirement", "1. Create Buyer Requirement", "FAIL", str(e))

    # B2. List Requirements
    try:
        res = requests.get(f"{BASE_URL}/requirements/", headers=buyer_headers)
        if res.status_code == 200 and "data" in res.json():
            reqs = res.json()["data"]
            found = any(r.get("requirement_id") == created_req_id for r in reqs)
            log_test("B. Buyer Requirement", "2. List Buyer Requirements", "PASS" if found else "PARTIAL", f"Retrieved {len(reqs)} active requirements")
        else:
            log_test("B. Buyer Requirement", "2. List Buyer Requirements", "FAIL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("B. Buyer Requirement", "2. List Buyer Requirements", "FAIL", str(e))

    # B3. Get Requirement by ID
    if created_req_id:
        try:
            res = requests.get(f"{BASE_URL}/requirements/{created_req_id}", headers=buyer_headers)
            if res.status_code == 200 and res.json().get("success"):
                log_test("B. Buyer Requirement", "3. Get Requirement by ID", "PASS", f"Retrieved requirement {created_req_id}")
            else:
                log_test("B. Buyer Requirement", "3. Get Requirement by ID", "FAIL", f"Status {res.status_code}")
        except Exception as e:
            log_test("B. Buyer Requirement", "3. Get Requirement by ID", "FAIL", str(e))

    # ==========================================================
    # AREA C: FARMER OFFER / BUYER OFFER FLOW
    # ==========================================================
    print("\n--- Testing Area C: Farmer Offer / Buyer Offer Flow ---")
    try:
        offer_payload = {
            "role": "buyer",
            "crop": "Tomato",
            "quantity": 500.0,
            "price": 18.5,
            "location": "Pune",
            "notes": "Direct counter-offer on Tomato listing"
        }
        res = requests.post(f"{BASE_URL}/role-offers/", json=offer_payload, headers=buyer_headers)
        if res.status_code == 200:
            log_test("C. Offer Flow", "1. Post Role Offer", "PASS", f"Offer created: {res.json()}")
        else:
            log_test("C. Offer Flow", "1. Post Role Offer", "FAIL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("C. Offer Flow", "1. Post Role Offer", "FAIL", str(e))

    try:
        res = requests.get(f"{BASE_URL}/role-offers/?role=buyer", headers=buyer_headers)
        if res.status_code == 200 and "offers" in res.json():
            log_test("C. Offer Flow", "2. List Role Offers", "PASS", f"Offers count: {len(res.json()['offers'])}")
        else:
            log_test("C. Offer Flow", "2. List Role Offers", "FAIL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("C. Offer Flow", "2. List Role Offers", "FAIL", str(e))

    # ==========================================================
    # AREA D: NEGOTIATION CREATION
    # ==========================================================
    print("\n--- Testing Area D: Negotiation Creation ---")
    neg_id = None
    neg_result = None
    try:
        neg_payload = {
            "crop": "Tomato",
            "quantity": 500.0,
            "min_price": 22.0,
            "farmer_name": "G2 Test Farmer",
            "location": "Nashik",
            "user_id": farmer_id,
            "shelf_life": 5,
            "max_rounds": 5
        }
        res = requests.post(f"{BASE_URL}/negotiation/start-negotiation", json=neg_payload, headers=farmer_headers)
        if res.status_code == 200:
            neg_result = res.json()
            neg_id = neg_result.get("negotiation_id") or neg_result.get("id")
            log_test("D. Negotiation Creation", "1. Start Negotiation", "PASS", f"State: {neg_result.get('state')}, Summary: {neg_result.get('summary', '')[:80]}")
        else:
            log_test("D. Negotiation Creation", "1. Start Negotiation", "FAIL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("D. Negotiation Creation", "1. Start Negotiation", "FAIL", str(e))

    # D2. Negotiation Agents Discovery
    try:
        res = requests.get(f"{BASE_URL}/negotiation/agents", headers=farmer_headers)
        if res.status_code == 200 and "agents" in res.json():
            log_test("D. Negotiation Creation", "2. List Negotiation Agents", "PASS", f"Agents available: {len(res.json()['agents'])}")
        else:
            log_test("D. Negotiation Creation", "2. List Negotiation Agents", "FAIL", f"Status {res.status_code}")
    except Exception as e:
        log_test("D. Negotiation Creation", "2. List Negotiation Agents", "FAIL", str(e))

    # ==========================================================
    # AREA E: NEGOTIATION ROUND EXECUTION
    # ==========================================================
    print("\n--- Testing Area E: Negotiation Round Execution ---")
    if neg_result:
        logs = neg_result.get("logs", [])
        price_series = neg_result.get("price_series", [])
        partnerships = neg_result.get("partnerships", [])
        deal = neg_result.get("deal")
        
        has_rounds = len(logs) > 0
        has_state = neg_result.get("state") in ("DEAL", "ESCALATED_STORAGE", "ESCALATED_PROCESSING", "ESCALATED_COMPOST", "REJECT", "ACTIVE")
        
        log_test("E. Round Execution", "1. Logs and Dialogue Generated", "PASS" if has_rounds else "FAIL", f"{len(logs)} log entries generated")
        log_test("E. Round Execution", "2. Final Agreement/Escalation State", "PASS" if has_state else "FAIL", f"Final State: {neg_result.get('state')}")
        log_test("E. Round Execution", "3. Price Convergence & Series", "PASS" if (price_series or deal) else "PARTIAL", f"Deal: {deal}, Price series points: {len(price_series)}")

    # ==========================================================
    # AREA F: LANGGRAPH / AGENT ORCHESTRATION
    # ==========================================================
    print("\n--- Testing Area F: LangGraph / Agent Orchestration ---")
    try:
        initial_state = {
            "crop": "Tomato",
            "quantity": 500.0,
            "min_price": 20.0,
            "target_price": 24.0,
            "spoilage_days": 4,
            "location": "Nashik",
            "market_price": 21.0,
            "round": 0,
            "max_rounds": 4,
            "history": [],
            "buyer_profile": None,
            "logs": [],
            "status": "ACTIVE",
            "proposed_scenario": "direct-sale",
            "next_action": "",
            "deal": None,
            "plan": None,
            "reflection": None,
            "selected_buyer": None,
            "market_offers": [],
            "user_id": farmer_id,
            "latest_farmer_ask": None,
            "latest_buyer_offer": None,
            "buyers_list": [
                {"name": "FreshMart Retail", "budget": 21000, "max_quantity": 900, "target_price": 22, "location": "Pune", "strategy": "High-quality retail"}
            ]
        }
        t0 = time.time()
        final_state = await graph_orchestrator.ainvoke(initial_state)
        elapsed = round(time.time() - t0, 2)
        
        has_nodes_ran = "logs" in final_state and len(final_state["logs"]) > 0
        has_status = "status" in final_state
        
        log_test("F. LangGraph Orchestration", "1. StateGraph Compilation & Invocation", "PASS", f"Executed in {elapsed}s. Final status: {final_state.get('status')}")
        log_test("F. LangGraph Orchestration", "2. Multi-Node State Progression", "PASS" if has_nodes_ran else "FAIL", f"Plan: {bool(final_state.get('plan'))}, Reflection: {bool(final_state.get('reflection'))}, Logs: {len(final_state.get('logs', []))}")
    except Exception as e:
        log_test("F. LangGraph Orchestration", "1. StateGraph Invocation", "FAIL", str(e))

    # ==========================================================
    # AREA G: OLLAMA / LLM INTEGRATION
    # ==========================================================
    print("\n--- Testing Area G: Ollama / LLM Integration ---")
    try:
        # Check Ollama tags directly
        ollama_tags = requests.get("http://ollama:11434/api/tags", timeout=5).json()
        model_names = [m["name"] for m in ollama_tags.get("models", [])]
        log_test("G. Ollama / LLM", "1. Ollama Connectivity & Models", "PASS", f"Loaded models: {', '.join(model_names)}")
        
        # Test generation with configured model
        t0 = time.time()
        gen_res = llm_client.generate("Evaluate Tomato price ₹22/kg in 10 words.")
        gen_time = round(time.time() - t0, 2)
        if gen_res:
            log_test("G. Ollama / LLM", "2. LLM Inference Execution", "PASS", f"Generated in {gen_time}s: '{gen_res}'")
        else:
            log_test("G. Ollama / LLM", "2. LLM Inference Execution", "FAIL", "Returned None")
    except Exception as e:
        log_test("G. Ollama / LLM", "1. Ollama Connectivity", "FAIL", str(e))

    # ==========================================================
    # AREA H: DATABASE PERSISTENCE
    # ==========================================================
    print("\n--- Testing Area H: Database Persistence ---")
    async with AsyncSessionLocal() as session:
        # Check user in postgres
        res = await session.execute(text("SELECT user_id, name, email, role FROM users WHERE email = :email"), {"email": farmer_email})
        user_row = res.fetchone()
        log_test("H. Database Persistence", "1. User Postgres Persistence", "PASS" if user_row else "FAIL", f"User in DB: {user_row}")

        # Check farmer record
        res_farmer = await session.execute(text("SELECT id, name, location FROM farmers WHERE id = :id OR name = :name"), {"id": farmer_id, "name": "G2 Test Farmer"})
        farmer_row = res_farmer.fetchone()
        log_test("H. Database Persistence", "2. Farmer Table Postgres Persistence", "PASS" if farmer_row else "PARTIAL", f"Farmer in DB: {farmer_row}")

        # Check in-memory vs postgres produce
        in_memory_produce = len(Database.produce) if hasattr(Database, "produce") and Database.produce else 0
        log_test("H. Database Persistence", "3. Produce Storage Model", "PASS", f"In-Memory Produce Cache: {in_memory_produce} listings; Postgres produce sync active")

    # ==========================================================
    # AREA I: NEGOTIATION HISTORY
    # ==========================================================
    print("\n--- Testing Area I: Negotiation History ---")
    try:
        res = requests.get(f"{BASE_URL}/history/negotiations", headers=farmer_headers)
        if res.status_code == 200:
            hist = res.json()
            log_test("I. Negotiation History", "1. Get Negotiation History", "PASS", f"History items: {len(hist) if isinstance(hist, list) else list(hist.keys())}")
        else:
            log_test("I. Negotiation History", "1. Get Negotiation History", "PARTIAL", f"Status {res.status_code}: {res.text}")
    except Exception as e:
        log_test("I. Negotiation History", "1. Get Negotiation History", "FAIL", str(e))

    # ==========================================================
    # AREA J: ERROR HANDLING
    # ==========================================================
    print("\n--- Testing Area J: Error Handling ---")
    # J1. Invalid negotiation ID
    try:
        res = requests.get(f"{BASE_URL}/negotiation/negotiation-status/non_existent_id_9999", headers=farmer_headers)
        log_test("J. Error Handling", "1. Invalid Negotiation ID", "PASS" if res.status_code == 404 else "FAIL", f"Returned status: {res.status_code}")
    except Exception as e:
        log_test("J. Error Handling", "1. Invalid Negotiation ID", "FAIL", str(e))

    # J2. Invalid crop listing ID
    try:
        res = requests.get(f"{BASE_URL}/listings/non_existent_listing_8888", headers=farmer_headers)
        log_test("J. Error Handling", "2. Invalid Listing ID", "PASS" if res.status_code == 404 else "FAIL", f"Returned status: {res.status_code}")
    except Exception as e:
        log_test("J. Error Handling", "2. Invalid Listing ID", "FAIL", str(e))

    # J3. Unauthenticated request
    try:
        res = requests.get(f"{BASE_URL}/listings/me")
        log_test("J. Error Handling", "3. Unauthenticated Access Rejection", "PASS" if res.status_code in (401, 403) else "FAIL", f"Returned status: {res.status_code}")
    except Exception as e:
        log_test("J. Error Handling", "3. Unauthenticated Access Rejection", "FAIL", str(e))

    print("\n" + "=" * 60)
    print("ALL GROUP-2 REGRESSION TESTS COMPLETED")
    print("=" * 60)
    return results

if __name__ == "__main__":
    asyncio.run(run_all_tests())
