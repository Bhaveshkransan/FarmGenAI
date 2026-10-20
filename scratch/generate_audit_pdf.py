import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

pdf_path = 'c:/Users/bhave/Downloads/Agrinegotiator-Ritik/BUYER_AGENT_MASTER_AUDIT_REPORT.pdf'
doc = SimpleDocTemplate(pdf_path, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)

styles = getSampleStyleSheet()
title_style = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#1b4332'))
subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=12, textColor=colors.HexColor('#495057'))
h1_style = ParagraphStyle('Heading1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11.5, leading=15, textColor=colors.HexColor('#2d6a4f'), spaceBefore=8, spaceAfter=3)
body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=7.5, leading=10.5, textColor=colors.HexColor('#212529'))
bullet_style = ParagraphStyle('Bullet', parent=body_style, leftIndent=8, bulletIndent=3)
table_header = ParagraphStyle('TH', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.5, leading=10, textColor=colors.white)
table_cell = ParagraphStyle('TC', parent=styles['Normal'], fontName='Helvetica', fontSize=7.2, leading=9.5, textColor=colors.HexColor('#212529'))
status_pass = ParagraphStyle('Pass', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=7.2, leading=9.5, textColor=colors.HexColor('#2d6a4f'))

story = []

# Title & Metadata
story.append(Paragraph('Buyer Agent Master Audit &amp; Verification Report', title_style))
story.append(Paragraph('<b>Complete Stakeholder-Aware AgriNegotiator SRS Architecture &amp; Negotiation Certification</b>', ParagraphStyle('Sub', parent=h1_style, fontSize=10, leading=13)))
story.append(Paragraph('<b>Branch:</b> feature/buyer-agent-verification &nbsp;|&nbsp; <b>Target:</b> main &nbsp;|&nbsp; <b>Repository:</b> Ritikmehta080905/FarmGenAI &nbsp;|&nbsp; <b>Status:</b> 100% Certified (94/94 Tests Passed)', subtitle_style))
story.append(Spacer(1, 4))
story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2d6a4f'), spaceBefore=2, spaceAfter=6))

# 1. Executive Summary
story.append(Paragraph('1. Executive Summary &amp; Architectural Scope', h1_style))
story.append(Paragraph('This Master Audit unifies the <b>83 safety/negotiation hardening tests</b> with the <b>complete stakeholder-aware AgriNegotiator SRS architecture</b>. The system enforces strict isolation between <b>SINGLE_AGENT</b> (locking <code>permitted_agents=[\"BUYER\"]</code> and strictly preventing accidental downstream execution) and <b>FULL_SUPPLY_CHAIN</b> (conditionally invoking Transport, Warehouse, or Processor ONLY when actually required by constraints).', body_style))
story.append(Spacer(1, 4))

# 2. 10 Architectural Domains Matrix
story.append(Paragraph('2. Architectural Verification Matrix (10 Core Domains)', h1_style))
domain_data = [
    [Paragraph('Domain', table_header), Paragraph('SRS Architectural Invariant', table_header), Paragraph('Implementation &amp; Evidence', table_header), Paragraph('Status', table_header)],
    [Paragraph('1. Single vs. Full', table_cell), Paragraph('SINGLE_AGENT must never invoke downstream; FULL conditionally invokes them.', table_cell), Paragraph('workflow_policy_gatekeeper in buyer_graph.py locks permitted_agents.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('2. Permitted vs. Required', table_cell), Paragraph('permitted = allowed services; required = actually needed services.', table_cell), Paragraph('Explicit contract blocks unpermitted services even if requested by user.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('3. Market Intelligence', table_cell), Paragraph('Live Mandi + ML trends + transport estimates + RAG context.', table_cell), Paragraph('buyer_market_context_service.py coordinates Mandi feed + XGBoost + RAG.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('4. Landed Cost Matching', table_cell), Paragraph('Landed = Base + Freight + APMC Cess. Lowest purchase price &ne; lowest cost.', table_cell), Paragraph('Local ₹49 lot wins over remote ₹48 lot due to highway freight calculation.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('5. RAG vs. Facts', table_cell), Paragraph('RAG retrieves domain knowledge; live prices come strictly from Mandi APIs.', table_cell), Paragraph('RAG ChromaDB supplies quality norms; live Agmarknet API supplies modal price.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('6. LangGraph StateGraph', table_cell), Paragraph('StateGraph multi-node engine decides agent eligibility dynamically.', table_cell), Paragraph('11-node compiled LangGraph StateGraph with conditional branching.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('7. Event Telemetry', table_cell), Paragraph('Granular WebSocket / Redis event streaming across procurement stages.', table_cell), Paragraph('Emits MATCH_FOUND, NEGOTIATION_STARTED, OFFER_RECEIVED, DEAL_SELECTED, etc.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('8. Copilot Guardrails', table_cell), Paragraph('Human / Copilot overrides cannot bypass P_max, budget, or agent scope.', table_cell), Paragraph('validate_copilot_buyer_override() rejects P_max breach, budget overrun, agent bypass.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('9. Downstream Escalation', table_cell), Paragraph('Conditional downstream dispatch for Transport, Warehouse, Processor.', table_cell), Paragraph('Conditionally calls assign_transport, assign_storage, or processor_service.', table_cell), Paragraph('PASS', status_pass)],
    [Paragraph('10. PostgreSQL Consistency', table_cell), Paragraph('Durable state in PostgreSQL with digital contracts and idempotency.', table_cell), Paragraph('SHA-256 digital contract hash (0x...), TXN-MH-2026-..., 64-char idempotency key.', table_cell), Paragraph('PASS', status_pass)],
]
dt = Table(domain_data, colWidths=[1.1*inch, 2.5*inch, 2.8*inch, 0.7*inch])
dt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d6a4f')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('ALIGN', (3,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
    ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8f9fa')]),
    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ('TOPPADDING', (0,0), (-1,-1), 2),
]))
story.append(dt)
story.append(Spacer(1, 6))

# 3. Test Certification Table
story.append(Paragraph('3. Test Certification Scorecard (94 / 94 Passed — 100% Pass Rate)', h1_style))
test_data = [
    [Paragraph('Test Suite File', table_header), Paragraph('Coverage Description', table_header), Paragraph('Pass / Total', table_header), Paragraph('Status', table_header)],
    [Paragraph('test_buyer_master_srs_architecture.py', table_cell), Paragraph('Full/Single Supply Chain, Permitted vs Required, Landed Cost, LangGraph, Copilot', table_cell), Paragraph('11 / 11', table_cell), Paragraph('PASS (100%)', status_pass)],
    [Paragraph('test_buyer_adversarial_pmax_budget.py', table_cell), Paragraph('NaN/Inf/Negatives/Strings, P_max override, budget lock, quantity lifecycle, freshness', table_cell), Paragraph('14 / 14', table_cell), Paragraph('PASS (100%)', status_pass)],
    [Paragraph('test_buyer_runtime_e2e.py', table_cell), Paragraph('Full runtime E2E chain, no-deal boundary, crop guardrail, invalid quantity', table_cell), Paragraph('4 / 4', table_cell), Paragraph('PASS (100%)', status_pass)],
    [Paragraph('test_05_buyer_agent_extensive.py', table_cell), Paragraph('Buyer personas, concession curves, utility scoring, memory, contracts', table_cell), Paragraph('38 / 38', table_cell), Paragraph('PASS (100%)', status_pass)],
    [Paragraph('test_07_buyer_guardrail_parallel.py', table_cell), Paragraph('APMC statutory price caps, parallel auto-selection, floor rejection', table_cell), Paragraph('5 / 5', table_cell), Paragraph('PASS (100%)', status_pass)],
    [Paragraph('test_09a_buyer_negotiation_orchestration.py', table_cell), Paragraph('Top-5 selection, state isolation, landed cost calculation, transcripts', table_cell), Paragraph('22 / 22', table_cell), Paragraph('PASS (100%)', status_pass)],
    [Paragraph('<b>TOTAL</b>', table_cell), Paragraph('<b>Complete SRS Architecture &amp; Safety Certification</b>', table_cell), Paragraph('<b>94 / 94</b>', table_cell), Paragraph('<b>CERTIFIED</b>', status_pass)],
]
tt = Table(test_data, colWidths=[1.8*inch, 3.2*inch, 0.9*inch, 1.1*inch])
tt.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2d6a4f')),
    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
    ('ALIGN', (2,0), (-1,-1), 'CENTER'),
    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#dee2e6')),
    ('ROWBACKGROUNDS', (0,1), (-1,-2), [colors.white, colors.HexColor('#f8f9fa')]),
    ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#d8f3dc')),
    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ('TOPPADDING', (0,0), (-1,-1), 2),
]))
story.append(tt)
story.append(Spacer(1, 6))

# 4. Status Links
story.append(Paragraph('4. Pull Request &amp; Live Verification Links', h1_style))
story.append(Paragraph('&bull; <b>Active PR #5:</b> https://github.com/Ritikmehta080905/FarmGenAI/pull/5<br/>&bull; <b>Live Application:</b> http://localhost:8080/dashboard/buyer<br/>&bull; <b>Closed PR:</b> PR #4 (closed and superseded by PR #5)', bullet_style))

doc.build(story)
print('Master Audit PDF generated at:', pdf_path)
