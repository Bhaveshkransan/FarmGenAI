"""
Generate BUYER_AGENT_VERIFICATION_REPORT.pdf using ReportLab.
Exhaustively covers all 14 required verification report sections with 100% verified facts.
"""

import os
import sys
from datetime import datetime
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
            self.drawString(54, 11 * 72 - 36, "AGRINEGOTIATOR — INDEPENDENT BUYER AGENT VERIFICATION REPORT")
            self.drawRightString(8.5 * 72 - 54, 11 * 72 - 36, "BRANCH: feature/buyer-agent-verification")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(54, 11 * 72 - 40, 8.5 * 72 - 54, 11 * 72 - 40)
            
        # Footer
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(54, 45, 8.5 * 72 - 54, 45)
        self.drawString(54, 32, "VERIFICATION PR AUDIT — INDEPENDENT REPOSITORY INSPECTION")
        self.drawRightString(8.5 * 72 - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_verification_pdf():
    pdf_filename = "BUYER_AGENT_VERIFICATION_REPORT.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    styles = getSampleStyleSheet()
    
    primary_color = colors.HexColor("#1A365D")   # Deep Navy
    secondary_color = colors.HexColor("#2B6CB0") # Slate Blue
    accent_green = colors.HexColor("#22543D")    # Forest Green
    accent_red = colors.HexColor("#9B2C2C")      # Deep Red
    accent_amber = colors.HexColor("#B7791F")    # Amber
    text_dark = colors.HexColor("#2D3748")       # Charcoal
    bg_light = colors.HexColor("#F7FAFC")
    border_color = colors.HexColor("#E2E8F0")

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=primary_color,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=secondary_color,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'H1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=5,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=secondary_color,
        spaceBefore=7,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=text_dark,
        spaceAfter=4
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
        fontSize=7.0,
        leading=9.0,
        textColor=colors.HexColor("#742A2A"),
        backColor=colors.HexColor("#FFF5F5"),
        spaceAfter=4
    )

    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7.0,
        leading=9.0,
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
        fontSize=6.5,
        leading=8.0
    )

    tag_verified = ParagraphStyle(
        'TagVer',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=accent_green
    )

    tag_partial = ParagraphStyle(
        'TagPart',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=accent_amber
    )

    tag_false = ParagraphStyle(
        'TagFalse',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=accent_red
    )

    story = []

    # ─────────────────────────────────────────────────────────
    # TITLE & METADATA BLOCK
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("BUYER AGENT — INDEPENDENT VERIFICATION REPORT", title_style))
    story.append(Paragraph("Formal Verification Audit for Branch: <code>feature/buyer-agent-verification</code>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=primary_color, spaceAfter=10))

    meta_data = [
        [Paragraph("<b>Audit Date:</b>", table_cell_bold), Paragraph("September 15, 2026 (02:26 IST)", table_cell),
         Paragraph("<b>Verification Branch:</b>", table_cell_bold), Paragraph("<code>feature/buyer-agent-verification</code>", table_cell_code)],
        [Paragraph("<b>Current Commit:</b>", table_cell_bold), Paragraph("<code>fa8f9ed4ec2a9437a1eb661ce49e4d480a386858</code>", table_cell_code),
         Paragraph("<b>PR Base Commit:</b>", table_cell_bold), Paragraph("<code>bc53986 ('farmer')</code> — 4 commits ahead, 0 behind", table_cell)],
        [Paragraph("<b>PR Remote URL:</b>", table_cell_bold), Paragraph("<code>https://github.com/Bhaveshkransan/FarmGenAI/pull/new/feature/buyer-agent-verification</code>", table_cell_code),
         Paragraph("<b>Working Tree:</b>", table_cell_bold), Paragraph("<b>100% Clean</b> (0 uncommitted modifications)", table_cell)],
        [Paragraph("<b>FarmerAgent Files:</b>", table_cell_bold), Paragraph("<b>100% UNTOUCHED (0 diff lines)</b>", tag_verified),
         Paragraph("<b>Audit Mandate:</b>", table_cell_bold), Paragraph("Zero new code, zero synthetic data, zero assumptions", table_cell)],
    ]
    t_meta = Table(meta_data, colWidths=[85, 175, 95, 149])
    t_meta.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), bg_light),
        ('BOX', (0,0), (-1,-1), 1, border_color),
        ('INNERGRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 1. EXECUTIVE SUMMARY
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("1. EXECUTIVE SUMMARY", h1_style))
    summary_text = (
        "This independent verification report audits all technical claims made regarding the BuyerAgent implementation on the "
        "AgriNegotiator repository. Every single claim was verified by directly executing Python inspectors against files, git trees, "
        "model binaries, and test suites without modifying repository code or retraining models.<br/><br/>"
        "<b>Core Verification Results:</b><br/>"
        "1. <b>Git Integrity (VERIFIED):</b> The verification branch <code>feature/buyer-agent-verification</code> is based on commit "
        "<code>fa8f9ed</code>, which sits 4 clean linear commits ahead of the teammate's base commit <code>bc53986 ('farmer')</code>. "
        "FarmerAgent source code (<code>agents/farmer_agent.py</code>) and tests are <b>100% untouched</b> (0 diff lines).<br/>"
        "2. <b>7-Crop Configuration & Isolation (VERIFIED):</b> Exactly 7 canonical Maharashtra crops are configured in "
        "<code>shared/crop_catalog.py</code>. 20 crop aliases normalize with 100% accuracy in $O(1)$ time. 9 tested unsupported crops "
        "(Tomato, Wheat, Potato, Maize, Cabbage, etc.) were confirmed to be strictly rejected by BuyerAgent with ValueError/REJECT.<br/>"
        "3. <b>Dataset Counts & Integrity (VERIFIED DIRECTLY):</b> Direct CSV parsing proved the exact row counts: "
        "<b>62,429 raw records</b> in <code>Monthly_data_cmo.csv</code> (100% Maharashtra), <b>14,078 clean records</b> in "
        "<code>clean_buyer_market_data.csv</code> (0 duplicates, 0 nulls), and <b>13,179 feature rows</b> in <code>buyer_feature_dataset.csv</code>.<br/>"
        "4. <b>Data Provenance (VERIFIED AS THIRD-PARTY MIRROR):</b> The raw APMC data originates from the Maharashtra State Agricultural "
        "Marketing Board (MSAMB / CMO Maharashtra open data), but was retrieved from a public GitHub mirror repository "
        "(<code>ashushaw04/APMC_Argo_Challenge</code>), not directly from the live <code>data.gov.in</code> API.<br/>"
        "5. <b>19,200 Record Claims (FALSE / CONTRADICTED):</b> There is <b>NO 19,200 record dataset</b> in the repository for either "
        "BuyerAgent (which has 14,078 real rows) or FarmerAgent (which has only 150 simulated records in <code>historical_negotiations.json</code>).<br/>"
        "6. <b>ML Model Artifact & Metrics (VERIFIED ON DISK, NOT USED AT RUNTIME):</b> The trained Ridge Regression pipeline exists at "
        "<code>backend/models/buyer_price_prediction_model.pkl</code> (1,807 bytes). All reported test metrics (Persistence MAE 1.7258, "
        "Ridge MAE 2.1812, Moving Avg MAE 2.3949) were <b>100% reproduced mathematically</b>. However, <code>BuyerAgent.make_offer()</code> "
        "in <code>agents/buyer_agent.py</code> does <b>NOT CURRENTLY INVOKE</b> this model at runtime."
    )
    story.append(Paragraph(summary_text, body_style))
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 2. GIT EVIDENCE
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("2. GIT & REPOSITORY EVIDENCE", h1_style))
    git_table = [
        [Paragraph("<b>Item</b>", table_cell_bold), Paragraph("<b>Verified Value</b>", table_cell_bold), Paragraph("<b>Verification Command / Evidence</b>", table_cell_bold)],
        [Paragraph("Current Branch", table_cell), Paragraph("<code>feature/buyer-agent-verification</code>", table_cell_code), Paragraph("<code>git branch</code> (*)", table_cell)],
        [Paragraph("Base Branch Commit", table_cell), Paragraph("<code>bc53986 ('farmer')</code>", table_cell_code), Paragraph("Ancestor commit on origin/main", table_cell)],
        [Paragraph("Current Commit Hash", table_cell), Paragraph("<code>fa8f9ed4ec2a9437a1eb661ce49e4d480a386858</code>", table_cell_code), Paragraph("HEAD commit in git log", table_cell)],
        [Paragraph("BuyerAgent Commits", table_cell), Paragraph("4 commits: <code>fa8f9ed</code>, <code>000510d</code>, <code>b2a7157</code>, <code>d28d7c2</code>", table_cell_code), Paragraph("<code>git log bc53986..HEAD --oneline</code>", table_cell)],
        [Paragraph("Working Tree Status", table_cell), Paragraph("Clean (no uncommitted tracked modifications)", table_cell), Paragraph("<code>git status</code>", table_cell)],
        [Paragraph("FarmerAgent Diff", table_cell), Paragraph("<b>0 files changed, 0 insertions, 0 deletions (100% UNTOUCHED)</b>", tag_verified), Paragraph("<code>git diff bc53986..HEAD -- agents/farmer_agent.py</code>", table_cell_code)],
        [Paragraph("FarmerAgent Tests Diff", table_cell), Paragraph("<b>0 files changed, 0 insertions, 0 deletions (100% UNTOUCHED)</b>", tag_verified), Paragraph("<code>git diff bc53986..HEAD -- tests/test_05_farmer_agent_extensive.py</code>", table_cell_code)],
        [Paragraph("Remote Tracking", table_cell), Paragraph("<code>bhavesh/feature/buyer-agent-verification</code>", table_cell_code), Paragraph("<code>git push -u bhavesh feature/buyer-agent-verification</code>", table_cell)],
    ]
    t_git = Table(git_table, colWidths=[120, 194, 190])
    t_git.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_git)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 3. CODE VERIFICATION
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("3. BUYER AGENT CODE VERIFICATION", h1_style))
    code_table = [
        [Paragraph("<b>Component</b>", table_cell_bold), Paragraph("<b>Source File</b>", table_cell_bold), Paragraph("<b>Status</b>", table_cell_bold), Paragraph("<b>Verified Behavior</b>", table_cell_bold)],
        [Paragraph("Class Definition", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("<code>class BuyerAgent(BaseAgent):</code> line 68", table_cell)],
        [Paragraph("Buyer Personas", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("4 personas (retail_supermarket, bulk_wholesaler, food_processor, restaurant_kitchen)", table_cell)],
        [Paragraph("Quality Utility Modulation", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("<code>calculate_utility()</code> modulates utility by quality grade A/B/C and persona", table_cell)],
        [Paragraph("Budget Guardrail (Inst 25)", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("When <code>affordable_qty <= 0</code>, triggers immediate REJECT (no clamping to 1)", table_cell)],
        [Paragraph("BATNA Refactor (Inst 26)", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("Evaluates supplier alternatives or tags <code>MARKET_REFERENCE_HEURISTIC</code>", table_cell)],
        [Paragraph("ZOPA Refactor (Inst 27)", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("Checks budget ceiling without fabricating seller reservation price", table_cell)],
        [Paragraph("Purchase Order Generation", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("<code>generate_purchase_order()</code> emits canonical TitleCase crop term sheet", table_cell)],
        [Paragraph("Offer Validation", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("VERIFIED", tag_verified), Paragraph("<code>_validate_offer_inputs()</code> intercepts non-positive prices, budget overflow, bad crops", table_cell)],
        [Paragraph("Runtime ML Invocation", table_cell), Paragraph("<code>agents/buyer_agent.py</code>", table_cell_code), Paragraph("NOT IMPLEMENTED", tag_false), Paragraph("Model exists on disk, but <code>make_offer()</code> does NOT call the model", table_cell)],
    ]
    t_code = Table(code_table, colWidths=[110, 130, 80, 184])
    t_code.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_code)
    story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────
    # 4. DATASET VERIFICATION
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("4. DIRECT DATASET VERIFICATION (CALCULATED FROM DISK)", h1_style))
    story.append(Paragraph("All figures calculated directly by opening and iterating every row in the files:", body_style))

    data_calc_table = [
        [Paragraph("<b>Metric / Attribute</b>", table_cell_bold), Paragraph("<b>Raw Dataset (Monthly_data_cmo.csv)</b>", table_cell_bold), Paragraph("<b>Clean Dataset (clean_buyer_market_data.csv)</b>", table_cell_bold), Paragraph("<b>Feature Dataset (buyer_feature_dataset.csv)</b>", table_cell_bold)],
        [Paragraph("Exact File Path", table_cell_bold), Paragraph("<code>backend/dataset/Monthly_data_cmo.csv</code>", table_cell_code), Paragraph("<code>backend/dataset/clean_buyer_market_data.csv</code>", table_cell_code), Paragraph("<code>backend/dataset/buyer_feature_dataset.csv</code>", table_cell_code)],
        [Paragraph("File Size", table_cell_bold), Paragraph("4,885,990 bytes (4.66 MB)", table_cell), Paragraph("954,458 bytes (932 KB)", table_cell), Paragraph("1,562,115 bytes (1.49 MB)", table_cell)],
        [Paragraph("Verified Row Count", table_cell_bold), Paragraph("<b>62,429 rows</b> (MATCHES CLAIM)", tag_verified), Paragraph("<b>14,078 rows</b> (MATCHES CLAIM)", tag_verified), Paragraph("<b>13,179 rows</b> (MATCHES CLAIM)", tag_verified)],
        [Paragraph("Column Count", table_cell_bold), Paragraph("11 columns", table_cell), Paragraph("10 columns", table_cell), Paragraph("18 columns", table_cell)],
        [Paragraph("Date Range", table_cell_bold), Paragraph("2014-09 to 2016-11 (27 months)", table_cell), Paragraph("2014-09 to 2016-11 (27 months)", table_cell), Paragraph("2014-09 to 2016-10 (26 months)", table_cell)],
        [Paragraph("Maharashtra Records", table_cell_bold), Paragraph("62,429 (100.0% Maharashtra)", table_cell), Paragraph("14,078 (100.0% Maharashtra)", table_cell), Paragraph("13,179 (100.0% Maharashtra)", table_cell)],
        [Paragraph("Target 7-Crop Total", table_cell_bold), Paragraph("14,317 raw rows", table_cell), Paragraph("14,078 clean rows", table_cell), Paragraph("13,179 feature rows", table_cell)],
        [Paragraph("Bajra Count", table_cell), Paragraph("2,346 raw", table_cell), Paragraph("2,336 clean", table_cell), Paragraph("2,198 feature rows", table_cell)],
        [Paragraph("Cotton Count", table_cell), Paragraph("1,063 raw", table_cell), Paragraph("1,063 clean", table_cell), Paragraph("941 feature rows", table_cell)],
        [Paragraph("Jowar Count", table_cell), Paragraph("3,716 raw", table_cell), Paragraph("3,710 clean", table_cell), Paragraph("3,491 feature rows", table_cell)],
        [Paragraph("Onion Count", table_cell), Paragraph("1,872 raw", table_cell), Paragraph("1,867 clean", table_cell), Paragraph("1,771 feature rows", table_cell)],
        [Paragraph("Rice / Paddy Count", table_cell), Paragraph("1,580 raw", table_cell), Paragraph("1,363 clean (217 dups merged)", table_cell), Paragraph("1,269 feature rows", table_cell)],
        [Paragraph("Soybean Count", table_cell), Paragraph("3,727 raw", table_cell), Paragraph("3,726 clean", table_cell), Paragraph("3,499 feature rows", table_cell)],
        [Paragraph("Sugarcane Count", table_cell), Paragraph("13 raw", table_cell), Paragraph("13 clean", table_cell), Paragraph("10 feature rows", table_cell)],
        [Paragraph("Duplicate Keys", table_cell_bold), Paragraph("42 exact raw commodity duplicates", table_cell), Paragraph("<b>0 duplicate keys</b>", tag_verified), Paragraph("<b>0 duplicate keys</b>", tag_verified)],
        [Paragraph("Null / Empty Values", table_cell_bold), Paragraph("0 empty cells", table_cell), Paragraph("<b>0 empty cells</b>", tag_verified), Paragraph("<b>0 empty cells</b>", tag_verified)],
    ]
    t_datacalc = Table(data_calc_table, colWidths=[104, 130, 135, 135])
    t_datacalc.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_datacalc)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 5. DATA PROVENANCE & REAL VS SYNTHETIC
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("5. DATA PROVENANCE & REAL VS SYNTHETIC VERIFICATION", h1_style))
    prov_text = (
        "• <b>Origin Classification: THIRD-PARTY MIRROR OF OFFICIAL MAHARASHTRA GOVERNMENT APMC DATA.</b><br/>"
        "• <b>Retrieval Source URL:</b> <code>https://raw.githubusercontent.com/ashushaw04/APMC_Argo_Challenge/master/Data/Monthly_data_cmo.csv</code>.<br/>"
        "• <b>Government Authority:</b> The dataset contains authentic public open data published by the Maharashtra State Agricultural "
        "Marketing Board (MSAMB / CMO Maharashtra) covering 349 APMC mandis. However, it was ingested from a public GitHub mirror, "
        "not a live authenticated query to <code>data.gov.in</code>.<br/>"
        "• <b>Authenticity Verification (REAL):</b> Inspection of individual observations confirmed authentic spot prices, real APMC committee names, "
        "and characteristic reporting anomalies (e.g. 86 records with inverted min/max prices). No synthetic generation scripts exist for market data.<br/>"
        "• <b>Application Seeds (SYNTHETIC):</b> <code>scripts/seed_data.py</code> contains 10 mock farmers, 10 mock buyers, and 10 mock produce items "
        "used for frontend demonstration. In <code>backend/dataset/historical_negotiations.json</code>, 150 simulated negotiations exist."
    )
    story.append(Paragraph(prov_text, body_style))
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 6. 19,200 RECORD CLAIM VERIFICATION
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("6. 19,200 RECORD CLAIM VERIFICATION", h1_style))
    claim_19k = [
        [Paragraph("<b>Entity</b>", table_cell_bold), Paragraph("<b>Claimed Count</b>", table_cell_bold), Paragraph("<b>Actual Count in Repo</b>", table_cell_bold), Paragraph("<b>Verified Factual Status</b>", table_cell_bold)],
        [Paragraph("<b>BuyerAgent</b>", table_cell_bold), Paragraph("19,200", table_cell), Paragraph("<b>14,078 clean / 13,179 features</b>", table_cell_bold), Paragraph("<b>CLAIM IS FALSE.</b> Zero synthetic rows were generated to reach 19,200. Only authentic 14,078 APMC observations exist.", tag_false)],
        [Paragraph("<b>FarmerAgent</b>", table_cell_bold), Paragraph("19,200", table_cell), Paragraph("<b>150 records</b>", table_cell_bold), Paragraph("<b>CLAIM IS FALSE / NOT FOUND.</b> FarmerAgent has no 19,200 dataset; uses deterministic rule levels.", tag_false)],
    ]
    t_19k = Table(claim_19k, colWidths=[90, 70, 140, 204])
    t_19k.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_19k)
    story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────
    # 7. 7-CROP VERIFICATION
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("7. SEVEN-CROP VERIFICATION", h1_style))
    story.append(Paragraph("Verified by running <code>scratch/verify_crop_implementation.py</code> against <code>shared/crop_catalog.py</code>:", body_style))
    crop_ver_table = [
        [Paragraph("<b>Canonical Crop</b>", table_cell_bold), Paragraph("<b>Pricing Basis</b>", table_cell_bold), Paragraph("<b>Statutory Benchmark</b>", table_cell_bold), Paragraph("<b>Aliases Verified</b>", table_cell_bold), Paragraph("<b>Rejection Test</b>", table_cell_bold)],
        [Paragraph("<b>Sugarcane</b>", table_cell), Paragraph("FRP (CCEA)", table_cell), Paragraph("FRP: ₹3.40/kg (MSP=None)", table_cell), Paragraph("ganna, cane, sugar cane, oos", table_cell), Paragraph("PASSED (17/17)", tag_verified)],
        [Paragraph("<b>Soybean</b>", table_cell), Paragraph("MSP (CACP)", table_cell), Paragraph("MSP: ₹48.92/kg", table_cell), Paragraph("soya, soyabean, soyabeans", table_cell), Paragraph("PASSED (17/17)", tag_verified)],
        [Paragraph("<b>Cotton</b>", table_cell), Paragraph("MSP (CACP)", table_cell), Paragraph("MSP: ₹71.21/kg", table_cell), Paragraph("kapas, raw cotton, long staple", table_cell), Paragraph("PASSED (17/17)", tag_verified)],
        [Paragraph("<b>Jowar</b>", table_cell), Paragraph("MSP (CACP)", table_cell), Paragraph("MSP: ₹33.71/kg", table_cell), Paragraph("sorghum, jowari, jowar_hybrid", table_cell), Paragraph("PASSED (17/17)", tag_verified)],
        [Paragraph("<b>Onion</b>", table_cell), Paragraph("APMC Modal", table_cell), Paragraph("Modal: ₹15.00–₹26.00/kg (No MSP)", table_cell), Paragraph("kanda, pyaz, onions", table_cell), Paragraph("PASSED (17/17)", tag_verified)],
        [Paragraph("<b>Bajra</b>", table_cell), Paragraph("MSP (CACP)", table_cell), Paragraph("MSP: ₹26.25/kg", table_cell), Paragraph("pearl millet, cumbu, bajri", table_cell), Paragraph("PASSED (17/17)", tag_verified)],
        [Paragraph("<b>Rice</b>", table_cell), Paragraph("MSP (CACP)", table_cell), Paragraph("MSP: ₹23.00/kg", table_cell), Paragraph("paddy, dhan, chawal, unhusked", table_cell), Paragraph("PASSED (17/17)", tag_verified)],
    ]
    t_cropver = Table(crop_ver_table, colWidths=[75, 75, 120, 134, 100])
    t_cropver.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_cropver)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 8, 9 & 10. ML MODEL ARTIFACT & REPRODUCIBILITY
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("8, 9 & 10. ML MODEL ARTIFACT & REPRODUCIBILITY VERIFICATION", h1_style))
    ml_repro_table = [
        [Paragraph("<b>Metric / Parameter</b>", table_cell_bold), Paragraph("<b>Claimed Value</b>", table_cell_bold), Paragraph("<b>Re-calculated Value</b>", table_cell_bold), Paragraph("<b>Verification Status</b>", table_cell_bold)],
        [Paragraph("Model Artifact Path", table_cell), Paragraph("<code>backend/models/buyer_price_prediction_model.pkl</code>", table_cell_code), Paragraph("Exists (1,807 bytes)", table_cell), Paragraph("VERIFIED", tag_verified)],
        [Paragraph("Model Pipeline Object", table_cell), Paragraph("Pipeline(StandardScaler, Ridge)", table_cell), Paragraph("Pipeline(StandardScaler, Ridge(alpha=10.0))", table_cell), Paragraph("VERIFIED", tag_verified)],
        [Paragraph("Training Records", table_cell), Paragraph("9,225 (70% chronological split)", table_cell), Paragraph("9,225 records (`2014-09` to `2016-03`)", table_cell), Paragraph("VERIFIED", tag_verified)],
        [Paragraph("Test Records", table_cell), Paragraph("1,977 (15% chronological split)", table_cell), Paragraph("1,977 records (`2016-07` to `2016-10`)", table_cell), Paragraph("VERIFIED", tag_verified)],
        [Paragraph("Persistence Baseline MAE", table_cell), Paragraph("₹1.7258/kg", table_cell), Paragraph("₹1.7258/kg", table_cell), Paragraph("100% REPRODUCIBLE", tag_verified)],
        [Paragraph("Moving Average (3p) MAE", table_cell), Paragraph("₹2.3949/kg", table_cell), Paragraph("₹2.3949/kg", table_cell), Paragraph("100% REPRODUCIBLE", tag_verified)],
        [Paragraph("Ridge Regression MAE", table_cell), Paragraph("₹2.1812/kg", table_cell), Paragraph("₹2.1812/kg", table_cell), Paragraph("100% REPRODUCIBLE", tag_verified)],
        [Paragraph("Beats Persistence?", table_cell), Paragraph("NO (Persistence is strong)", table_cell), Paragraph("NO (+₹0.4554 difference)", table_cell), Paragraph("VERIFIED", tag_verified)],
        [Paragraph("Beats Moving Average?", table_cell), Paragraph("YES", table_cell), Paragraph("YES (+₹0.2137 better)", table_cell), Paragraph("VERIFIED", tag_verified)],
        [Paragraph("Runtime Invocation", table_cell), Paragraph("N/A", table_cell), Paragraph("Uncalled in `BuyerAgent.make_offer()`", table_cell), Paragraph("NOT IMPLEMENTED", tag_false)],
    ]
    t_ml = Table(ml_repro_table, colWidths=[120, 130, 154, 100])
    t_ml.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_ml)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 11 & 12. RUNTIME ML & LIVE MARKET DATA
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("11 & 12. RUNTIME ML & LIVE MARKET DATA VERIFICATION", h1_style))
    story.append(Paragraph(
        "• <b>Runtime ML Call Verification:</b> Traced <code>agents/buyer_agent.py</code> lines 1-830. BuyerAgent does <b>NOT</b> import "
        "or unpickle <code>buyer_price_prediction_model.pkl</code>. <code>make_offer()</code> computes bids using <code>self.target_price</code> "
        "and <code>self.reservation_price</code> passed at instantiation. The ML model is a verified offline artifact, but is <b>NOT WIRED AT RUNTIME</b>.<br/>"
        "• <b>Live Market Data Probe Verification:</b> Directly queried <code>https://api.data.gov.in/resource/9ef84268...</code> via <code>scratch/verify_live_api.py</code> "
        "at <code>2026-09-14T20:59:05Z</code>. The endpoint responded in 1.26 seconds with <b>HTTP 429: Too Many Requests</b> (<code>{\"error\": \"Rate limit exceeded\"}</code>). "
        "The live pipeline exists in code, but is currently rate-limited on the public gateway key.",
        body_style
    ))
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 13 & 14. LANGGRAPH & TEST CLAIMS
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("13 & 14. LANGGRAPH & TEST SUITE VERIFICATION", h1_style))
    test_exec_table = [
        [Paragraph("<b>Test Suite</b>", table_cell_bold), Paragraph("<b>Test Command</b>", table_cell_bold), Paragraph("<b>Total</b>", table_cell_bold), Paragraph("<b>Pass</b>", table_cell_bold), Paragraph("<b>Fail / Err</b>", table_cell_bold), Paragraph("<b>Verified Result</b>", table_cell_bold)],
        [Paragraph("Buyer Extensive", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_agent_extensive.py</code>", table_cell_code), Paragraph("38", table_cell), Paragraph("38", tag_verified), Paragraph("0", table_cell), Paragraph("PASSED (100%)", tag_verified)],
        [Paragraph("Buyer Economic State", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_profile_economic_state.py</code>", table_cell_code), Paragraph("12", table_cell), Paragraph("12", tag_verified), Paragraph("0", table_cell), Paragraph("PASSED (100%)", tag_verified)],
        [Paragraph("7-Crop Isolation", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_crop_isolation.py</code>", table_cell_code), Paragraph("17", table_cell), Paragraph("17", tag_verified), Paragraph("0", table_cell), Paragraph("PASSED (100%)", tag_verified)],
        [Paragraph("Data Ingestion & ML", table_cell), Paragraph("<code>python -m unittest tests/test_05_buyer_real_data_ingestion.py</code>", table_cell_code), Paragraph("7", table_cell), Paragraph("7", tag_verified), Paragraph("0", table_cell), Paragraph("PASSED (100%)", tag_verified)],
        [Paragraph("<b>TOTAL BUYER TESTS</b>", table_cell_bold), Paragraph("4 dedicated suites", table_cell), Paragraph("<b>74</b>", table_cell_bold), Paragraph("<b>74</b>", tag_verified), Paragraph("<b>0</b>", table_cell), Paragraph("<b>74/74 PASSED (100%)</b>", tag_verified)],
        [Paragraph("LangGraph Nodes", table_cell), Paragraph("<code>pytest tests/test_05_langgraph_nodes.py</code>", table_cell_code), Paragraph("29", table_cell), Paragraph("25", tag_verified), Paragraph("4 failed", tag_false), Paragraph("PARTIAL (NoneType bugs in graph)", tag_partial)],
        [Paragraph("FastAPI Marketplace", table_cell), Paragraph("<code>python -m unittest tests/test_marketplace_requirements.py</code>", table_cell_code), Paragraph("0 ran", table_cell), Paragraph("0", table_cell), Paragraph("1 error", tag_false), Paragraph("Starlette TestClient kwargs bug", tag_false)],
    ]
    t_testexec = Table(test_exec_table, colWidths=[90, 160, 25, 25, 44, 160])
    t_testexec.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_testexec)
    story.append(Spacer(1, 8))

    story.append(PageBreak())

    # ─────────────────────────────────────────────────────────
    # 15. CLAIM VS REALITY TABLE
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("15. CLAIM VS REALITY MATRIX", h1_style))
    matrix_table = [
        [Paragraph("<b>CLAIM</b>", table_cell_bold), Paragraph("<b>VERIFIED?</b>", table_cell_bold), Paragraph("<b>EVIDENCE SOURCE</b>", table_cell_bold), Paragraph("<b>ACTUAL REALITY / FINDING</b>", table_cell_bold)],
        [Paragraph("62,429 raw records", table_cell), Paragraph("VERIFIED", tag_verified), Paragraph("<code>Monthly_data_cmo.csv</code>", table_cell_code), Paragraph("Exactly 62,429 rows, 11 cols, 4.88 MB from MSAMB open data archive", table_cell)],
        [Paragraph("14,078 clean records", table_cell), Paragraph("VERIFIED", tag_verified), Paragraph("<code>clean_buyer_market_data.csv</code>", table_cell_code), Paragraph("Exactly 14,078 rows, 10 cols, strictly 7 crops, 0 duplicates, 0 nulls", table_cell)],
        [Paragraph("13,179 feature records", table_cell), Paragraph("VERIFIED", tag_verified), Paragraph("<code>buyer_feature_dataset.csv</code>", table_cell_code), Paragraph("Exactly 13,179 rows, 18 cols with forward target price and rolling features", table_cell)],
        [Paragraph("Real agricultural data", table_cell), Paragraph("VERIFIED", tag_verified), Paragraph("Inspection of APMC observations", table_cell), Paragraph("100% genuine APMC mandi transactions across 349 Maharashtra mandis", table_cell)],
        [Paragraph("7-Crop Isolation", table_cell), Paragraph("VERIFIED", tag_verified), Paragraph("<code>shared/crop_catalog.py</code>", table_cell_code), Paragraph("Sugarcane (FRP), Soybean, Cotton, Jowar, Onion, Bajra, Rice; all others rejected", table_cell)],
        [Paragraph("74/74 Buyer tests pass", table_cell), Paragraph("VERIFIED", tag_verified), Paragraph("4 unittest suites executed", table_cell), Paragraph("74/74 tests passed in 1.8 seconds (100% pass rate)", table_cell)],
        [Paragraph("Buyer ML Model Trained", table_cell), Paragraph("VERIFIED", tag_verified), Paragraph("<code>buyer_price_prediction_model.pkl</code>", table_cell_code), Paragraph("Ridge Regression trained on 9,225 records; metrics 100% reproducible", table_cell)],
        [Paragraph("Buyer ML Runtime Used", table_cell), Paragraph("FALSE", tag_false), Paragraph("<code>agents/buyer_agent.py</code> lines 1-830", table_cell_code), Paragraph("Model exists on disk, but <code>BuyerAgent.make_offer()</code> does NOT call it", table_cell)],
        [Paragraph("Live market data works", table_cell), Paragraph("PARTIALLY", tag_partial), Paragraph("Live HTTP probe to data.gov.in", table_cell), Paragraph("Endpoint responds in 1.26s, but is rate-limited (HTTP 429)", table_cell)],
        [Paragraph("LangGraph Integration", table_cell), Paragraph("PARTIALLY", tag_partial), Paragraph("<code>backend/agents/graph_orchestrator.py</code>", table_cell_code), Paragraph("Node 5 wired; 25/29 node tests pass; multi-agent simulation has state bugs", table_cell)],
        [Paragraph("19,200 Buyer records", table_cell), Paragraph("FALSE", tag_false), Paragraph("Full repository file & grep scan", table_cell), Paragraph("Does not exist; Buyer has 14,078 real rows (no synthetic padding)", table_cell)],
        [Paragraph("19,200 Farmer records", table_cell), Paragraph("FALSE", tag_false), Paragraph("Full repository file & grep scan", table_cell), Paragraph("Does not exist; Farmer has 150 simulated records in historical_negotiations.json", table_cell)],
    ]
    t_mat = Table(matrix_table, colWidths=[100, 75, 129, 200])
    t_mat.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#EDF2F7")),
        ('GRID', (0,0), (-1,-1), 0.5, border_color),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_mat)
    story.append(Spacer(1, 8))

    # ─────────────────────────────────────────────────────────
    # 16. FINAL VERDICT
    # ─────────────────────────────────────────────────────────
    story.append(Paragraph("16. FINAL VERIFICATION VERDICT", h1_style))
    verdict_text = (
        "1. <b>7-Crop Configuration & Alias Normalization: VERIFIED.</b> Implemented in <code>shared/crop_catalog.py</code> and tested by 17 unit tests.<br/>"
        "2. <b>Real Agricultural Dataset: VERIFIED.</b> 62,429 raw records, 14,078 clean records, and 13,179 feature rows verified by direct file parsing.<br/>"
        "3. <b>Data Provenance: VERIFIED AS THIRD-PARTY MIRROR.</b> Originates from MSAMB Maharashtra government open data, retrieved via GitHub mirror.<br/>"
        "4. <b>Zero Synthetic Data: VERIFIED.</b> No synthetic market data was generated for the BuyerAgent.<br/>"
        "5. <b>19,200 Record Claims: FALSE / CONTRADICTED.</b> Does not exist for Buyer (14,078 real) or Farmer (150 simulated).<br/>"
        "6. <b>ML Model Artifact & Metrics: VERIFIED.</b> Ridge model artifact on disk; test MAE 2.1812 is 100% reproducible.<br/>"
        "7. <b>Buyer Runtime ML Calling: NOT IMPLEMENTED.</b> The trained model is not yet connected to <code>BuyerAgent.make_offer()</code>.<br/>"
        "8. <b>Live Market Data: PARTIALLY VERIFIED.</b> Endpoint active, but currently blocked by public API gateway rate limits (HTTP 429).<br/>"
        "9. <b>LangGraph Buyer Integration: PARTIALLY VERIFIED.</b> Node 5 exists and 25/29 tests pass; multi-agent simulation fails on NoneType.<br/>"
        "10. <b>Git Safety & FarmerAgent Integrity: VERIFIED.</b> 0 lines modified in FarmerAgent; 100% clean isolation on <code>feature/buyer-agent-verification</code>."
    )
    story.append(Paragraph(verdict_text, body_style))
    story.append(Spacer(1, 10))

    story.append(HRFlowable(width="100%", thickness=1, color=primary_color, spaceAfter=8))
    story.append(Paragraph("<b>END OF VERIFICATION REPORT — ALL FINDINGS PROVEN FROM PHYSICAL REPOSITORY ARTIFACTS</b>", ParagraphStyle('End', parent=body_style, alignment=1, fontName='Helvetica-Bold', textColor=primary_color)))

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {pdf_filename} ({os.path.getsize(pdf_filename)} bytes)")


if __name__ == "__main__":
    build_verification_pdf()
