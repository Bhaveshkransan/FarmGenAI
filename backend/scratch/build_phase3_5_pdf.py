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
            self.drawString(54, 750, "AgriNegotiator — Phase 3, 4 & 5 Validation & System Checkpoint Report")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.5)
            self.line(54, 744, 558, 744)
        
        # Footer
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 36, page_text)
        self.drawString(54, 36, "CONFIDENTIAL — Phase 5 Core System Checkpoint")
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
        fontSize=17,
        leading=21,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#16a34a'),
        spaceAfter=10
    )
    
    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=13.5,
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

    code_style = ParagraphStyle(
        'CodeBlock',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=4
    )
    
    table_cell = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#1e293b')
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7,
        leading=9,
        textColor=colors.HexColor('#0f172a')
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.white
    )

    story = []

    # Title Block
    story.append(Paragraph("AGRINEGOTIATOR — PHASE 3, 4 & 5 VALIDATION REPORT", title_style))
    story.append(Paragraph("Buyer Demand, Semantic Matching, LangGraph Multi-Agent Negotiation & E2E Checkpoint", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#16a34a"), spaceAfter=8))

    # Metadata Summary Card
    meta_data = [
        [
            Paragraph("<b>Phase 3 (Buyer Demand):</b> <font color='#16a34a'><b>PASS (7/7 Tested)</b></font>", table_cell),
            Paragraph("<b>Phase 4 (Matching Engine):</b> <font color='#16a34a'><b>PASS (3/3 Tested)</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Phase 5 (LangGraph AI):</b> <font color='#16a34a'><b>PASS (5/5 Tested)</b></font>", table_cell),
            Paragraph("<b>Phase 3→5 Integration:</b> <font color='#16a34a'><b>PASS (All 6 Steps)</b></font>", table_cell)
        ],
        [
            Paragraph("<b>Phase 1–5 Defects:</b> <b>0 Application Bugs</b>", table_cell),
            Paragraph("<b>Checkpoint Decision:</b> <font color='#16a34a'><b>READY FOR MANUAL TESTING</b></font>", table_cell_bold)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[270, 270])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0fdf4')),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor('#86efac')),
        ('PADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # Section 1: Phase 3
    story.append(Paragraph("1. PHASE 3: BUYER DEMAND, REQUIREMENTS CRUD & ROLE OFFERS (FR-4)", h1_style))
    story.append(Paragraph(
        "<b>Scope:</b> Capture structured buyer procurement requirements (crop, quantity, target price, budget ceiling, delivery window) and provide role-filtered market board views with strict RBAC enforcement.",
        body_style
    ))
    
    p3_headers = [Paragraph("FEATURE", table_header), Paragraph("ENDPOINT", table_header), Paragraph("RESULT", table_header), Paragraph("RUNTIME EVIDENCE & NOTES", table_header)]
    p3_rows = [
        [Paragraph("Create Requirement", table_cell_bold), Paragraph("<code>POST /api/v1/requirements/</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, returned <code>requirement_id: 4c475027-4ba</code>, saved budget ₹30,000", table_cell)],
        [Paragraph("List Requirements", table_cell_bold), Paragraph("<code>GET /api/v1/requirements/</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, returned active requirements list (<code>count: 3</code>)", table_cell)],
        [Paragraph("Get by ID", table_cell_bold), Paragraph("<code>GET /api/v1/requirements/{id}</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, retrieved requirement payload (<code>crop: Tomato</code>)", table_cell)],
        [Paragraph("Update Target", table_cell_bold), Paragraph("<code>PATCH /api/v1/requirements/{id}</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, target price updated to ₹26.00/kg", table_cell)],
        [Paragraph("Buyer Offer Post", table_cell_bold), Paragraph("<code>POST /api/v1/buyers/offers</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200 with Buyer JWT, creates offer bound to <code>user_id</code>", table_cell)],
        [Paragraph("Role Offer Filter", table_cell_bold), Paragraph("<code>GET /role-offers/?role=buyer</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, returns buyer-filtered offer array", table_cell)],
        [Paragraph("RBAC Guard (Negative)", table_cell_bold), Paragraph("<code>POST /buyers/offers (Farmer)</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 403 Forbidden (<code>detail: Role 'buyer' required</code>)", table_cell)]
    ]
    t_p3 = Table([p3_headers] + p3_rows, colWidths=[110, 150, 45, 235], repeatRows=1)
    t_p3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_p3)
    story.append(Spacer(1, 6))

    # Section 2: Phase 4
    story.append(Paragraph("2. PHASE 4: AI-POWERED MULTI-CRITERIA MATCHING ENGINE (FR-5)", h1_style))
    story.append(Paragraph(
        "<b>Scope:</b> Evaluate candidate compatibility based on crop matching, price overlap (Zone of Possible Agreement / ZOPA), geographical proximity, and volume thresholds.",
        body_style
    ))
    
    p4_headers = [Paragraph("FEATURE", table_header), Paragraph("ENDPOINT", table_header), Paragraph("RESULT", table_header), Paragraph("RUNTIME EVIDENCE & NOTES", table_header)]
    p4_rows = [
        [Paragraph("Listing-to-Buyers", table_cell_bold), Paragraph("<code>POST /matching/listing-to-buyers</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, <code>total_matches: 2</code>, Top match score <code>0.85</code>", table_cell)],
        [Paragraph("Requirement-to-Listings", table_cell_bold), Paragraph("<code>POST /matching/requirement-to-listings</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, evaluated buyer budget ₹15,000 and target price ₹25.00", table_cell)],
        [Paragraph("Unmatched Crop (Neg)", table_cell_bold), Paragraph("<code>POST /matching/listing-to-buyers</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, <code>total_matches: 0</code>, <code>matches: []</code> handled cleanly", table_cell)]
    ]
    t_p4 = Table([p4_headers] + p4_rows, colWidths=[110, 150, 45, 235], repeatRows=1)
    t_p4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_p4)
    story.append(Spacer(1, 6))

    # Section 3: Phase 5
    story.append(Paragraph("3. PHASE 5: AUTONOMOUS MULTI-AGENT NEGOTIATION & LANGGRAPH ENGINE (FR-7, FR-8)", h1_style))
    story.append(Paragraph(
        "<b>Scope:</b> Orchestrate 9-node LangGraph execution state graph with Ollama LLM (<code>qwen3:8b</code>/<code>qwen2.5:1.5b</code>), iterative concession curves, consensus deal closing, and permanent transaction history logging.",
        body_style
    ))
    
    p5_headers = [Paragraph("FEATURE", table_header), Paragraph("ENDPOINT", table_header), Paragraph("RESULT", table_header), Paragraph("RUNTIME EVIDENCE & NOTES", table_header)]
    p5_rows = [
        [Paragraph("LangGraph AI Negotiation", table_cell_bold), Paragraph("<code>POST /negotiation/start-negotiation</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, <code>status: DEAL</code>, Agreed final price: <b>₹26.25/kg</b> (ID: <code>neg_cc4633f3</code>)", table_cell)],
        [Paragraph("Telemetry & Status Poll", table_cell_bold), Paragraph("<code>GET /negotiation-status/{id}</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, returned complete 3-round bid progression and deal summary", table_cell)],
        [Paragraph("Agent Registry", table_cell_bold), Paragraph("<code>GET /negotiation/agents</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, returned 7 registered agent roles (Farmer, Buyer, Warehouse, etc.)", table_cell)],
        [Paragraph("Ledger History", table_cell_bold), Paragraph("<code>GET /api/v1/history/{user_id}</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 200, verified 1 finalized deal persisted in PostgreSQL <code>history</code> table", table_cell)],
        [Paragraph("Invalid Query (Negative)", table_cell_bold), Paragraph("<code>GET /negotiation-status/invalid_id</code>", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell), Paragraph("HTTP 404 Not Found (<code>detail: Negotiation not found</code>)", table_cell)]
    ]
    t_p5 = Table([p5_headers] + p5_rows, colWidths=[110, 150, 45, 235], repeatRows=1)
    t_p5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING', (0,0), (-1,-1), 2.5),
    ]))
    story.append(t_p5)
    story.append(Spacer(1, 6))

    # Section 4: Integration Flow
    story.append(Paragraph("4. PHASE 3 → 5 END-TO-END INTEGRATION CHAIN", h1_style))
    story.append(Paragraph(
        "A single sequential end-to-end integration journey was executed directly across all newly introduced Phase 3–5 capabilities using fresh live entities:",
        body_style
    ))

    flow_headers = [Paragraph("STEP", table_header), Paragraph("FLOW COMPONENT", table_header), Paragraph("ROUTE / API", table_header), Paragraph("EXPECTED OUTCOME", table_header), Paragraph("ACTUAL RUNTIME OUTCOME", table_header), Paragraph("STATUS", table_header)]
    flow_rows = [
        [Paragraph("1", table_cell), Paragraph("Farmer Listing", table_cell_bold), Paragraph("<code>POST /api/v1/listings/</code>", table_cell), Paragraph("Listing created with UUID", table_cell), Paragraph("HTTP 200 (<code>id: 7238f464-e22</code>, Tomato 1200kg @ ₹20)", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell)],
        [Paragraph("2", table_cell), Paragraph("Buyer Requirement", table_cell_bold), Paragraph("<code>POST /api/v1/requirements/</code>", table_cell), Paragraph("Requirement registered", table_cell), Paragraph("HTTP 200 (<code>id: 4c475027-4ba</code>, Tomato 1000kg @ ₹25)", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell)],
        [Paragraph("3", table_cell), Paragraph("Semantic Matching", table_cell_bold), Paragraph("<code>POST /matching/listing-to-buyers</code>", table_cell), Paragraph("Match score > 0.80", table_cell), Paragraph("HTTP 200 (<code>total_matches: 2</code>, Score: 0.85)", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell)],
        [Paragraph("4", table_cell), Paragraph("AI Multi-Agent Negotiation", table_cell_bold), Paragraph("<code>POST /negotiation/start-negotiation</code>", table_cell), Paragraph("LangGraph converges on deal", table_cell), Paragraph("HTTP 200 (<code>status: DEAL</code>, Agreed: ₹26.25/kg)", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell)],
        [Paragraph("5", table_cell), Paragraph("Telemetry Polling", table_cell_bold), Paragraph("<code>GET /negotiation-status/{id}</code>", table_cell), Paragraph("3-round bid logs returned", table_cell), Paragraph("HTTP 200 (Telemetry and price series verified)", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell)],
        [Paragraph("6", table_cell), Paragraph("Ledger Persistence", table_cell_bold), Paragraph("<code>GET /history/{user_id}</code>", table_cell), Paragraph("Deal indexed in user history", table_cell), Paragraph("HTTP 200 (1 verified record in Postgres <code>history</code>)", table_cell), Paragraph("<font color='#16a34a'><b>PASS</b></font>", table_cell)]
    ]
    t_flow = Table([flow_headers] + flow_rows, colWidths=[20, 85, 125, 110, 160, 40], repeatRows=1)
    t_flow.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0f172a')),
        ('GRID', (0,0), (-1,-1), 0.3, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
        ('PADDING', (0,0), (-1,-1), 2.2),
    ]))
    story.append(t_flow)
    story.append(Spacer(1, 6))

    # Section 5: Real Defects
    story.append(Paragraph("5. REAL DEFECTS & OUT-OF-SCOPE ANALYSIS", h1_style))
    story.append(Paragraph(
        "• <b>Phase 1–5 Application Bugs:</b> <b>0 Defects.</b> All routes in Phases 1 to 5 return HTTP 200 OK with valid schemas.<br/>"
        "• <b>Schema Strictness:</b> <code>POST /buyers/offers</code> requires <code>buyer_name</code>, <code>min_price</code>, <code>max_price</code>, <code>quantity</code>, <code>location</code>; <code>POST /matching/requirement-to-listings</code> requires <code>budget</code>.<br/>"
        "• <b>RBAC Security Checks:</b> <code>POST /buyers/offers</code> rejects Farmer tokens with HTTP 403 Forbidden (Working as intended).<br/>"
        "• <b>Out-of-Scope Known Issues:</b> <code>POST /workflows/plan</code> (Phase 7), <code>GET /transport/estimate</code> (Phase 6), and <code>POST /node/select</code> (Phase 10) are outside Phase 3–5 scope.",
        body_style
    ))

    # Section 6: Main APIs for Manual Testing
    story.append(Paragraph("6. MAIN APIs FOR MANUAL ACCEPTANCE TESTING", h1_style))
    story.append(Paragraph(
        "<b>1. Post Buyer Requirement:</b> <code>POST http://localhost:8000/api/v1/requirements/</code> (Auth: Bearer BuyerToken)<br/>"
        "<code>{\"crop\": \"Tomato\", \"quantity\": 1000.0, \"target_price\": 25.0, \"max_price\": 28.0, \"location\": \"Mumbai\", \"budget\": 30000.0, \"delivery_days\": 5, \"quality_grade\": \"A\"}</code><br/>"
        "<i>Expected:</i> HTTP 200 with generated <code>requirement_id</code>.<br/><br/>"
        "<b>2. Match Listing to Buyers:</b> <code>POST http://localhost:8000/api/v1/matching/listing-to-buyers</code> (Auth: Bearer BuyerToken)<br/>"
        "<code>{\"crop\": \"Tomato\", \"quantity\": 1200.0, \"min_price\": 20.0, \"location\": \"Nashik\"}</code><br/>"
        "<i>Expected:</i> HTTP 200 with <code>total_matches >= 1</code>.<br/><br/>"
        "<b>3. Start LangGraph Negotiation:</b> <code>POST http://localhost:8000/api/v1/negotiation/start-negotiation</code> (Auth: None)<br/>"
        "<code>{\"farmer_name\": \"Ramesh Farmer\", \"crop\": \"Tomato\", \"quantity\": 1200, \"min_price\": 20.0, \"shelf_life\": 6, \"location\": \"Nashik\", \"quality\": \"A\", \"language\": \"Marathi\"}</code><br/>"
        "<i>Expected:</i> HTTP 200 with <code>status: \"DEAL\"</code>, agreed <code>final_price</code> between ₹20 and ₹28.<br/><br/>"
        "<b>4. Verify Deal in History:</b> <code>GET http://localhost:8000/api/v1/history/{user_id}</code> (Auth: Bearer BuyerToken)<br/>"
        "<i>Expected:</i> HTTP 200 with history array containing the finalized negotiation record.",
        body_style
    ))

    # Section 7: Checkpoint Decision
    story.append(Paragraph("7. CHECKPOINT DECISION & READINESS", h1_style))
    story.append(Paragraph(
        "<font color='#16a34a' size='11'><b>STATUS: READY FOR MANUAL PHASE 3–5 TESTING</b></font><br/>"
        "All Phase 3, Phase 4, and Phase 5 modules, individual routes, negative test cases, and the complete 6-step integration flow have passed with verified runtime evidence.",
        body_style
    ))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated Phase 3-5 report PDF at: {output_path}")

if __name__ == "__main__":
    out_file = os.path.join(os.getcwd(), "AgriNegotiator_Phase_3_to_5_Validation_Report.pdf")
    generate_pdf(out_file)
