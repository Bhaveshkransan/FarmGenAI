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
            self.drawString(54, 750, "AgriNegotiator — Targeted API Failure Triage & Root Cause Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)
        
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, "CONFIDENTIAL — Phase 10 API Triage & Root-Cause Analysis")
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
        textColor=colors.HexColor('#dc2626'),
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
    story.append(Paragraph("AGRINEGOTIATOR — TARGETED API FAILURE TRIAGE REPORT", title_style))
    story.append(Paragraph("Root-Cause Diagnostics, HTTP 500 Trace Analysis & Actionable Triage Matrix (Phase 10 Baseline)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#dc2626"), spaceAfter=8))

    # Metadata Summary Card
    meta_data = [
        [
            Paragraph("<b>Total Operations Audited:</b> 93 Endpoints / Operations", table_cell),
            Paragraph("<b>Confirmed Pass:</b> <font color='#16a34a'><b>74 Operations (79.6%)</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Total Failures Triaged:</b> 19 Operations (20.4%)", table_cell),
            Paragraph("<b>Genuine Code Bugs:</b> <b>3 Defects (2 P0 Must-Fix, 1 P1 Should-Fix)</b>", table_cell)
        ],
        [
            Paragraph("<b>False / Test-Data Artifacts:</b> 8 Items (Role Rejections & Deletions)", table_cell),
            Paragraph("<b>Route Path Mismatches:</b> 8 Items (Undeclared/Aliased Subpaths)", table_cell)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#fef2f2')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#fca5a5')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # Section 1: Executive Summary
    story.append(Paragraph("1. EXECUTIVE SUMMARY & TRIAGE SCOPE", h1_style))
    story.append(Paragraph(
        "A rigorous, source-code level triage was conducted across all 19 recorded failures from the bulk API verification run. "
        "Each failure was inspected against its route handler, service implementation, database schema, and runtime exception logs. "
        "<b>Key Finding:</b> Out of 19 reported failures, only <b>3 are genuine implementation bugs</b> (all isolated HTTP 500 exceptions). "
        "The remaining 16 failures consist of expected security role rejections (HTTP 403), speculative/undeclared path names (HTTP 404), and test-suite entity lifecycle teardowns.",
        body_style
    ))

    # Section 2: Deep-Dive on HTTP 500s
    story.append(Paragraph("2. DEEP-DIVE ANALYSIS OF THE THREE HTTP 500 RUNTIME FAILURES", h1_style))
    
    deep_500_data = [
        [
            Paragraph("FAILED ENDPOINT", table_header),
            Paragraph("RUNTIME EXCEPTION / TRACE", table_header),
            Paragraph("EXACT SOURCE CODE ROOT CAUSE", table_header),
            Paragraph("REMEDIATION PLAN", table_header)
        ],
        [
            Paragraph("<code>POST /api/v1/workflows/plan</code>", table_cell_bold),
            Paragraph("<code>TypeError: 'coroutine' object is not iterable</code>", table_cell),
            Paragraph("In <code>workflow_service.py</code> line 142, helper <code>_build_reason</code> is declared as <code>async def</code>, but is called synchronously on line 138 inside <code>plan_workflow</code>. It returns an unawaited coroutine object that breaks JSON serialization.", table_cell),
            Paragraph("Change <code>async def _build_reason</code> to synchronous <code>def _build_reason</code> in <code>backend/services/workflow_service.py</code>.", table_cell)
        ],
        [
            Paragraph("<code>GET /api/v1/transport/estimate</code>", table_cell_bold),
            Paragraph("<code>TypeError: 'coroutine' object is not JSON serializable</code>", table_cell),
            Paragraph("In <code>transport_routes.py</code> line 112, <code>assign_transport</code> is an asynchronous function (<code>async def</code>), but is invoked without <code>await</code> keyword: <code>result = assign_transport(...)</code>.", table_cell),
            Paragraph("Add <code>await</code> to <code>result = await assign_transport(...)</code> in <code>backend/routes/transport_routes.py</code>.", table_cell)
        ],
        [
            Paragraph("<code>POST /api/node/{id}/select</code>", table_cell_bold),
            Paragraph("<code>AttributeError: type object 'Database' has no attribute 'update_negotiation'</code>", table_cell),
            Paragraph("In <code>backend/main.py</code> line 254, the P2P node handshake handler invokes <code>Database.update_negotiation(neg_id, neg_record)</code>. The <code>Database</code> class defines <code>upsert_negotiation_async</code> / dict caching, but not <code>update_negotiation</code>.", table_cell),
            Paragraph("Replace call with <code>Database.negotiations[neg_id] = neg_record</code> and <code>Database.add_history(...)</code>.", table_cell)
        ]
    ]
    t_500 = Table(deep_500_data, colWidths=[120, 120, 170, 130])
    t_500.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#991b1b')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#fef2f2')]),
        ('PADDING', (0,0), (-1,-1), 3),
    ]))
    story.append(t_500)
    story.append(Spacer(1, 8))

    # Section 3: In-Memory Stores Analysis
    story.append(Paragraph("3. IN-MEMORY STORES VS. POSTGRESQL ARCHITECTURE", h1_style))
    story.append(Paragraph(
        "• <b><code>_requirements = {}</code> in <code>buyer_requirement_routes.py</code>:</b> Added during FR-4 rapid development. PostgreSQL schema currently lacks a dedicated <code>buyer_requirements</code> table (table <code>buyers</code> only stores buyer profiles). <i>Assessment: Temporary implementation. Data does not survive container restarts.</i><br/>"
        "• <b><code>Database.produce = {}</code> in <code>crop_listing_routes.py</code>:</b> Hybrid model. Core fields are persisted to PostgreSQL table <code>produce</code>, but ephemeral attributes (<code>spoilage_days</code>, <code>shelf_life</code>) are indexed in memory. <i>Assessment: Partially persistent.</i><br/>"
        "• <b><code>_bookings = {}</code> in <code>transport_routes.py</code>:</b> PostgreSQL table <code>transporters</code> stores fleet metadata, but live booking slips (<code>booking_...</code>) reside in memory. <i>Assessment: Requires migration to a persistent bookings table in future phases.</i>",
        body_style
    ))

    # Section 4: Comprehensive 19-Failure Table
    story.append(Paragraph("4. COMPREHENSIVE 19-FAILURE TRIAGE MATRIX", h1_style))
    
    matrix_header = [
        Paragraph("#", table_header),
        Paragraph("ENDPOINT", table_header),
        Paragraph("STAT", table_header),
        Paragraph("CAT", table_header),
        Paragraph("BUG?", table_header),
        Paragraph("ROOT CAUSE & ANALYSIS", table_header),
        Paragraph("RECOMMENDED ACTION", table_header),
        Paragraph("PRIORITY", table_header)
    ]

    matrix_rows = [
        [
            Paragraph("1", table_cell),
            Paragraph("<code>POST /api/v1/workflows/plan</code>", table_cell),
            Paragraph("500", table_cell_bold),
            Paragraph("A", table_cell),
            Paragraph("<font color='#dc2626'><b>YES</b></font>", table_cell),
            Paragraph("<code>_build_reason</code> declared <code>async def</code> but called synchronously", table_cell),
            Paragraph("Change to synchronous <code>def _build_reason</code>", table_cell),
            Paragraph("<b>P0 (Must Fix)</b>", table_cell_bold)
        ],
        [
            Paragraph("2", table_cell),
            Paragraph("<code>GET /api/v1/transport/estimate</code>", table_cell),
            Paragraph("500", table_cell_bold),
            Paragraph("A", table_cell),
            Paragraph("<font color='#dc2626'><b>YES</b></font>", table_cell),
            Paragraph("Missing <code>await</code> on <code>assign_transport(...)</code> call", table_cell),
            Paragraph("Add <code>await</code> keyword before call", table_cell),
            Paragraph("<b>P0 (Must Fix)</b>", table_cell_bold)
        ],
        [
            Paragraph("3", table_cell),
            Paragraph("<code>POST /api/node/{id}/select</code>", table_cell),
            Paragraph("500", table_cell_bold),
            Paragraph("A", table_cell),
            Paragraph("<font color='#dc2626'><b>YES</b></font>", table_cell),
            Paragraph("Calls non-existent <code>Database.update_negotiation</code>", table_cell),
            Paragraph("Update method call to match <code>Database</code> dict caching", table_cell),
            Paragraph("<b>P1 (Should Fix)</b>", table_cell_bold)
        ],
        [
            Paragraph("4", table_cell),
            Paragraph("<code>POST /api/v1/role-offers/</code>", table_cell),
            Paragraph("400", table_cell),
            Paragraph("A", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Test payload omitted required <code>urgency</code> and <code>neg_mode</code> fields", table_cell),
            Paragraph("Provide complete payload in test runner", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("5", table_cell),
            Paragraph("<code>GET /api/v1/listings/{id}</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("C", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Listing entity was deleted during earlier test cycle", table_cell),
            Paragraph("Maintain active entity ID across test steps", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("6", table_cell),
            Paragraph("<code>PATCH /api/v1/listings/{id}</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("C", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Listing was deleted in previous test step", table_cell),
            Paragraph("Adjust test suite execution order", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("7", table_cell),
            Paragraph("<code>DELETE /api/v1/listings/{id}</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("C", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Attempted second delete on already-deleted listing", table_cell),
            Paragraph("Test teardown sequence adjustment", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("8", table_cell),
            Paragraph("<code>GET /api/v1/requirements/me</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Path <code>/requirements/me</code> not implemented (use query param filter)", table_cell),
            Paragraph("Use <code>GET /api/v1/requirements/?user_id={id}</code>", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ],
        [
            Paragraph("9", table_cell),
            Paragraph("<code>GET /api/v1/buyers/offers</code>", table_cell),
            Paragraph("403", table_cell),
            Paragraph("D", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Tested with Farmer token; route strictly enforces Buyer role", table_cell),
            Paragraph("Security RBAC working as intended (PASS)", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("10", table_cell),
            Paragraph("<code>GET /api/v1/history/negotiations</code>", table_cell),
            Paragraph("403", table_cell),
            Paragraph("D", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Tested with Farmer token; route strictly enforces Admin role", table_cell),
            Paragraph("Security RBAC working as intended (PASS)", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("11", table_cell),
            Paragraph("<code>POST /api/v1/trust/record-outcome</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Path not declared in <code>trust_routes.py</code> (automated via LangGraph)", table_cell),
            Paragraph("Call <code>GET /api/v1/trust/score/{id}</code> instead", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ],
        [
            Paragraph("12", table_cell),
            Paragraph("<code>GET /api/v1/matching/auto/{id}</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("C", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Stale/deleted listing ID passed to matching route", table_cell),
            Paragraph("Pass active listing ID", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("13", table_cell),
            Paragraph("<code>GET /api/v1/workflows/plan/{id}</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("C", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Stale/deleted listing ID passed to workflow planner", table_cell),
            Paragraph("Pass active listing ID", table_cell),
            Paragraph("P3 (False/Data)", table_cell)
        ],
        [
            Paragraph("14", table_cell),
            Paragraph("<code>GET /api/v1/transport/track/{id}</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Path <code>/track/{id}</code> not declared (declared as <code>/bookings</code>)", table_cell),
            Paragraph("Use <code>GET /api/v1/transport/bookings</code>", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ],
        [
            Paragraph("15", table_cell),
            Paragraph("<code>PATCH /api/v1/transport/status/{id}</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Declared route path is <code>/booking/{id}/status</code>", table_cell),
            Paragraph("Use exact path <code>PATCH /transport/booking/{id}/status</code>", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ],
        [
            Paragraph("16", table_cell),
            Paragraph("<code>GET /api/v1/warehouse/list</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Declared route path is <code>GET /api/v1/warehouse/</code>", table_cell),
            Paragraph("Use exact path <code>GET /api/v1/warehouse/</code>", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ],
        [
            Paragraph("17", table_cell),
            Paragraph("<code>POST /api/v1/warehouse/book</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Declared route path is <code>POST /api/v1/warehouse/order</code>", table_cell),
            Paragraph("Use exact path <code>POST /api/v1/warehouse/order</code>", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ],
        [
            Paragraph("18", table_cell),
            Paragraph("<code>GET /api/v1/agents/list</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Declared route path is <code>GET /api/v1/agents/</code>", table_cell),
            Paragraph("Use exact path <code>GET /api/v1/agents/</code>", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ],
        [
            Paragraph("19", table_cell),
            Paragraph("<code>POST /api/v1/agents/simulate</code>", table_cell),
            Paragraph("404", table_cell),
            Paragraph("B", table_cell),
            Paragraph("NO", table_cell),
            Paragraph("Declared route path is <code>POST /agents/negotiate-simulation</code>", table_cell),
            Paragraph("Use exact path <code>POST /api/v1/agents/negotiate-simulation</code>", table_cell),
            Paragraph("P2 (Can Defer)", table_cell)
        ]
    ]

    t_matrix = Table([matrix_header] + matrix_rows, colWidths=[14, 110, 22, 18, 24, 160, 142, 50], repeatRows=1)
    t_matrix.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING', (0,0), (-1,-1), 2),
    ]))
    story.append(t_matrix)
    story.append(Spacer(1, 8))

    # Section 5: Prioritized Summary
    story.append(Paragraph("5. PRIORITIZED ACTION PLAN", h1_style))
    story.append(Paragraph(
        "<b>1. MUST FIX Before Demo (2 Items — Both P0):</b><br/>"
        "• <code>POST /api/v1/workflows/plan</code>: Remove <code>async</code> from <code>_build_reason</code> helper in <code>workflow_service.py</code>.<br/>"
        "• <code>GET /api/v1/transport/estimate</code>: Add <code>await</code> to <code>assign_transport(...)</code> call in <code>transport_routes.py</code>.<br/><br/>"
        "<b>2. SHOULD FIX (1 Item — P1):</b><br/>"
        "• <code>POST /api/node/{id}/select</code>: Fix database update call in P2P node selector in <code>backend/main.py</code>.<br/><br/>"
        "<b>3. CAN DEFER / ROUTE PATH ALIASES (8 Items — P2):</b><br/>"
        "• Speculative URL path mismatches (<code>/warehouse/list</code> $\\rightarrow$ <code>/warehouse/</code>, <code>/agents/simulate</code> $\\rightarrow$ <code>/agents/negotiate-simulation</code>). These do not block core frontend workflows.<br/><br/>"
        "<b>4. FALSE / TEST-DATA FAILURES (8 Items — P3):</b><br/>"
        "• Intentional HTTP 403 role-based security blocks and test-suite entity lifecycle teardowns. No backend code modifications needed.",
        body_style
    ))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated triage PDF at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.join(os.getcwd(), "AgriNegotiator_API_Failure_Triage_Report.pdf")
    generate_pdf(out_file)
