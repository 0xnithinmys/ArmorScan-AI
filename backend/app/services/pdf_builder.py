from fpdf import FPDF
from typing import Any
import json

class ArmorScanPDF(FPDF):
    def header(self):
        # Logo / Branding
        self.set_fill_color(4, 8, 15) # Very dark blue matching UI background #04080f
        self.rect(0, 0, 210, 25, 'F')
        self.set_y(8)
        self.set_font('Helvetica', 'B', 20)
        self.set_text_color(168, 255, 62) # #a8ff3e
        self.cell(0, 10, 'ArmorScan AI', border=0, align='L', fill=False)
        self.set_font('Helvetica', '', 10)
        self.set_text_color(255, 255, 255)
        self.cell(0, 10, 'SECURITY AUDIT REPORT', border=0, align='R', fill=False)
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('Helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title):
        self.set_font('Helvetica', 'B', 16)
        self.set_fill_color(240, 240, 245)
        self.set_text_color(20, 20, 20)
        self.cell(0, 10, f'  {title}', 0, 1, 'L', 1)
        self.ln(4)

    def print_text(self, text, style='', size=11, color=(40, 40, 40)):
        self.set_font('Helvetica', style, size)
        self.set_text_color(*color)
        self.multi_cell(0, 6, text)
        self.ln(2)

def get_severity_color(rating: str):
    r = rating.lower()
    if r == "critical": return (255, 124, 112) # #ff7c70
    if r == "high": return (255, 177, 95)     # #ffb15f
    if r == "medium": return (226, 235, 114)  # #e2eb72
    if r == "low": return (139, 216, 255)     # #8bd8ff
    return (200, 200, 200)

def generate_pdf_report(report: dict[str, Any]) -> bytes:
    pdf = ArmorScanPDF()
    pdf.add_page()
    
    # Target Info
    target_url = report['target'].get('target_url') or report['target'].get('url') or 'Unknown Target'
    pdf.set_font('Helvetica', 'B', 14)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, f'Target: {target_url}', 0, 1)
    
    overall_rating = report['executive_summary']['overall_risk_rating'].upper()
    overall_score = report['executive_summary']['overall_risk_score']
    
    # Overall risk badge
    pdf.set_font('Helvetica', 'B', 12)
    pdf.set_fill_color(*get_severity_color(overall_rating))
    pdf.set_text_color(255, 255, 255)
    if overall_rating.lower() in ['medium', 'low']:
        pdf.set_text_color(0, 0, 0)
    
    pdf.cell(0, 10, f' OVERALL RISK: {overall_rating} ({overall_score}/100) ', 0, 1, 'L', 1)
    pdf.ln(10)
    
    # Executive Summary
    pdf.chapter_title('Executive Summary')
    pdf.print_text(report["executive_summary"]["narrative"])
    pdf.ln(5)
    
    # Findings
    pdf.chapter_title('Prioritized Findings')
    
    for idx, finding in enumerate(report["findings"], 1):
        # Title
        pdf.set_font('Helvetica', 'B', 12)
        pdf.set_text_color(20, 20, 20)
        pdf.cell(0, 8, f"{idx}. {finding.get('title')}", 0, 1)
        
        # Risk Badge
        rating = str(finding.get('risk_rating')).upper()
        score = finding.get('risk_score')
        
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_fill_color(*get_severity_color(rating))
        pdf.set_text_color(255, 255, 255)
        if rating.lower() in ['medium', 'low']:
            pdf.set_text_color(0, 0, 0)
            
        pdf.cell(50, 6, f' RISK: {rating} ({score}/100) ', 0, 1, 'C', 1)
        pdf.ln(2)
        
        # Details
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(30, 6, 'Location:', 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, str(finding.get('location')), 0, 1)
        
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(30, 6, 'Confidence:', 0, 0)
        pdf.set_font('Helvetica', '', 10)
        pdf.cell(0, 6, f"{finding.get('confidence')}%", 0, 1)
        
        pdf.ln(2)
        
        # Description
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, 'Summary:', 0, 1)
        pdf.print_text(str(finding.get('summary')), size=10, color=(60, 60, 60))
        
        # Impact
        pdf.set_font('Helvetica', 'B', 10)
        pdf.cell(0, 6, 'Business Impact:', 0, 1)
        pdf.print_text(str(finding.get('business_impact')), size=10, color=(60, 60, 60))
        
        # Remediation
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(30, 130, 70) # Green tint for remediation
        pdf.cell(0, 6, 'Remediation:', 0, 1)
        pdf.print_text(str(finding.get('remediation')), size=10, color=(40, 100, 50))
        
        pdf.ln(5)
        # Separator line
        pdf.set_draw_color(220, 220, 220)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(5)

    return pdf.output(dest='S')
