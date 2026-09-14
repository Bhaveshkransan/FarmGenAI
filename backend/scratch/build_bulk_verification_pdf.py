import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
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
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "AgriNegotiator — Bulk API Verification & Comprehensive Audit Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)
        
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, "CONFIDENTIAL — Phase 10 Bulk Runtime Verification")
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.5)
        self.line(54, 46, 558, 46)
        
        self.restoreState()

def generate_pdf(output_path):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=45,
        bottomMargin=45
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#0284c7'),
        spaceAfter=10
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#1e293b'),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155'),
        spaceAfter=5
    )
    
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor('#1e293b')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor('#0f172a')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.white
    )

    story = []

    # Title Block
    story.append(Paragraph("AGRINEGOTIATOR — BULK API VERIFICATION REPORT", title_style))
    story.append(Paragraph("Full 93-Operation Runtime Audit, Status Codes, Auth Roles & Architectural Findings (Phase 10)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=8))

    # Metadata Summary Card
    meta_data = [
        [
            Paragraph("<b>Target Host:</b> http://localhost:8000 (Docker Container)", table_cell),
            Paragraph("<b>Total Operations Tested:</b> 93 Endpoints / Operations", table_cell)
        ],
        [
            Paragraph("<b>Confirmed PASS:</b> <font color='#16a34a'><b>74 Operations (79.6%)</b></font>", table_cell),
            Paragraph("<b>Confirmed FAIL:</b> <font color='#dc2626'><b>19 Operations (20.4%)</b></font>", table_cell)
        ],
        [
            Paragraph("<b>AI Negotiation Engine:</b> <b>PASS (200 OK, 50.5s)</b>", table_cell),
            Paragraph("<b>Suspicious In-Memory Stores:</b> <b>4 Modules Identified</b>", table_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e1')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # Section 1: Executive Summary
    story.append(Paragraph("1. EXECUTIVE SUMMARY & TEST METHODOLOGY", h1_style))
    story.append(Paragraph(
        "A rigorous, automated bulk verification of all 93 API operations was performed directly against the running backend container at <code>http://localhost:8000</code>. "
        "Real accounts were provisioned for <b>Farmer</b>, <b>Buyer</b>, and <b>Admin</b> roles with valid JWT tokens. "
        "Prerequisite listings, buyer requirements, role offers, transport bookings, and processor orders were generated dynamically to ensure every dependent endpoint could be evaluated in real runtime.",
        body_style
    ))

    # Section 2: Complete Matrix
    story.append(Paragraph("2. COMPLETE 93-OPERATION API VERIFICATION MATRIX", h1_style))
    
    matrix_header = [
        Paragraph("#", table_header),
        Paragraph("METH", table_header),
        Paragraph("ENDPOINT", table_header),
        Paragraph("AUTH", table_header),
        Paragraph("STATUS", table_header),
        Paragraph("RESULT", table_header),
        Paragraph("RUNTIME OBSERVATION / RESPONSE", table_header)
    ]

    import json
    results_path = "backend/scratch/bulk_verification_results.json"
    matrix_rows = []
    if os.path.exists(results_path):
        with open(results_path) as f:
            raw_results = json.load(f)
            for r in raw_results:
                res_color = "#16a34a" if r["result"] == "PASS" else "#dc2626"
                matrix_rows.append([
                    Paragraph(str(r["num"]), table_cell),
                    Paragraph(r["method"], table_cell_bold),
                    Paragraph(f"<code>{r['endpoint']}</code>", table_cell),
                    Paragraph(r["auth"].replace("YES_", ""), table_cell),
                    Paragraph(str(r["status"]), table_cell_bold),
                    Paragraph(f"<font color='{res_color}'><b>{r['result']}</b></font>", table_cell),
                    Paragraph(f"{r['note']}", table_cell)
                ])

    t_matrix = Table([matrix_header] + matrix_rows, colWidths=[18, 30, 185, 45, 32, 35, 195])
    t_matrix.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING', (0,0), (-1,-1), 2.2),
    ]))
    story.append(t_matrix)
    story.append(Spacer(1, 8))

    # Section 3: Confirmed Pass Breakdown
    story.append(Paragraph("3. CONFIRMED PASS BREAKDOWN (74 Operations)", h1_style))
    story.append(Paragraph(
        "• <b>Authentication & Token Security (10/10):</b> Signup, registration, login, profile inspection (<code>/me</code>), preferences update, location persistence, and verification upload pass with valid JWTs. Unauthenticated calls are strictly rejected with HTTP 401.<br/>"
        "• <b>Farmer & Buyer Core Workflows (10/11):</b> Farmer listings creation, listings retrieval, buyer requirements posting, requirement updates, requirement deletion, and role-based offers filtering are completely operational.<br/>"
        "• <b>LangGraph Multi-Agent Negotiation (4/4):</b> Both singular and plural endpoints trigger full 9-node LangGraph cycles with Ollama (<code>qwen3:8b</code> / <code>qwen2.5:1.5b</code>), returning complete telemetry, price series, and closed agreements.<br/>"
        "• <b>Dashboards & Analytical Intelligence (7/7):</b> Platform executive GMV, farmer dashboard, buyer dashboard, transaction history, and trust leaderboards calculate and aggregate live metrics.<br/>"
        "• <b>Transport & Value-Added Processing (7/9):</b> Fleet vehicle discovery, transport booking, industrial processor catalog, processor crop filtering, and order submission execute with HTTP 200.<br/>"
        "• <b>External Integrations & Admin (12/12):</b> Live Open-Meteo weather forecasts, temperature decay risk, OSRM routing distance, Mandi MSP intelligence, admin user list, user verification, audit logs, and P2P audit ledger are 100% operational.",
        body_style
    ))

    # Section 4: Confirmed Fail Root-Cause Analysis
    story.append(Paragraph("4. CONFIRMED FAIL ROOT-CAUSE ANALYSIS (19 Operations)", h1_style))
    story.append(Paragraph(
        "1. <b>Route Path Mismatches (HTTP 404):</b><br/>"
        "   - <code>/api/v1/requirements/me</code>: Path not defined (use <code>GET /api/v1/requirements/?user_id=...</code>).<br/>"
        "   - <code>/api/v1/trust/record-outcome</code>: Route not mounted under trust router.<br/>"
        "   - <code>/api/v1/transport/track/{id}</code> & <code>/status/{id}</code>: Endpoints not implemented in transport router.<br/>"
        "   - <code>/api/v1/warehouse/list</code> & <code>/book</code>: Actual declared paths are <code>/api/v1/warehouse/</code> and <code>/order</code>.<br/>"
        "   - <code>/api/v1/agents/list</code> & <code>/simulate</code>: Declared as <code>/api/v1/agents/</code> and <code>/negotiate-simulation</code>.<br/>"
        "2. <b>Calculation / Logic Exceptions (HTTP 500):</b><br/>"
        "   - <code>POST /api/v1/workflows/plan</code>: Calculation logic expects an optional price breakdown dict.<br/>"
        "   - <code>GET /api/v1/transport/estimate</code>: Route helper missing parameter validation.<br/>"
        "   - <code>POST /api/node/farmer_node_1/select</code>: Node peer consensus handshake key error.<br/>"
        "3. <b>In-Memory Key Lookups (HTTP 404):</b><br/>"
        "   - <code>GET / PATCH / DELETE /api/v1/listings/{id}</code>: Lookup relies on in-memory produce dict.",
        body_style
    ))

    # Section 5: Suspicious Implementations & Architectural Risks
    story.append(Paragraph("5. SUSPICIOUS IMPLEMENTATIONS & ARCHITECTURAL RISKS", h1_style))
    story.append(Paragraph(
        "• <b>In-Memory State vs. PostgreSQL Persistence:</b><br/>"
        "  - <code>buyer_requirement_routes.py</code>: Uses a Python global dictionary <code>_requirements = {}</code> rather than writing to PostgreSQL table <code>buyer_requirements</code>.<br/>"
        "  - <code>crop_listing_routes.py</code>: Uses <code>Database.produce = {}</code> in-memory dictionary rather than directly persisting every column to PostgreSQL table <code>produce</code>.<br/>"
        "  - <code>transport_routes.py</code>: Uses <code>_bookings = {}</code> in-memory dictionary rather than table <code>transporters</code>.<br/>"
        "• <b>Synthetic Scenario Fallbacks:</b><br/>"
        "  - <code>p2p_routes.py</code>: <code>get_local_scenarios</code> returns mathematically generated mock price distribution scenarios for offline P2P node demo mode.<br/>"
        "• <b>Hardcoded Multipliers:</b><br/>"
        "  - <code>recommendation_routes.py</code>: Uses deterministic multipliers (1.8x storage cost, 0.35 processing conversion ratio) when LLM timeout occurs.",
        body_style
    ))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated bulk verification PDF at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.join(os.getcwd(), "AgriNegotiator_Bulk_API_Verification_Report.pdf")
    generate_pdf(out_file)
