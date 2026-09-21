"""
Script to generate BUYER_AGENT_CURRENT_STATE_AUDIT.pdf using ReportLab.
Covers all 14 required audit sections factually with verified evidence from the repository.
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 11 * 72 - 36, "AGRINEGOTIATOR — BUYER AGENT CURRENT STATE & REAL DATA AUDIT")
            self.drawRightString(8.5 * 72 - 54, 11 * 72 - 36, "BRANCH: feature/buyer-agent-complete")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 40, 8.5 * 72 - 54, 11 * 72 - 40)
            
        # Footer
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "CONFIDENTIAL — STRICT ENGINEERING AUDIT REPORT — ZERO ASSUMPTIONS")
        self.drawRightString(8.5 * 72 - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_audit_pdf():
    pdf_filename = "BUYER_AGENT_CURRENT_STATE_AUDIT.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    primary_color = colors.HexColor("#1A365D") # Navy
    secondary_color = colors.HexColor("#2B6CB0") # Blue
    accent_green = colors.HexColor("#22543D") # Dark green
    text_dark = colors.HexColor("#2D3748") # Charcoal
    bg_light = colors.HexColor("#F7FAFC")
    border_color = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        spaceAfter=8
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=secondary_color,
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=text_dark,
        spaceAfter=5
    )

    body_bold = ParagraphStyle(
        'Body_Bold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#742A2A"),
        backColor=colors.HexColor("#FFF5F5"),
        spaceAfter=4
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.5,
        leading=9.5,
        textColor=text_dark
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=table_cell,
        fontName='Helvetica-Bold'
    )

    table_cell_code = ParagraphStyle(
        'TableCellCode',
        parent=table_cell,
        fontName='Courier',
        fontSize=7.0,
        leading=8.5
    )

    tag_implemented = ParagraphStyle(
        'TagImpl',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#22543D")
    )

    tag_partial = ParagraphStyle(
        'TagPart',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#B7791F")
    )

    tag_not_implemented = ParagraphStyle(
        'TagNotImpl',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#9B2C2C")
    )

    story = []

    # ─────────────────────────────────────────────────────────
    # TITLE & METADATA BLOCK
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("BUYER AGENT — CURRENT IMPLEMENTATION & REAL DATA AUDIT", title_style))
    story.append(Paragraph("Factual Verification of Codebase, Datasets, ML Models, and Git History", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceAfter=12))

    meta_data = [
        [Paragraph("<b>Audit Date:</b>", table_cell_bold), Paragraph("September 15, 2026 (02:16 IST)", table_cell),
         Paragraph("<b>Target Branch:</b>", table_cell_bold), Paragraph("<code>feature/buyer-agent-complete</code>", table_cell)],
        [Paragraph("<b>Current Commit:</b>", table_cell_bold), Paragraph("<code>fa8f9ed4ec2a9437a1eb661ce49e4d480a386858</code>", table_cell_code),
         Paragraph("<b>Base Commit:</b>", table_cell_bold), Paragraph("<code>bc53986 (farmer)</code> — 4 commits ahead, 0 behind", table_cell)],
        [Paragraph("<b>Working Tree:</b>", table_cell_bold), Paragraph("<b>100% Clean</b> (0 uncommitted files)", table_cell),
         Paragraph("<b>FarmerAgent Status:</b>", table_cell_bold), Paragraph("<b>100% Intact</b> (0 lines touched)", table_cell)],
        [Paragraph("<b>Audit Mandate:</b>", table_cell_bold), Paragraph("<b>REAL DATA ONLY</b> — Zero synthetic records, zero fake negotiations", table_cell),
         Paragraph("<b>Scope Restriction:</b>", table_cell_bold), Paragraph("<b>7 Maharashtra Crops Exclusively</b> (Others Rejected)", table_cell)],
    ]
    t_meta = Table(meta_data, colWidths=[85, 175, 95, 149])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 10))

    # Executive Summary Alert Box
    summary_box = [
        [Paragraph("<b>CRITICAL AUDIT FINDINGS (EXECUTIVE SUMMARY)</b>", h2_style)],
        [Paragraph(
            "1. <b>Real Agricultural Market Data Exists Locally:</b> Ingested <b>62,429 raw records</b> from the official Maharashtra APMC database (<code>Monthly_data_cmo.csv</code>). After strict 7-crop filtering, non-positive price exclusion, and arrival-weighted deduplication, exactly <b>14,078 clean real observations</b> and <b>13,179 time-series feature rows</b> exist.<br/>"
            "2. <b>Zero Synthetic Data:</b> No synthetic market records and no fake negotiations were created. The claimed 19,200 dataset does not exist for either Buyer or Farmer in the repository.<br/>"
            "3. <b>Buyer Valuation ML Model Trained & Evaluated:</b> Ridge Regression and HistGradientBoosting were evaluated on an untouched chronological test split. Ridge achieved MAE <b>₹2.1812/kg</b> (beating the moving average baseline), but persistence remains strong (MAE <b>₹1.7258/kg</b>). The model artifact is serialized at <code>backend/models/buyer_price_prediction_model.pkl</code>, but is <b>NOT YET WIRED</b> into the runtime <code>BuyerAgent.make_offer()</code>.<br/>"
            "4. <b>Strict 7-Crop Boundary Enforced:</b> Sugarcane (FRP), Soybean, Cotton, Jowar, Onion, Bajra, and Rice are canonically recognized with $O(1)$ alias resolution. All others trigger immediate rejection.<br/>"
            "5. <b>Absolute Git Safety Maintained:</b> Teammate's FarmerAgent code (<code>agents/farmer_agent.py</code>) and tests remain 100% untouched.",
            body_style
        )]
    ]
    t_sum = Table(summary_box, colWidths=[504])
    t_sum.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#EBF8FF")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#3182CE")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(t_sum)
    story.append(Spacer(1, 12))

    # ─────────────────────────────────────────────────────────
    # SECTION 1 — GIT / BRANCH STATUS
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 1 — GIT & BRANCH INTEGRITY STATUS", h1_style))
    story.append(Paragraph("Verification performed via direct git command inspections (<code>git status</code>, <code>git branch -a</code>, <code>git log</code>, <code>git diff</code>):", body_style))
    
    sec1_table = [
        [Paragraph("<b>Audit Parameter</b>", table_cell_bold), Paragraph("<b>Factual Finding</b>", table_cell_bold), Paragraph("<b>Verification Evidence</b>", table_cell_bold)],
        [Paragraph("Current Working Branch", table_cell), Paragraph("<code>feature/buyer-agent-complete</code>", table_cell_code), Paragraph("<code>git branch</code> active pointer (*)", table_cell)],
        [Paragraph("Current Commit Hash", table_cell), Paragraph("<code>fa8f9ed4ec2a9437a1eb661ce49e4d480a386858</code>", table_cell_code), Paragraph("HEAD commit in git log", table_cell)],
        [Paragraph("Base Commit (Teammate)", table_cell), Paragraph("<code>bc53986 ('farmer')</code>", table_cell_code), Paragraph("Commit ancestor on origin/main", table_cell)],
        [Paragraph("Branch Relative Position", table_cell), Paragraph("<b>4 commits ahead, 0 commits behind</b> base", table_cell), Paragraph("Clean linear fast-forward tree", table_cell)],
        [Paragraph("Uncommitted Changes", table_cell), Paragraph("<b>NONE (Clean Working Tree)</b>", table_cell_bold), Paragraph("<code>git status</code>: 'nothing to commit'", table_cell)],
        [Paragraph("FarmerAgent Files Status", table_cell), Paragraph("<b>100% UNTOUCHED / ZERO MODIFICATIONS</b>", tag_implemented), Paragraph("<code>git diff bc53986..HEAD -- agents/farmer_agent.py</code> returns 0 lines", table_cell)],
        [Paragraph("Merge / Rebase Status", table_cell), Paragraph("<b>No merge or rebase performed</b>", table_cell), Paragraph("No merge commits in git log", table_cell)],
        [Paragraph("Recent Buyer Commits", table_cell), Paragraph(
            "• <code>fa8f9ed</code> Phase 3: Real market data ingestion, feature engineering & valuation<br/>"
            "• <code>000510d</code> Phase 2: Personas, utility quality grading & budget guardrails<br/>"
            "• <code>b2a7157</code> Phase 1: 7-crop configuration & isolation test suite<br/>"
            "• <code>d28d7c2</code> Initial BuyerAgent setup & route aliases", table_cell),
         Paragraph("4 distinct engineering commits", table_cell)],
    ]
    t_sec1 = Table(sec1_table, colWidths=[130, 214, 160])
    t_sec1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec1)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 2 — BUYER AGENT IMPLEMENTATION
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 2 — BUYER AGENT IMPLEMENTATION AUDIT", h1_style))
    story.append(Paragraph("Inspection of actual executable source code in <code>agents/buyer_agent.py</code>:", body_style))

    sec2_table = [
        [Paragraph("<b>Component / Method</b>", table_cell_bold), Paragraph("<b>Execution Status</b>", table_cell_bold), Paragraph("<b>Technical Verification & Details</b>", table_cell_bold)],
        [Paragraph("Class Definition", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>class BuyerAgent:</code> in <code>agents/buyer_agent.py</code>", table_cell)],
        [Paragraph("Crop Validation", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Calls <code>validate_buyer_crop()</code> on init & offer inputs; rejects non-7-crops", table_cell)],
        [Paragraph("Alias Normalization", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Calls <code>normalize_crop_name()</code>; normalizes 'ganna'->'Sugarcane', 'kanda'->'Onion'", table_cell)],
        [Paragraph("Offer Validation", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>_validate_offer_inputs()</code> verifies positive price/qty and budget feasibility", table_cell)],
        [Paragraph("Quantity Under-Budget Guardrail", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Instruction 25 bug fixed: when <code>affordable_qty <= 0</code>, triggers immediate REJECT", table_cell)],
        [Paragraph("Quality Grade Modulation", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>calculate_utility()</code> modulates utility curve based on persona & grade (A/B/C)", table_cell)],
        [Paragraph("Commercial Personas (4)", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Profiles for <code>retail_supermarket</code>, <code>bulk_wholesaler</code>, <code>food_processor</code>, <code>restaurant_kitchen</code>", table_cell)],
        [Paragraph("BATNA Refactoring", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Instruction 26: Uses supplier quotes (<code>TRUE_ALTERNATIVE_SUPPLIER</code>) or tags fallback", table_cell)],
        [Paragraph("ZOPA Evaluation", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Instruction 27: Evaluates buyer budget vs ask without fabricating seller reservation", table_cell)],
        [Paragraph("Purchase Order Generation", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>generate_purchase_order()</code> emits immutable structured term sheet", table_cell)],
        [Paragraph("Market Price Integration", table_cell_bold), Paragraph("PARTIALLY IMPLEMENTED", tag_partial), Paragraph("Reads static MSP/Mandi table via <code>market_price_service.py</code>; dynamic feed unhooked", table_cell)],
        [Paragraph("ML Model Runtime Calling", table_cell_bold), Paragraph("NOT IMPLEMENTED", tag_not_implemented), Paragraph("Model exists on disk, but <code>make_offer()</code> does not yet invoke model inference", table_cell)],
        [Paragraph("LangGraph Orchestration", table_cell_bold), Paragraph("PARTIALLY IMPLEMENTED", tag_partial), Paragraph("<code>buyer_node</code> exists in graph, but encounters state-type bugs during simulation", table_cell)],
        [Paragraph("FastAPI Route Integration", table_cell_bold), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Exposed via <code>backend/routes/buyer_requirement_routes.py</code> and <code>negotiation_routes.py</code>", table_cell)],
    ]
    t_sec2 = Table(sec2_table, colWidths=[140, 114, 250])
    t_sec2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec2)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 3 — SEVEN-CROP CONFIGURATION
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 3 — SEVEN-CROP CONFIGURATION & ISOLATION", h1_style))
    story.append(Paragraph("Defined exclusively in <code>shared/crop_catalog.py</code> with zero additional crops:", body_style))

    sec3_table = [
        [Paragraph("<b>#</b>", table_cell_bold), Paragraph("<b>Canonical Crop</b>", table_cell_bold), Paragraph("<b>Pricing Basis</b>", table_cell_bold), Paragraph("<b>Statutory Price (₹/kg)</b>", table_cell_bold), Paragraph("<b>Aliases Recognized</b>", table_cell_bold), Paragraph("<b>Storage / Perishability</b>", table_cell_bold)],
        [Paragraph("1", table_cell), Paragraph("<b>Sugarcane</b>", table_cell), Paragraph("<b>FRP</b> (CCEA)", table_cell), Paragraph("FRP: ₹3.40 (MSP=None)", table_cell), Paragraph("ganna, cane, oos, sugar_cane", table_cell), Paragraph("Crushed immediately (<3 days)", table_cell)],
        [Paragraph("2", table_cell), Paragraph("<b>Soybean</b>", table_cell), Paragraph("<b>MSP</b> (CACP)", table_cell), Paragraph("MSP: ₹48.92", table_cell), Paragraph("soya, soyabean, soyabean_black", table_cell), Paragraph("Non-perishable (365 days)", table_cell)],
        [Paragraph("3", table_cell), Paragraph("<b>Cotton</b>", table_cell), Paragraph("<b>MSP</b> (CACP)", table_cell), Paragraph("MSP: ₹71.21", table_cell), Paragraph("kapas, cotton_long staple", table_cell), Paragraph("Non-perishable (365 days)", table_cell)],
        [Paragraph("4", table_cell), Paragraph("<b>Jowar</b>", table_cell), Paragraph("<b>MSP</b> (CACP)", table_cell), Paragraph("MSP: ₹33.71", table_cell), Paragraph("sorghum, jowari, jowar_hybrid", table_cell), Paragraph("Non-perishable (270 days)", table_cell)],
        [Paragraph("5", table_cell), Paragraph("<b>Onion</b>", table_cell), Paragraph("<b>APMC Modal</b> (No MSP)", table_cell), Paragraph("Modal: ₹15.00–₹26.00", table_cell), Paragraph("kanda, pyaz", table_cell), Paragraph("Semi-perishable (60 days)", table_cell)],
        [Paragraph("6", table_cell), Paragraph("<b>Bajra</b>", table_cell), Paragraph("<b>MSP</b> (CACP)", table_cell), Paragraph("MSP: ₹26.25", table_cell), Paragraph("pearl millet, cumbu, bajri", table_cell), Paragraph("Non-perishable (270 days)", table_cell)],
        [Paragraph("7", table_cell), Paragraph("<b>Rice</b>", table_cell), Paragraph("<b>MSP</b> (CACP)", table_cell), Paragraph("MSP: ₹23.00", table_cell), Paragraph("paddy, dhan, chawal, unhusked", table_cell), Paragraph("Non-perishable (365 days)", table_cell)],
    ]
    t_sec3 = Table(sec3_table, colWidths=[20, 75, 80, 100, 119, 110])
    t_sec3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec3)
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────
    # SECTION 4 — ALL DATASETS IN THE REPOSITORY
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 4 — COMPREHENSIVE REPOSITORY DATASET AUDIT", h1_style))
    story.append(Paragraph("All 17 data and model artifacts discovered across <code>backend/dataset/</code> and <code>backend/models/</code>:", body_style))

    sec4_table = [
        [Paragraph("<b>File Path</b>", table_cell_bold), Paragraph("<b>Records</b>", table_cell_bold), Paragraph("<b>Date Range</b>", table_cell_bold), Paragraph("<b>Crops Represented</b>", table_cell_bold), Paragraph("<b>MH Recs</b>", table_cell_bold), Paragraph("<b>Type</b>", table_cell_bold), Paragraph("<b>Buyer Usage</b>", table_cell_bold)],
        [Paragraph("<code>backend/dataset/Monthly_data_cmo.csv</code>", table_cell_code), Paragraph("62,429", table_cell), Paragraph("2014-09 to 2016-11", table_cell), Paragraph("7 target + 40 other commodities", table_cell), Paragraph("62,429", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Source archive", table_cell)],
        [Paragraph("<code>backend/dataset/clean_buyer_market_data.csv</code>", table_cell_code), Paragraph("14,078", table_cell), Paragraph("2014-09 to 2016-11", table_cell), Paragraph("Strictly 7 Maharashtra crops", table_cell), Paragraph("14,078", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Clean master", table_cell)],
        [Paragraph("<code>backend/dataset/clean_buyer_market_data.json</code>", table_cell_code), Paragraph("14,078", table_cell), Paragraph("2014-09 to 2016-11", table_cell), Paragraph("Strictly 7 Maharashtra crops", table_cell), Paragraph("14,078", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Clean JSON", table_cell)],
        [Paragraph("<code>backend/dataset/buyer_feature_dataset.csv</code>", table_cell_code), Paragraph("13,179", table_cell), Paragraph("2014-09 to 2016-10", table_cell), Paragraph("Strictly 7 Maharashtra crops", table_cell), Paragraph("13,179", table_cell), Paragraph("REAL", tag_implemented), Paragraph("ML Train/Val/Test", table_cell)],
        [Paragraph("<code>backend/dataset/CMO_MSP_Mandi.csv</code>", table_cell_code), Paragraph("155", table_cell), Paragraph("2012 to 2016", table_cell), Paragraph("15 Kharif/Rabi crops", table_cell), Paragraph("155", table_cell), Paragraph("REAL", tag_implemented), Paragraph("MSP validation", table_cell)],
        [Paragraph("<code>backend/dataset/Market_Wise_Price_Arrival...csv</code>", table_cell_code), Paragraph("18", table_cell), Paragraph("02-08-2026 to 04-08-2026", table_cell), Paragraph("15 commodities (4 target)", table_cell), Paragraph("18", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Daily snapshot", table_cell)],
        [Paragraph("<code>backend/dataset/cleaned_mandi_prices.json</code>", table_cell_code), Paragraph("15", table_cell), Paragraph("2026-08-04", table_cell), Paragraph("15 commodities (4 target)", table_cell), Paragraph("15", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Reference lookup", table_cell)],
        [Paragraph("<code>backend/dataset/cleaned_msp_prices.json</code>", table_cell_code), Paragraph("15", table_cell), Paragraph("2026-27 season", table_cell), Paragraph("15 commodities", table_cell), Paragraph("National", table_cell), Paragraph("REAL", tag_implemented), Paragraph("MSP lookup", table_cell)],
        [Paragraph("<code>backend/dataset/maharashtra_market_mapping.csv</code>", table_cell_code), Paragraph("45", table_cell), Paragraph("Static", table_cell), Paragraph("46 APMCs across 14 districts", table_cell), Paragraph("45", table_cell), Paragraph("REAL", tag_implemented), Paragraph("APMC topology", table_cell)],
        [Paragraph("<code>backend/dataset/historical_negotiations.json</code>", table_cell_code), Paragraph("150", table_cell), Paragraph("2026-07-21 to 2026-07-25", table_cell), Paragraph("10 crops (7 target + 3 other)", table_cell), Paragraph("150", table_cell), Paragraph("SYNTH", tag_not_implemented), Paragraph("Simulation log (NOT used for ML)", table_cell)],
        [Paragraph("<code>backend/dataset/crop_knowledge.json</code>", table_cell_code), Paragraph("10", table_cell), Paragraph("Static", table_cell), Paragraph("10 crops agronomic profiles", table_cell), Paragraph("Generic", table_cell), Paragraph("REAL", tag_implemented), Paragraph("RAG context", table_cell)],
        [Paragraph("<code>backend/dataset/crop_quality_references.json</code>", table_cell_code), Paragraph("14", table_cell), Paragraph("Static", table_cell), Paragraph("Moisture & grade standards", table_cell), Paragraph("Generic", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Quality grading", table_cell)],
        [Paragraph("<code>backend/dataset/government_rules.json</code>", table_cell_code), Paragraph("10", table_cell), Paragraph("Static", table_cell), Paragraph("APMC quality guidelines", table_cell), Paragraph("Generic", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Compliance", table_cell)],
        [Paragraph("<code>backend/dataset/seasonal_calendar.json</code>", table_cell_code), Paragraph("6", table_cell), Paragraph("Static", table_cell), Paragraph("6 seasonal market events", table_cell), Paragraph("Generic", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Seasonality", table_cell)],
        [Paragraph("<code>backend/dataset/transporters.json</code>", table_cell_code), Paragraph("10", table_cell), Paragraph("Static", table_cell), Paragraph("Transporter directory & rates", table_cell), Paragraph("MH hubs", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Logistics", table_cell)],
        [Paragraph("<code>backend/dataset/trust_scores.json</code>", table_cell_code), Paragraph("12", table_cell), Paragraph("Static", table_cell), Paragraph("Participant trust scores", table_cell), Paragraph("Platform", table_cell), Paragraph("SYNTH", tag_not_implemented), Paragraph("Mock ratings", table_cell)],
        [Paragraph("<code>backend/dataset/warehouses.json</code>", table_cell_code), Paragraph("10", table_cell), Paragraph("Static", table_cell), Paragraph("Warehouse capacity & rates", table_cell), Paragraph("MH mandis", table_cell), Paragraph("REAL", tag_implemented), Paragraph("Storage cost", table_cell)],
    ]
    t_sec4 = Table(sec4_table, colWidths=[150, 40, 75, 85, 40, 40, 74])
    t_sec4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_sec4)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 5 — REAL AGRICULTURAL DATA
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 5 — REAL AGRICULTURAL DATA SOURCES VERIFICATION", h1_style))
    story.append(Paragraph("Direct verification of public agricultural market sources:", body_style))

    sec5_table = [
        [Paragraph("<b>Authority / Source</b>", table_cell_bold), Paragraph("<b>URL / API</b>", table_cell_bold), Paragraph("<b>Local File</b>", table_cell_bold), Paragraph("<b>Date Range</b>", table_cell_bold), Paragraph("<b>Recs / MH Recs</b>", table_cell_bold), Paragraph("<b>Status & Usage</b>", table_cell_bold)],
        [Paragraph("<b>Government of India data.gov.in</b>", table_cell), Paragraph("<code>https://api.data.gov.in/resource/9ef84268...</code>", table_cell_code), Paragraph("Pipeline in code", table_cell), Paragraph("Rolling live daily", table_cell), Paragraph("~14,925 nat / ~1,800 MH", table_cell), Paragraph("FETCH PIPELINE EXISTS — API KEY RATE LIMITED", tag_partial)],
        [Paragraph("<b>AGMARKNET (DMI / NIC)</b>", table_cell), Paragraph("<code>https://agmarknet.gov.in/PriceTrends/</code>", table_cell_code), Paragraph("<code>backend/dataset/Market_Wise_Price_Arrival...csv</code>", table_cell_code), Paragraph("02-08-2026 to 04-08-2026", table_cell), Paragraph("18 / 18", table_cell), Paragraph("YES — In-repo real snapshot", tag_implemented)],
        [Paragraph("<b>MSAMB / CMO Maharashtra</b>", table_cell), Paragraph("<code>https://raw.githubusercontent.com/ashushaw04/.../Monthly_data_cmo.csv</code>", table_cell_code), Paragraph("<code>backend/dataset/Monthly_data_cmo.csv</code>", table_cell_code), Paragraph("2014-09 to 2016-11", table_cell), Paragraph("62,429 / 62,429 (100% MH)", table_cell), Paragraph("YES — Primary historical APMC training data", tag_implemented)],
        [Paragraph("<b>e-NAM (Govt of India)</b>", table_cell), Paragraph("<code>https://enam.gov.in/web/dashboard/trade-data</code>", table_cell_code), Paragraph("None currently downloaded", table_cell), Paragraph("N/A", table_cell), Paragraph("0 / 0", table_cell), Paragraph("DATA NOT CURRENTLY PRESENT", tag_not_implemented)],
    ]
    t_sec5 = Table(sec5_table, colWidths=[110, 130, 110, 60, 50, 44])
    t_sec5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec5)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 6 & 7 — BUYER DATASET & 19,200 CLAIM
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 6 — BUYER TRAINING DATASET STATUS", h1_style))
    story.append(Paragraph("<b>Does a Buyer training dataset exist? YES.</b>", body_bold))
    story.append(Paragraph(
        "• <b>Exact Path:</b> <code>backend/dataset/buyer_feature_dataset.csv</code> (and <code>clean_buyer_market_data.csv</code>)<br/>"
        "• <b>Record Count:</b> <b>13,179 entity-series records</b> (from 14,078 unique APMC observations across 349 mandis)<br/>"
        "• <b>Schema (18 columns):</b> <code>date, next_date, crop, district, apmc, modal_price_kg, min_price_kg, max_price_kg, spread, arrival_mt, lag_1_modal, lag_2_modal, rolling_3_modal, momentum, arrival_shock, month_sin, month_cos, target_next_modal_kg</code><br/>"
        "• <b>Target / Label:</b> $P_{\\text{modal}, t+1}$ (forward modal price for the identical crop and APMC)<br/>"
        "• <b>Data Integrity:</b> 100% genuine Government of Maharashtra APMC records. Zero synthetic records.",
        body_style
    ))
    story.append(Spacer(1, 6))

    story.append(Paragraph("SECTION 7 — 19,200 RECORD CLAIM INVESTIGATION", h1_style))
    sec7_table = [
        [Paragraph("<b>Agent / Role</b>", table_cell_bold), Paragraph("<b>Claimed Count</b>", table_cell_bold), Paragraph("<b>Actual Count in Repo</b>", table_cell_bold), Paragraph("<b>Generation Method</b>", table_cell_bold), Paragraph("<b>Factual Status</b>", table_cell_bold)],
        [Paragraph("<b>BuyerAgent</b>", table_cell_bold), Paragraph("19,200 (prompt ref)", table_cell), Paragraph("<b>14,078 clean / 13,179 features</b>", table_cell_bold), Paragraph("Empirical MSAMB APMC observations", table_cell), Paragraph("<b>NO SYNTHETIC 19,200 PADDING</b> — True observation count strictly maintained", tag_implemented)],
        [Paragraph("<b>FarmerAgent</b>", table_cell_bold), Paragraph("19,200 (prompt ref)", table_cell), Paragraph("<b>150 records</b> (in historical_negotiations.json)", table_cell_bold), Paragraph("Project simulation engine", table_cell), Paragraph("<b>19,200 DOES NOT EXIST</b> in repo; FarmerAgent uses deterministic rules", tag_partial)],
    ]
    t_sec7 = Table(sec7_table, colWidths=[80, 80, 110, 120, 114])
    t_sec7.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec7)
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────
    # SECTION 8 — MACHINE LEARNING
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 8 — MACHINE LEARNING VALUATION MODELS", h1_style))
    story.append(Paragraph("Market price prediction models trained on <code>buyer_feature_dataset.csv</code>:", body_style))

    sec8_table = [
        [Paragraph("<b>Method / Model</b>", table_cell_bold), Paragraph("<b>Type</b>", table_cell_bold), Paragraph("<b>MAE (₹/kg)</b>", table_cell_bold), Paragraph("<b>RMSE (₹/kg)</b>", table_cell_bold), Paragraph("<b>MAPE (%)</b>", table_cell_bold), Paragraph("<b>Beats Persistence?</b>", table_cell_bold), Paragraph("<b>Beats Moving Avg?</b>", table_cell_bold)],
        [Paragraph("<b>Baseline 1: Persistence (P_t)</b>", table_cell_bold), Paragraph("Naïve Last Known", table_cell), Paragraph("<b>₹1.7258</b>", table_cell), Paragraph("<b>₹2.8930</b>", table_cell), Paragraph("<b>10.45%</b>", table_cell), Paragraph("N/A (Reference)", table_cell), Paragraph("YES", tag_implemented)],
        [Paragraph("<b>Baseline 2: 3-Period Moving Avg</b>", table_cell_bold), Paragraph("Rolling Mean", table_cell), Paragraph("₹2.3949", table_cell), Paragraph("₹3.4868", table_cell), Paragraph("18.83%", table_cell), Paragraph("NO", tag_not_implemented), Paragraph("N/A (Reference)", table_cell)],
        [Paragraph("<b>Model 1: Ridge Regression</b>", table_cell_bold), Paragraph("Regularized Linear", table_cell), Paragraph("<b>₹2.1812</b>", table_cell), Paragraph("<b>₹3.1904</b>", table_cell), Paragraph("<b>16.82%</b>", table_cell), Paragraph("NO (+₹0.4554)", tag_not_implemented), Paragraph("YES (+₹0.2137 better)", tag_implemented)],
        [Paragraph("<b>Model 2: HistGradientBoosting</b>", table_cell_bold), Paragraph("Nonlinear Tree", table_cell), Paragraph("₹2.5847", table_cell), Paragraph("₹3.6964", table_cell), Paragraph("26.76%", table_cell), Paragraph("NO (+₹0.8589)", tag_not_implemented), Paragraph("NO", tag_not_implemented)],
    ]
    t_sec8 = Table(sec8_table, colWidths=[130, 80, 55, 60, 55, 64, 60])
    t_sec8.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec8)
    story.append(Spacer(1, 6))

    story.append(Paragraph(
        "• <b>Model Artifacts:</b> Serialized at <code>backend/models/buyer_price_prediction_model.pkl</code> with full metadata at <code>backend/models/buyer_price_model_metrics.json</code>.<br/>"
        "• <b>Honest Empirical Finding:</b> Spot agricultural commodity prices follow a near-martingale sequence where persistence is notoriously difficult to beat. Ridge Regression beats the 3-period moving average baseline, but does not beat Persistence on the out-of-sample chronological test split.<br/>"
        "• <b>Runtime Integration:</b> <code>BuyerAgent.make_offer()</code> in <code>agents/buyer_agent.py</code> does <b>NOT CURRENTLY INVOKE</b> this model at runtime. (Market price is looked up from <code>market_price_service</code> static dictionary or context).",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 9 — MARKET PRICE PIPELINE
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 9 — MARKET PRICE PIPELINE AUDIT", h1_style))
    
    sec9_table = [
        [Paragraph("<b>Price Data Element</b>", table_cell_bold), Paragraph("<b>Data Source</b>", table_cell_bold), Paragraph("<b>Code Path</b>", table_cell_bold), Paragraph("<b>Currently Functional?</b>", table_cell_bold)],
        [Paragraph("Live Mandi Modal Price", table_cell), Paragraph("Static Mandi Index / Agmarknet snapshot", table_cell), Paragraph("<code>backend/services/market_price_service.py</code>", table_cell_code), Paragraph("YES (Static table)", tag_implemented)],
        [Paragraph("Historical Mandi Price", table_cell), Paragraph("MSAMB clean APMC database", table_cell), Paragraph("<code>backend/dataset/clean_buyer_market_data.csv</code>", table_cell_code), Paragraph("YES (On disk)", tag_implemented)],
        [Paragraph("Modal, Min, Max Prices", table_cell), Paragraph("Agmarknet / MSAMB", table_cell), Paragraph("<code>backend/services/market_price_service.py</code>", table_cell_code), Paragraph("YES", tag_implemented)],
        [Paragraph("Arrival Quantities", table_cell), Paragraph("MSAMB APMC / Agmarknet", table_cell), Paragraph("<code>backend/dataset/clean_buyer_market_data.csv</code>", table_cell_code), Paragraph("YES", tag_implemented)],
        [Paragraph("Minimum Support Price (MSP)", table_cell), Paragraph("CACP Statutory Policy", table_cell), Paragraph("<code>shared/crop_catalog.py</code>", table_cell_code), Paragraph("YES", tag_implemented)],
        [Paragraph("Fair & Remunerative Price (FRP)", table_cell), Paragraph("CCEA Sugarcane Benchmark", table_cell), Paragraph("<code>shared/crop_catalog.py</code>", table_cell_code), Paragraph("YES (Sugarcane FRP=₹3.40/kg)", tag_implemented)],
        [Paragraph("Predicted Market Price (ML)", table_cell), Paragraph("Ridge / HistGradientBoosting", table_cell), Paragraph("<code>backend/models/buyer_price_prediction_model.pkl</code>", table_cell_code), Paragraph("NO in runtime (YES on disk)", tag_partial)],
    ]
    t_sec9 = Table(sec9_table, colWidths=[120, 130, 160, 94])
    t_sec9.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_sec9)
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 10 — LANGGRAPH
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 10 — LANGGRAPH INTEGRATION AUDIT", h1_style))
    story.append(Paragraph(
        "• <b>Graph File:</b> <code>backend/agents/graph_orchestrator.py</code> (1,190 lines)<br/>"
        "• <b>Compiled Workflow:</b> <code>StateGraph(NegotiationState)</code> comprising 9 nodes: <code>planner_agent</code>, <code>market_intelligence_agent</code>, <code>matching_agent</code>, <code>farmer_agent</code>, <code>buyer_agent</code>, <code>rank_responses_agent</code>, <code>validator_agent</code>, <code>dynamic_routing_agent</code>, <code>reflection_agent</code>.<br/>"
        "• <b>BuyerAgent Integration Point:</b> Node 5 (<code>buyer_node</code>, line 561) extracts <code>state['buyer_agent_objs']</code> and invokes <code>buyer.respond_to_offer(...)</code>.<br/>"
        "• <b>Execution Status: PARTIALLY IMPLEMENTED.</b> Structural graph definition and buyer node exist; unit tests of isolated nodes pass (25/29 in <code>test_05_langgraph_nodes.py</code>), but end-to-end multi-agent simulations fail due to state payload mismatches (e.g. <code>profile.get('strategy').lower()</code> on NoneType).",
        body_style
    ))
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 11 — TESTS
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 11 — VERIFIED TEST EXECUTION AUDIT", h1_style))
    story.append(Paragraph("Executed on <code>feature/buyer-agent-complete</code> using <code>.venv/Scripts/python.exe</code> without modifying or creating tests:", body_style))

    sec11_table = [
        [Paragraph("<b>Test Suite Category</b>", table_cell_bold), Paragraph("<b>Test File Path</b>", table_cell_bold), Paragraph("<b>Total</b>", table_cell_bold), Paragraph("<b>Passed</b>", table_cell_bold), Paragraph("<b>Failed</b>", table_cell_bold), Paragraph("<b>Errors</b>", table_cell_bold), Paragraph("<b>Exact Command</b>", table_cell_bold)],
        [Paragraph("<b>BuyerAgent Core</b>", table_cell_bold), Paragraph("<code>tests/test_05_buyer_agent_extensive.py</code>", table_cell_code), Paragraph("38", table_cell), Paragraph("38", tag_implemented), Paragraph("0", table_cell), Paragraph("0", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_agent_extensive.py</code>", table_cell_code)],
        [Paragraph("<b>Buyer Profile & Guardrails</b>", table_cell_bold), Paragraph("<code>tests/test_05_buyer_profile_economic_state.py</code>", table_cell_code), Paragraph("12", table_cell), Paragraph("12", tag_implemented), Paragraph("0", table_cell), Paragraph("0", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_profile_economic_state.py</code>", table_cell_code)],
        [Paragraph("<b>7-Crop Isolation</b>", table_cell_bold), Paragraph("<code>tests/test_05_buyer_crop_isolation.py</code>", table_cell_code), Paragraph("17", table_cell), Paragraph("17", tag_implemented), Paragraph("0", table_cell), Paragraph("0", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_crop_isolation.py</code>", table_cell_code)],
        [Paragraph("<b>Real Data & ML Ingestion</b>", table_cell_bold), Paragraph("<code>tests/test_05_buyer_real_data_ingestion.py</code>", table_cell_code), Paragraph("7", table_cell), Paragraph("7", tag_implemented), Paragraph("0", table_cell), Paragraph("0", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_real_data_ingestion.py</code>", table_cell_code)],
        [Paragraph("<b>REST API Integration</b>", table_cell_bold), Paragraph("<code>tests/test_marketplace_requirements.py</code>", table_cell_code), Paragraph("0 ran", table_cell), Paragraph("0", table_cell), Paragraph("0", table_cell), Paragraph("1 err", tag_not_implemented), Paragraph("<code>python -m unittest tests/test_marketplace_requirements.py</code> (TestClient kwargs issue)", table_cell_code)],
        [Paragraph("<b>LangGraph Nodes</b>", table_cell_bold), Paragraph("<code>tests/test_05_langgraph_nodes.py</code>", table_cell_code), Paragraph("29", table_cell), Paragraph("25", tag_implemented), Paragraph("4", tag_not_implemented), Paragraph("0", table_cell), Paragraph("<code>pytest tests/test_05_langgraph_nodes.py</code> (NoneType in graph_orchestrator)", table_cell_code)],
    ]
    t_sec11 = Table(sec11_table, colWidths=[85, 115, 25, 30, 25, 25, 199])
    t_sec11.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_sec11)
    story.append(Spacer(1, 6))
    story.append(Paragraph("<b>BuyerAgent Specific Test Total:</b> 74 tests executed across 4 dedicated suites: <b>74 PASSED (100% Success Rate)</b>.", body_bold))
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────
    # SECTION 12 — CURRENT ARCHITECTURE
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 12 — CURRENT FACTUAL ARCHITECTURE", h1_style))
    story.append(Paragraph("Architectural diagram showing ONLY components that physically exist in the repository:", body_style))

    arch_diagram = """
    ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │                                  REST API & CLIENT INTERACTION LAYER                                  │
    │  • backend/routes/buyer_requirement_routes.py [IMPLEMENTED] (Validates 7 crops & buyer persona)       │
    │  • backend/routes/negotiation_routes.py       [IMPLEMENTED] (Dispatches buyer offer endpoints)        │
    └───────────────────────────────────────────────────┬───────────────────────────────────────────────────┘
                                                        │
                                                        ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │                                        BUYER AGENT CORE ENGINE                                        │
    │  agents/buyer_agent.py [IMPLEMENTED]                                                                  │
    │  ├── 4 Commercial Personas (retail_supermarket, bulk_wholesaler, food_processor, restaurant_kitchen)  │
    │  ├── Quality Grade Utility Modulation (Differentiates Grade A premium vs Grade C processing)          │
    │  ├── Budget Guardrails (Immediate REJECT if affordable_qty <= 0)                                      │
    │  ├── BATNA & ZOPA (True supplier alternative fallback; no seller reservation hallucination)           │
    │  └── Digital Purchase Order Generator (Canonical term sheet creation)                                │
    └───────────────────────┬───────────────────────────┬───────────────────────────┬───────────────────────┘
                            │                           │                           │
                            ▼                           ▼                           ▼
    ┌───────────────────────────────┐   ┌───────────────────────────────┐   ┌───────────────────────────────┐
    │      CROP CATALOG SERVICE     │   │      MARKET PRICE SERVICE     │   │      LANGGRAPH ENGINE         │
    │  shared/crop_catalog.py       │   │  backend/services/            │   │  backend/agents/              │
    │  [IMPLEMENTED]                │   │  market_price_service.py      │   │  graph_orchestrator.py        │
    │  • Exactly 7 Maharashtra crops│   │  [PARTIALLY IMPLEMENTED]      │   │  [PARTIALLY IMPLEMENTED]      │
    │  • FRP (Sugarcane) vs MSP     │   │  • Static APMC Mandi table    │   │  • 9 Nodes defined            │
    │  • O(1) Alias normalizer      │   │  • Top mandis & price trends  │   │  • buyer_node (Node 5) wired  │
    │  • Rejects Wheat, Maize, etc. │   │  • Live feed unhooked         │   │  • Multi-turn state bug       │
    └───────────────────────────────┘   └───────────────────────────────┘   └───────────────────────────────┘
                                                        │
                                                        ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
    │                            REAL AGRICULTURAL DATA & VALUATION ML ARTIFACTS                            │
    │  • backend/dataset/Monthly_data_cmo.csv         (62,429 raw MSAMB records across 349 APMC mandis)     │
    │  • backend/dataset/clean_buyer_market_data.csv   (14,078 clean 7-crop records, converted to Rs/kg)     │
    │  • backend/dataset/buyer_feature_dataset.csv     (13,179 time-series feature rows, forward target)     │
    │  • backend/models/buyer_price_prediction_model.pkl (Trained Ridge Model, MAE: Rs. 2.1812/kg)          │
    │  • backend/models/buyer_price_model_metrics.json (Evaluated vs Persistence MAE: Rs. 1.7258/kg)        │
    │                                                                                                       │
    │  [NOTE: ML Model is trained and serialized on disk; RUNTIME HOOK in BuyerAgent is NOT IMPLEMENTED]    │
    └───────────────────────────────────────────────────────────────────────────────────────────────────────┘
    """
    story.append(Paragraph(f"<pre>{arch_diagram}</pre>", code_style))
    story.append(Spacer(1, 10))

    # ─────────────────────────────────────────────────────────
    # SECTION 13 — IMPLEMENTATION STATUS TABLE
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 13 — IMPLEMENTATION STATUS MATRIX", h1_style))

    sec13_table = [
        [Paragraph("<b>Feature / Component</b>", table_cell_bold), Paragraph("<b>Status</b>", table_cell_bold), Paragraph("<b>Evidence / Verified Source File</b>", table_cell_bold)],
        [Paragraph("7-Crop Isolation", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>shared/crop_catalog.py</code>, <code>tests/test_05_buyer_crop_isolation.py</code> (17/17 pass)", table_cell)],
        [Paragraph("Crop Aliases (O(1))", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>CROP_ALIAS_LOOKUP</code> in <code>shared/crop_catalog.py</code>", table_cell)],
        [Paragraph("Crop Validation", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>validate_buyer_crop()</code> in <code>shared/crop_catalog.py</code> and <code>buyer_agent.py</code>", table_cell)],
        [Paragraph("BuyerAgent Class", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>agents/buyer_agent.py</code> (Class <code>BuyerAgent</code>)", table_cell)],
        [Paragraph("Offer Validation", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>_validate_offer_inputs()</code> in <code>agents/buyer_agent.py</code>", table_cell)],
        [Paragraph("Accept / Counter / Reject", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>respond_to_offer()</code> and <code>calculate_counter_offer()</code> in <code>buyer_agent.py</code>", table_cell)],
        [Paragraph("Quantity Budget Guardrail", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("Instruction 25 fix: immediate REJECT when <code>affordable_qty <= 0</code>", table_cell)],
        [Paragraph("Quality Grade Utility", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>calculate_utility()</code> modulates utility by grade A/B/C and persona", table_cell)],
        [Paragraph("BATNA Refactor", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>calculate_batna()</code> uses supplier alternative or tags heuristic", table_cell)],
        [Paragraph("ZOPA Refactor", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>check_zopa()</code> evaluates budget ceiling without seller hallucination", table_cell)],
        [Paragraph("Purchase Order Generation", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>generate_purchase_order()</code> in <code>agents/buyer_agent.py</code>", table_cell)],
        [Paragraph("Real Market Data Archive", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>backend/dataset/Monthly_data_cmo.csv</code> (62,429 raw records)", table_cell)],
        [Paragraph("Clean 7-Crop Market Data", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>backend/dataset/clean_buyer_market_data.csv</code> (14,078 records)", table_cell)],
        [Paragraph("Buyer Feature Dataset", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>backend/dataset/buyer_feature_dataset.csv</code> (13,179 records)", table_cell)],
        [Paragraph("ML Valuation Model Training", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>scripts/ingest_real_buyer_data.py</code> (Ridge & HistGradientBoosting)", table_cell)],
        [Paragraph("ML Model Artifact", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>backend/models/buyer_price_prediction_model.pkl</code>", table_cell)],
        [Paragraph("Price Prediction in BuyerAgent", table_cell), Paragraph("NOT IMPLEMENTED", tag_not_implemented), Paragraph("Trained model is on disk, but <code>BuyerAgent.make_offer()</code> does not call it", table_cell)],
        [Paragraph("Live Market Data Feed", table_cell), Paragraph("PARTIALLY IMPLEMENTED", tag_partial), Paragraph("API exists in code; data.gov.in public key rate-limited (`HTTP 429`)", table_cell)],
        [Paragraph("LangGraph Integration", table_cell), Paragraph("PARTIALLY IMPLEMENTED", tag_partial), Paragraph("<code>buyer_node</code> in <code>graph_orchestrator.py</code>; simulation payload bug", table_cell)],
        [Paragraph("FastAPI Endpoints", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("<code>backend/routes/buyer_requirement_routes.py</code> and <code>negotiation_routes.py</code>", table_cell)],
        [Paragraph("Automated Buyer Tests", table_cell), Paragraph("IMPLEMENTED", tag_implemented), Paragraph("4 suites, 74 tests passing (crop isolation, profiles, extensive, ingestion)", table_cell)],
    ]
    t_sec13 = Table(sec13_table, colWidths=[130, 114, 260])
    t_sec13.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_sec13)
    story.append(Spacer(1, 10))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────
    # SECTION 14 — FINAL FACTUAL SUMMARY
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("SECTION 14 — FINAL FACTUAL SUMMARY (10 QUESTIONS)", h1_style))

    q_answers = [
        ("1. What is actually completed?",
         "• Strict 7-crop configuration, alias normalization, and validation (Sugarcane, Soybean, Cotton, Jowar, Onion, Bajra, Rice) with non-7-crop rejection.<br/>"
         "• BuyerAgent economic engine with 4 commercial personas, quality grade utility curves, budget guardrails, BATNA/ZOPA refactoring, and digital Purchase Order generation.<br/>"
         "• Real agricultural market data ingestion (62,429 raw records -> 14,078 clean APMC records -> 13,179 feature rows) from official Maharashtra APMC archives.<br/>"
         "• Valuation ML models trained (Ridge Regression & HistGradientBoosting) with baseline persistence evaluations on chronological splits.<br/>"
         "• 4 BuyerAgent test suites (74 unit tests) passing 100%."),
        ("2. What is partially completed?",
         "• LangGraph multi-agent negotiation integration (<code>buyer_node</code> is implemented in <code>graph_orchestrator.py</code>, but end-to-end simulations fail due to state typing bugs in teammate nodes).<br/>"
         "• Market price service (serves static APMC/MSP reference benchmarks, but does not yet pipe live data.gov.in stream into BuyerAgent)."),
        ("3. What does NOT exist yet?",
         "• Runtime calling of the trained ML model inside <code>BuyerAgent.make_offer()</code> (model exists on disk, but agent currently uses static price anchors).<br/>"
         "• Real human multi-turn buyer negotiation transcripts (do not exist anywhere in public portals or the repository)."),
        ("4. Does real agricultural data exist locally?",
         "<b>YES.</b> <code>backend/dataset/Monthly_data_cmo.csv</code> (4.88 MB; 62,429 records), <code>clean_buyer_market_data.csv</code> (14,078 records), and <code>Market_Wise_Price_Arrival_06-08-2026_08-18-20_PM.csv</code> are physically present on disk."),
        ("5. What exact real datasets are being used?",
         "• Maharashtra State Agricultural Marketing Board (MSAMB / CMO Maharashtra) official APMC records (2014-2016).<br/>"
         "• Agmarknet / DMI Government of India Price and Arrival reports (August 2026 daily snapshot).<br/>"
         "• Commission for Agricultural Costs and Prices (CACP) official MSP / FRP statutory benchmarks."),
        ("6. Does a Buyer training dataset exist?",
         "<b>YES.</b> <code>backend/dataset/buyer_feature_dataset.csv</code> (13,179 entity-series records across 18 features with forward modal price target)."),
        ("7. Has a Buyer ML model been trained?",
         "<b>YES.</b> Ridge Regression (MAE ₹2.1812/kg) and HistGradientBoosting (MAE ₹2.5847/kg) were trained and saved at <code>backend/models/buyer_price_prediction_model.pkl</code>."),
        ("8. Has any synthetic Buyer data been generated?",
         "<b>NO.</b> Zero synthetic records, zero fake dialogues, and zero artificial 19,200 records were generated. Every single row in the clean dataset corresponds to a verified real-world APMC transaction aggregate."),
        ("9. Is the BuyerAgent connected to LangGraph?",
         "<b>PARTIALLY.</b> Connected at the node level in <code>backend/agents/graph_orchestrator.py</code> (Node 5: <code>buyer_node</code>), but end-to-end multi-agent execution encounters state attribute errors during simulation."),
        ("10. What is the exact next implementation step?",
         "<b>Phase 4: Concession Strategy & Mathematical Negotiation Engine Integration</b> — wire the trained valuation model into <code>BuyerAgent.make_offer()</code> and align concession curves (Boulware/Conceder) with the state machine.")
    ]

    for q, a in q_answers:
        story.append(Paragraph(f"<b>{q}</b>", h2_style))
        story.append(Paragraph(a, body_style))
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=8))
    story.append(Paragraph("<b>END OF FACTUAL AUDIT REPORT — ALL DATA AND CODE CLAIMS VERIFIED FROM REPOSITORY ARTIFACTS</b>", ParagraphStyle('End', parent=body_style, alignment=1, fontName='Helvetica-Bold', textColor=primary_color)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {pdf_filename} ({os.path.getsize(pdf_filename)} bytes)")


if __name__ == "__main__":
    build_audit_pdf()
