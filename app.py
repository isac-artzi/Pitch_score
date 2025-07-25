import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from openai import OpenAI
import json
import re
import pypdf
import docx
import io
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.pdfgen import canvas
import plotly.io as pio
import tempfile
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse



def clean_markdown(text):
    """Remove markdown formatting that causes display issues"""
    if not text:
        return text
    # Remove asterisks and underscores
    text = text.replace('*', '').replace('_', '')
    # Fix common AI formatting issues
    text = text.replace('•', '-')  # Replace bullet points
    # Ensure proper spacing after periods
    text = re.sub(r'\.([A-Z])', r'. \1', text)
    return text


# Page configuration
st.set_page_config(
    page_title="Investor Proposal Vetting Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main {
        padding: 0rem 1rem;
    }
    .stAlert {
        margin-top: 1rem;
    }
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .big-font {
        font-size: 24px !important;
        font-weight: bold;
    }
    .upload-text {
        font-size: 14px;
        color: #666;
        margin-top: 5px;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions for document processing
def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    try:
        pdf_reader = pypdf.PdfReader(io.BytesIO(file.read()))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {str(e)}"

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    try:
        doc = docx.Document(io.BytesIO(file.read()))
        text = ""
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text
    except Exception as e:
        return f"Error reading DOCX: {str(e)}"

def extract_text_from_txt(file):
    """Extract text from TXT file"""
    try:
        return file.read().decode('utf-8')
    except Exception as e:
        return f"Error reading TXT: {str(e)}"

def process_uploaded_file(uploaded_file):
    """Process uploaded file and extract text"""
    if uploaded_file is None:
        return ""
    
    try:
        file_type = uploaded_file.type
        
        if file_type == "application/pdf":
            return extract_text_from_pdf(uploaded_file)
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            return extract_text_from_docx(uploaded_file)
        elif file_type == "text/plain":
            return extract_text_from_txt(uploaded_file)
        else:
            return "Unsupported file type. Please upload PDF, DOCX, or TXT files."
    except Exception as e:
        return f"Error processing file: {str(e)}"

# URL processing functions
def is_valid_url(text):
    """Check if text contains a valid URL"""
    try:
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.search(text) is not None
    except:
        return False

def extract_urls_from_text(text):
    """Extract all URLs from text"""
    try:
        url_pattern = re.compile(
            r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        )
        return url_pattern.findall(text)
    except:
        return []

def fetch_url_content(url, timeout=10):
    """Fetch content from URL with appropriate handling for different content types"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        
        content_type = response.headers.get('content-type', '').lower()
        
        # Handle PDFs
        if 'application/pdf' in content_type:
            pdf_reader = pypdf.PdfReader(io.BytesIO(response.content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return f"Content from PDF at {url}:\n{text[:3000]}..."  # Limit to 3000 chars
        
        # Handle HTML/Web pages
        elif 'text/html' in content_type:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean up text
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Try to extract meaningful content
            # Look for main content areas
            main_content = soup.find(['main', 'article', 'div'], class_=['content', 'main-content', 'post-content'])
            if main_content:
                text = main_content.get_text(strip=True)
            
            return f"Content from {url}:\n{text[:3000]}..."  # Limit to 3000 chars
        
        # Handle plain text
        elif 'text/plain' in content_type:
            return f"Content from {url}:\n{response.text[:3000]}..."
        
        else:
            return f"Unsupported content type at {url}: {content_type}"
            
    except requests.exceptions.Timeout:
        return f"Timeout accessing {url}"
    except requests.exceptions.RequestException as e:
        return f"Error accessing {url}: {str(e)}"
    except Exception as e:
        return f"Error processing content from {url}: {str(e)}"

def process_text_with_urls(text):
    """Process text field content and fetch any URLs found"""
    if not text or not is_valid_url(text):
        return text
    
    try:
        urls = extract_urls_from_text(text)
        
        if not urls:
            return text
        
        # Combine original text with fetched URL content
        combined_content = text + "\n\n--- Additional Content from URLs ---\n"
        
        for url in urls[:3]:  # Limit to first 3 URLs to avoid too much content
            with st.spinner(f"Fetching content from {url}..."):
                url_content = fetch_url_content(url)
                combined_content += f"\n{url_content}\n"
        
        return combined_content
    except Exception as e:
        st.warning(f"⚠️ Could not fetch URL content: {str(e)}")
        return text

# Analysis Functions
def calculate_comprehensive_metrics(data):
    """Calculate comprehensive metrics for analysis"""
    try:
        metrics = {}
        
        # Unit Economics
        if data.get('cac', 0) > 0:
            metrics['ltv_cac_ratio'] = data.get('ltv', 0) / data['cac']
            metrics['payback_period'] = data['cac'] / (data.get('arr', 0) / 12 / max(data.get('current_customers', 1), 1)) if data.get('arr', 0) > 0 else float('inf')
        else:
            metrics['ltv_cac_ratio'] = 0
            metrics['payback_period'] = float('inf')
        
        # Burn Multiple
        if data.get('burn_rate', 0) > 0 and data.get('current_mrr', 0) > 0:
            net_burn = data['burn_rate'] - data['current_mrr']
            if net_burn > 0 and data.get('monthly_growth_rate', 0) > 0:
                metrics['burn_multiple'] = net_burn / (data['current_mrr'] * data['monthly_growth_rate'] / 100)
            else:
                metrics['burn_multiple'] = 0
        else:
            metrics['burn_multiple'] = float('inf')
        
        # Efficiency Score (0-100)
        ltv_cac_score = min(100, (metrics['ltv_cac_ratio'] / 3) * 50) if metrics['ltv_cac_ratio'] > 0 else 0
        margin_score = data.get('gross_margin', 0) * 0.5
        # Cap the total at 100
        metrics['efficiency_score'] = min(100, (ltv_cac_score + margin_score))
        
        # Growth Score (0-100)
        growth_rate = data.get('monthly_growth_rate', 0)
        if growth_rate >= 20:
            metrics['growth_score'] = 100
        elif growth_rate >= 10:
            metrics['growth_score'] = 80
        elif growth_rate >= 5:
            metrics['growth_score'] = 60
        else:
            metrics['growth_score'] = growth_rate * 10
        
        # Market Score (0-100)
        tam = data.get('tam', 0)
        if tam >= 10000:  # $10B+
            market_size_score = 100
        elif tam >= 1000:  # $1B+
            market_size_score = 80
        elif tam >= 100:   # $100M+
            market_size_score = 60
        else:
            market_size_score = 40
        
        # Market capture potential
        if tam > 0 and data.get('som', 0) > 0:
            capture_ratio = (data['som'] / tam) * 100
            capture_score = min(100, capture_ratio * 20)  # 5% capture = 100 score
        else:
            capture_score = 50
        
        metrics['market_score'] = (market_size_score + capture_score) / 2
        
        # Team Score (0-100)
        team_size_score = min(100, data.get('team_size', 0) * 5)
        technical_ratio = (data.get('technical_team', 0) / max(data.get('team_size', 1), 1)) * 100
        advisor_score = min(100, data.get('advisors_count', 0) * 20)
        metrics['team_score'] = (team_size_score + technical_ratio + advisor_score) / 3
        
        # Traction Score (0-100)
        customer_score = min(100, data.get('current_customers', 0) / 10)
        revenue_score = min(100, (data.get('arr', 0) / 100000) * 100)  # $100k ARR = 100
        funding_score = min(100, (data.get('funding_raised', 0) / 1000000) * 50)  # $2M = 100
        metrics['traction_score'] = (customer_score + revenue_score + funding_score) / 3
        
        # Risk Score (0-100, higher is better)
        runway_score = min(100, (data.get('runway_months', 0) / 18) * 100)  # 18 months = 100
        churn_score = max(0, 100 - (data.get('churn_rate', 0) * 10))  # 10% churn = 0 score
        metrics['risk_score'] = (runway_score + churn_score) / 2
        
        # Overall Investment Score
        weights = {
            'efficiency': 0.20,
            'growth': 0.20,
            'market': 0.15,
            'team': 0.15,
            'traction': 0.20,
            'risk': 0.10
        }
        
        metrics['overall_score'] = (
            metrics['efficiency_score'] * weights['efficiency'] +
            metrics['growth_score'] * weights['growth'] +
            metrics['market_score'] * weights['market'] +
            metrics['team_score'] * weights['team'] +
            metrics['traction_score'] * weights['traction'] +
            metrics['risk_score'] * weights['risk']
        )
        
        return metrics
    except Exception as e:
        st.error(f"⚠️ Error calculating metrics: {str(e)}")
        return {
            'ltv_cac_ratio': 0,
            'efficiency_score': 0,
            'growth_score': 0,
            'market_score': 0,
            'team_score': 0,
            'traction_score': 0,
            'risk_score': 0,
            'overall_score': 0,
            'burn_multiple': 0,
            'payback_period': 0
        }

def generate_ai_insights(data, api_key):
    """Generate comprehensive AI insights for Pro mode"""
    if not api_key:
        return {"error": "Please provide an OpenAI API key for Pro mode analysis."}
    
    if not api_key.startswith('sk-'):
        return {"error": "Invalid API key format. OpenAI API keys should start with 'sk-'"}
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Combine all text data including uploaded documents
        all_text = f"""
        Company: {data.get('company_name', 'N/A')}
        Industry: {data.get('industry', 'N/A')}
        Stage: {data.get('stage', 'N/A')}
        
        BUSINESS & PRODUCT:
        Problem/Solution: {data.get('problem_solution', 'N/A')}
        Market Info: {data.get('market_info', 'N/A')}
        Business Model: {data.get('business_model_desc', 'N/A')}
        Uniqueness: {data.get('uniqueness', 'N/A')}
        IP Assets: {data.get('ip_assets', 'N/A')}
        Progress: {data.get('progress', 'N/A')}
        
        TEAM:
        Experience: {data.get('team_experience', 'N/A')}
        Structure: {data.get('team_structure', 'N/A')}
        Team Size: {data.get('team_size', 0)}
        
        FINANCIALS:
        MRR: ${data.get('current_mrr', 0)}
        ARR: ${data.get('arr', 0)}
        Burn Rate: ${data.get('burn_rate', 0)}
        Runway: {data.get('runway_months', 0)} months
        CAC: ${data.get('cac', 0)}
        LTV: ${data.get('ltv', 0)}
        Gross Margin: {data.get('gross_margin', 0)}%
        Funding Seeking: ${data.get('funding_seeking', 0)}
        
        MARKET & COMPETITION:
        TAM: ${data.get('tam', 0)}M
        Competitors: {data.get('competitors', 'N/A')}
        Competitive Advantage: {data.get('competitive_advantage', 'N/A')}
        Customer Acquisition: {data.get('customer_acquisition', 'N/A')}
        
        RISKS:
        Legal: {data.get('legal_risks', 'N/A')}
        Regulatory: {data.get('regulatory_risks', 'N/A')}
        Other: {data.get('other_risks', 'N/A')}
        
        EXIT STRATEGY: {data.get('exit_strategy', 'N/A')}
        """
        
        # Add uploaded document content
        for doc_type, content in data.get('uploaded_docs', {}).items():
            if content:
                all_text += f"\n\n{doc_type.upper()} DOCUMENT CONTENT:\n{content[:2000]}..."
        
        prompt = f"""
        You are a seasoned venture capital investment partner analyzing a startup proposal. 
        Based on the comprehensive information provided, generate a detailed investment analysis.
        
        {all_text}
        
        YOU MUST respond with ONLY a valid JSON object (no markdown, no explanation, no formatting).
        The JSON must have this exact structure:
        {{
            "investment_thesis": "2-3 sentence executive summary of the investment opportunity",
            "investment_recommendation": "STRONG BUY or BUY or HOLD or PASS",
            "valuation_assessment": "Assessment of the proposed valuation and terms",
            "key_strengths": ["strength 1", "strength 2", "strength 3", "strength 4"],
            "key_concerns": ["concern 1", "concern 2", "concern 3", "concern 4"],
            "due_diligence_priorities": ["priority 1", "priority 2", "priority 3"],
            "growth_potential": "Assessment of growth trajectory and scalability",
            "team_assessment": "Evaluation of team capability and experience",
            "market_timing": "Assessment of market timing and opportunity window",
            "competitive_position": "Analysis of competitive positioning and moat",
            "financial_health": "Assessment of unit economics and financial sustainability",
            "risk_assessment": "Overall risk level: LOW or MEDIUM or HIGH with explanation",
            "recommended_terms": "Suggested investment terms or modifications",
            "post_investment_support": ["support area 1", "support area 2", "support area 3"],
            "comparable_exits": "Similar companies and their exit multiples",
            "investment_score": 85
        }}
        
        Remember: Return ONLY the JSON object, nothing else.
        """
        
        # Use the model that works in your JS
        response = client.chat.completions.create(
            model='gpt-4o-mini',  # Using your working model
            messages=[
                {
                    'role': 'system', 
                    'content': 'You are a venture capital investment assistant. You must always respond with valid JSON only, no markdown formatting, no code blocks, no explanations.'
                },
                {
                    'role': 'user', 
                    'content': prompt
                }
            ],
            temperature=0.7,
            max_tokens=2000  # Increased for comprehensive analysis
        )
        
        # Get the response
        response_text = response.choices[0].message.content.strip()
        
        # Clean up common issues
        # Remove markdown code blocks if present
        if '```json' in response_text:
            response_text = response_text.split('```json')[1].split('```')[0].strip()
        elif '```' in response_text:
            response_text = response_text.split('```')[1].split('```')[0].strip()
        
        # Remove any non-JSON content before the first {
        if not response_text.startswith('{'):
            start = response_text.find('{')
            if start != -1:
                response_text = response_text[start:]
        
        # Remove any non-JSON content after the last }
        if response_text.endswith('}'):
            end = response_text.rfind('}')
            response_text = response_text[:end+1]
        
        # Parse JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            print(f"Response was: {response_text[:500]}")
            
            # Return a structured error response
            return {
                "error": "JSON parsing failed",
                "investment_thesis": "Unable to parse AI response. Please try again.",
                "investment_recommendation": "HOLD",
                "valuation_assessment": "Analysis incomplete",
                "key_strengths": ["Data provided", "Comprehensive information", "Clear metrics", "Established team"],
                "key_concerns": ["Technical analysis error", "Please retry", "Consider manual review", "System processing issue"],
                "due_diligence_priorities": ["Retry analysis", "Manual review", "Verify data"],
                "growth_potential": "Requires reanalysis",
                "team_assessment": "Team information provided",
                "market_timing": "Market analysis pending",
                "competitive_position": "Competitive data available",
                "financial_health": "Financial metrics provided",
                "risk_assessment": "MEDIUM - Analysis incomplete",
                "recommended_terms": "Rerun analysis for recommendations",
                "post_investment_support": ["Technical review", "Strategic planning", "Market analysis"],
                "comparable_exits": "Data pending",
                "investment_score": 50
            }
    
    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower():
            return {"error": "Invalid API key. Please check your OpenAI API key and try again."}
        elif "rate" in error_msg.lower():
            return {"error": "API rate limit reached. Please wait a moment and try again."}
        else:
            return {"error": f"AI analysis failed: {error_msg}"}

def generate_pdf_report(form_data, metrics, ai_insights=None, recommendations=[]):
    """Generate a professional PDF report with charts and analysis"""
    
    # Create a temporary directory for images
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Create PDF buffer
        pdf_buffer = io.BytesIO()
        
        # Create the PDF document
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=18,
        )
        
        # Container for the 'Flowable' objects
        elements = []
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=30,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1f4788'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        subheading_style = ParagraphStyle(
            'CustomSubHeading',
            parent=styles['Heading3'],
            fontSize=14,
            textColor=colors.HexColor('#2c5282'),
            spaceAfter=10
        )
        
        # Cover Page
        elements.append(Spacer(1, 2*inch))
        elements.append(Paragraph("INVESTMENT ANALYSIS REPORT", title_style))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"<b>{form_data['company_name']}</b>", title_style))
        elements.append(Spacer(1, 0.3*inch))
        elements.append(Paragraph(f"{form_data['industry']} | {form_data['stage']}", styles['Normal']))
        elements.append(Spacer(1, 0.5*inch))
        elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", styles['Normal']))
        elements.append(PageBreak())
        
        # Executive Summary
        elements.append(Paragraph("Executive Summary", heading_style))
        
        exec_summary_data = [
            ['Overall Investment Score:', f"{metrics['overall_score']:.0f}/100"],
            ['Company Stage:', form_data['stage']],
            ['Industry:', form_data['industry']],
            ['Funding Seeking:', f"${form_data['funding_seeking']:,.0f}"],
            ['Current ARR:', f"${form_data['arr']:,.0f}"],
            ['Runway:', f"{form_data['runway_months']} months"]
        ]
        
        exec_table = Table(exec_summary_data, colWidths=[3*inch, 3*inch])
        exec_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.lightgrey)
        ]))
        elements.append(exec_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Score Breakdown
        elements.append(Paragraph("Score Breakdown", subheading_style))
        
        score_data = [
            ['Metric', 'Score', 'Status'],
            ['Efficiency', f"{metrics['efficiency_score']:.0f}/100", '✓' if metrics['efficiency_score'] >= 70 else '✗'],
            ['Growth', f"{metrics['growth_score']:.0f}/100", '✓' if metrics['growth_score'] >= 70 else '✗'],
            ['Market', f"{metrics['market_score']:.0f}/100", '✓' if metrics['market_score'] >= 70 else '✗'],
            ['Team', f"{metrics['team_score']:.0f}/100", '✓' if metrics['team_score'] >= 70 else '✗'],
            ['Traction', f"{metrics['traction_score']:.0f}/100", '✓' if metrics['traction_score'] >= 70 else '✗'],
            ['Risk Management', f"{metrics['risk_score']:.0f}/100", '✓' if metrics['risk_score'] >= 70 else '✗']
        ]
        
        score_table = Table(score_data, colWidths=[2.5*inch, 2*inch, 1.5*inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(score_table)
        elements.append(PageBreak())
        
        # Key Metrics
        elements.append(Paragraph("Key Financial Metrics", heading_style))
        
        financial_data = [
            ['Metric', 'Value', 'Benchmark', 'Status'],
            ['LTV/CAC Ratio', f"{metrics['ltv_cac_ratio']:.2f}", '≥ 3.0', '✓' if metrics['ltv_cac_ratio'] >= 3 else '✗'],
            ['Monthly Growth Rate', f"{form_data['monthly_growth_rate']}%", '≥ 10%', '✓' if form_data['monthly_growth_rate'] >= 10 else '✗'],
            ['Gross Margin', f"{form_data['gross_margin']}%", '≥ 70%', '✓' if form_data['gross_margin'] >= 70 else '✗'],
            ['Burn Rate', f"${form_data['burn_rate']:,.0f}", 'Sustainable', '✓' if form_data['runway_months'] >= 12 else '✗'],
            ['Churn Rate', f"{form_data['churn_rate']}%", '≤ 5%', '✓' if form_data['churn_rate'] <= 5 else '✗']
        ]
        
        financial_table = Table(financial_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1*inch])
        financial_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE')
        ]))
        elements.append(financial_table)
        elements.append(Spacer(1, 0.5*inch))
        
        # Market Opportunity
        elements.append(Paragraph("Market Opportunity Analysis", subheading_style))
        
        market_data = [
            ['Market Segment', 'Size'],
            ['Total Addressable Market (TAM)', f"${form_data['tam']}M"],
            ['Serviceable Addressable Market (SAM)', f"${form_data['sam']}M"],
            ['Serviceable Obtainable Market (SOM)', f"${form_data['som']}M"],
            ['Current Market Capture', f"${form_data['arr']/1000000:.2f}M"]
        ]
        
        market_table = Table(market_data, colWidths=[4*inch, 2*inch])
        market_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c5282')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(market_table)
        elements.append(PageBreak())
        
        # Business Overview
        elements.append(Paragraph("Business Overview", heading_style))
        
        # Problem & Solution
        elements.append(Paragraph("Problem & Solution", subheading_style))
        elements.append(Paragraph(form_data.get('problem_solution', 'Not provided'), styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Business Model
        elements.append(Paragraph("Business Model", subheading_style))
        elements.append(Paragraph(form_data.get('business_model_desc', 'Not provided'), styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Competitive Advantage
        elements.append(Paragraph("Competitive Advantage", subheading_style))
        elements.append(Paragraph(form_data.get('competitive_advantage', 'Not provided'), styles['Normal']))
        elements.append(PageBreak())
        
        # Team Analysis
        elements.append(Paragraph("Team Analysis", heading_style))
        
        team_stats_data = [
            ['Team Size', str(form_data['team_size'])],
            ['Technical Team', str(form_data['technical_team'])],
            ['Advisors', str(form_data['advisors_count'])],
            ['Technical Ratio', f"{(form_data['technical_team']/max(form_data['team_size'], 1)*100):.0f}%"]
        ]
        
        team_table = Table(team_stats_data, colWidths=[3*inch, 3*inch])
        team_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.lightblue),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 11),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.white)
        ]))
        elements.append(team_table)
        elements.append(Spacer(1, 0.3*inch))
        
        elements.append(Paragraph("Team Experience", subheading_style))
        elements.append(Paragraph(form_data.get('team_experience', 'Not provided'), styles['Normal']))
        
        # AI Insights (if available)
        if ai_insights and "error" not in ai_insights:
            elements.append(PageBreak())
            elements.append(Paragraph("AI-Powered Investment Analysis", heading_style))
            
            # Investment Thesis
            elements.append(Paragraph("Investment Thesis", subheading_style))
            elements.append(Paragraph(ai_insights.get('investment_thesis', 'Not available'), styles['Normal']))
            elements.append(Spacer(1, 0.3*inch))
            
            # Recommendation
            rec = ai_insights.get('investment_recommendation', 'HOLD')
            rec_color = colors.green if 'BUY' in rec else colors.orange if 'HOLD' in rec else colors.red
            
            rec_style = ParagraphStyle(
                'RecStyle',
                parent=styles['Normal'],
                fontSize=14,
                textColor=rec_color,
                alignment=TA_CENTER
            )
            elements.append(Paragraph(f"<b>Recommendation: {rec.split()[0]}</b>", rec_style))
            elements.append(Spacer(1, 0.3*inch))
            
            # Strengths and Concerns
            col_data = []
            strengths = ai_insights.get('key_strengths', [])
            concerns = ai_insights.get('key_concerns', [])
            
            for i in range(max(len(strengths), len(concerns))):
                strength = f"• {strengths[i]}" if i < len(strengths) else ""
                concern = f"• {concerns[i]}" if i < len(concerns) else ""
                col_data.append([strength, concern])
            
            if col_data:
                sc_table = Table(col_data, colWidths=[3*inch, 3*inch])
                sc_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('FONTSIZE', (0, 0), (-1, -1), 10)
                ]))
                
                elements.append(Paragraph("Strengths vs Concerns", subheading_style))
                header_data = [["Key Strengths", "Key Concerns"]]
                header_table = Table(header_data, colWidths=[3*inch, 3*inch])
                header_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#1f4788')),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold')
                ]))
                elements.append(header_table)
                elements.append(sc_table)
        
        # Recommendations
        elements.append(PageBreak())
        elements.append(Paragraph("Recommendations & Action Items", heading_style))
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                elements.append(Paragraph(f"<b>{i}. {rec['area']}</b>", subheading_style))
                elements.append(Paragraph(f"Issue: {rec['issue']}", styles['Normal']))
                elements.append(Paragraph(f"Action: {rec['action']}", styles['Normal']))
                elements.append(Spacer(1, 0.2*inch))
        else:
            elements.append(Paragraph("No specific recommendations. The company shows strong metrics across all areas.", styles['Normal']))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF value
        pdf_buffer.seek(0)
        pdf_data = pdf_buffer.read()
        
        # Clean up temp directory
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
        os.rmdir(temp_dir)
        
        return pdf_data
        
    except Exception as e:
        # Clean up on error
        if os.path.exists(temp_dir):
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))
            os.rmdir(temp_dir)
        raise e

# Initialize session state
if 'mode' not in st.session_state:
    st.session_state.mode = 'Light'
if 'api_key' not in st.session_state:
    st.session_state.api_key = ''
if 'form_data' not in st.session_state:
    st.session_state.form_data = {}
if 'uploaded_docs' not in st.session_state:
    st.session_state.uploaded_docs = {}

# Header
st.title("Investor Proposal Vetting Tool")
st.subheader("Comprehensive analysis for startup evaluation")
st.markdown("##### Copyright © 2025 - All Rights Reserved - Isac Artzi & SenSym, LLC")
st.caption("Make data-driven investment decisions with confidence - version 1.0.0")

# Privacy Notice Popup
with st.expander("🔒 Privacy Notice & Disclaimer", expanded=False):
    st.info("""
    **Privacy Statement:**
    - No user data is stored after analysis completion
    - All information is processed in real-time and discarded
    - Your API key (if provided) is used only for the current session
    - Uploaded documents are not retained after processing
    
    **Disclaimer:**
    This tool is for general information purposes only. The site assumes no responsibility 
    for errors in judgment or calculations. This tool should not be used as the sole basis 
    for making investment decisions. Always consult with qualified professionals before 
    making investment choices.
    """)

# Mode Selection
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    mode = st.radio(
        "Select Analysis Mode",
        ["Light (No AI)", "Pro (AI-Enhanced)"],
        horizontal=True,
        help="Light mode uses data analytics only. Pro mode includes AI insights."
    )
    st.session_state.mode = mode.split()[0]

# API Key input for Pro mode
if st.session_state.mode == "Pro":
    api_key = st.text_input(
        "Enter your OpenAI API Key",
        type="password",
        placeholder="sk-...",
        help="Your API key is not stored and is used only for this session"
    )
    st.session_state.api_key = api_key
    
    # Validate API key format
    if api_key and not api_key.startswith('sk-'):
        st.error("⚠️ Invalid API key format. OpenAI API keys should start with 'sk-'")

# Questionnaire Form
st.markdown("---")
st.header("📝 Comprehensive Proposal Questionnaire")

if st.session_state.mode == "Pro":
    st.info("💡 **Pro Mode Tip:** You can paste URLs in any text field, and the AI will automatically fetch and analyze the content from those links (e.g., pitch decks, company websites, online documents).")
else:
    st.markdown("You can either type in information or upload documents for each section.")

with st.form("proposal_form"):
    # Basic Company Information
    st.subheader("🏢 Basic Company Information")
    col1, col2 = st.columns(2)
    with col1:
        company_name = st.text_input("Company Name*", placeholder="Enter company name")
        founding_year = st.number_input("Year Founded*", min_value=1900, max_value=2025, value=2023)
        website = st.text_input("Company Website", placeholder="https://www.example.com")
    with col2:
        industry = st.selectbox("Industry*", [
            "Technology", "Healthcare", "FinTech", "E-commerce", "SaaS",
            "Consumer Goods", "B2B Services", "Education", "CleanTech",
            "BioTech", "AI/ML", "Cybersecurity", "Other"
        ])
        stage = st.selectbox("Current Stage*", [
            "Idea/Concept", "MVP", "Early Revenue", "Growth", "Scale", "Pre-IPO"
        ])
        location = st.text_input("Company Location", placeholder="City, Country")
    
    # Section 1: About the Business & Product
    st.markdown("---")
    st.subheader("1️⃣ About the Business & Product")
    
    # Problem/Solution
    st.markdown("#### Problem/Solution")
    problem_solution = st.text_area(
        "What problem are you solving, and for whom? What is unique or proprietary about your solution?*",
        placeholder="Describe the problem, your target audience, and your unique solution...\n\nPro Mode: You can also paste URLs to your pitch deck or product demo here.",
        height=150,
        key="problem_solution"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        problem_doc = st.file_uploader(
            "Or upload a document (Problem/Solution Statement)",
            type=['pdf', 'docx', 'txt'],
            key="problem_doc",
            help="Upload your problem/solution documentation"
        )
    with col2:
        st.markdown("<p class='upload-text'>Supported: PDF, DOCX, TXT</p>", unsafe_allow_html=True)
    
    # Market
    st.markdown("#### Market")
    market_info = st.text_area(
        "How large is the market? How is it evolving?*",
        placeholder="Describe market size (TAM, SAM, SOM), growth trends, and evolution...\n\nPro Mode: Include URLs to market research reports or industry analyses.",
        height=100,
        key="market_info"
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        tam = st.number_input("Total Addressable Market (TAM) in $M*", min_value=0.0, value=0.0, step=1.0)
    with col2:
        sam = st.number_input("Serviceable Addressable Market (SAM) in $M", min_value=0.0, value=0.0, step=1.0)
    with col3:
        som = st.number_input("Serviceable Obtainable Market (SOM) in $M", min_value=0.0, value=0.0, step=1.0)
    
    market_doc = st.file_uploader(
        "Upload market research document",
        type=['pdf', 'docx', 'txt'],
        key="market_doc"
    )
    
    # Business Model
    st.markdown("#### Business Model")
    business_model_desc = st.text_area(
        "How will you generate revenue? How will you achieve profitability?*",
        placeholder="Describe revenue streams, pricing strategy, path to profitability...",
        height=100,
        key="business_model_desc"
    )
    
    col1, col2 = st.columns(2)
    with col1:
        revenue_model = st.selectbox("Primary Revenue Model*", [
            "Subscription (SaaS)", "Transaction Fee", "Marketplace", "Advertising",
            "Direct Sales", "Freemium", "License", "Usage-based", "Commission",
            "Product Sales", "Service Fees", "Other"
        ])
    with col2:
        pricing_model = st.text_input("Pricing Strategy", placeholder="e.g., $99/month per user")
    
    # Uniqueness & Competitive Advantage
    st.markdown("#### Uniqueness & Competitive Advantage")
    uniqueness = st.text_area(
        "What makes your business different? What is your competitive advantage?*",
        placeholder="Describe your unique value proposition, moat, and competitive advantages...",
        height=100,
        key="uniqueness"
    )
    
    ip_assets = st.text_area(
        "What intellectual property does the company own?",
        placeholder="Patents, trademarks, trade secrets, proprietary technology...",
        height=80,
        key="ip_assets"
    )
    
    # Progress & Milestones
    st.markdown("#### Progress & Milestones")
    progress = st.text_area(
        "What progress has been made? What key goals have been accomplished?*",
        placeholder="List major milestones, achievements, and current traction...",
        height=100,
        key="progress"
    )
    
    business_plan_doc = st.file_uploader(
        "Upload business plan or pitch deck",
        type=['pdf', 'docx', 'txt'],
        key="business_plan_doc"
    )
    
    # Section 2: About the Team
    st.markdown("---")
    st.subheader("2️⃣ About the Team")
    
    # Team Experience
    st.markdown("#### Team Experience & Structure")
    team_experience = st.text_area(
        "Why is your team the best choice to execute this venture?*",
        placeholder="Describe relevant experience, track record, and expertise...",
        height=100,
        key="team_experience"
    )
    
    team_structure = st.text_area(
        "How are responsibilities divided? Who leads key areas?*",
        placeholder="CEO: [Name] - [Responsibilities]\nCTO: [Name] - [Responsibilities]...",
        height=100,
        key="team_structure"
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        team_size = st.number_input("Current Team Size", min_value=1, value=1)
    with col2:
        technical_team = st.number_input("Technical Team Members", min_value=0, value=0)
    with col3:
        advisors_count = st.number_input("Number of Advisors", min_value=0, value=0)
    
    # Team Dynamics & Hiring
    team_dynamics = st.text_area(
        "What is the team's experience with this specific product/market?",
        placeholder="Describe relevant domain expertise and past successes...",
        height=80,
        key="team_dynamics"
    )
    
    hiring_strategy = st.text_area(
        "How will you attract and retain top talent?",
        placeholder="Describe hiring plans, compensation strategy, culture...",
        height=80,
        key="hiring_strategy"
    )
    
    team_doc = st.file_uploader(
        "Upload team bios or organizational chart",
        type=['pdf', 'docx', 'txt'],
        key="team_doc"
    )
    
    # Section 3: About the Financials
    st.markdown("---")
    st.subheader("3️⃣ About the Financials")
    
    # Funding Information
    st.markdown("#### Funding & Use of Funds")
    col1, col2 = st.columns(2)
    with col1:
        funding_raised = st.number_input("Total Funding Raised to Date ($)", min_value=0.0, value=0.0, step=10000.0)
        funding_seeking = st.number_input("Current Funding Seeking ($)*", min_value=0.0, value=0.0, step=10000.0)
    with col2:
        funding_type = st.selectbox("Funding Type", [
            "Pre-Seed", "Seed", "Series A", "Series B", "Series C+", 
            "Bridge", "Convertible Note", "SAFE", "Revenue-based"
        ])
        valuation = st.number_input("Pre-money Valuation ($)", min_value=0.0, value=0.0, step=100000.0)
    
    use_of_funds = st.text_area(
        "How will the funding be used?*",
        placeholder="Product Development: 40%\nSales & Marketing: 30%\nTeam Expansion: 20%\nOperations: 10%",
        height=100,
        key="use_of_funds"
    )
    
    # Financial Metrics
    st.markdown("#### Key Financial Metrics")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        current_mrr = st.number_input("Current MRR ($)", min_value=0.0, value=0.0, step=100.0)
        arr = st.number_input("Current ARR ($)", min_value=0.0, value=0.0, step=1000.0)
    with col2:
        burn_rate = st.number_input("Monthly Burn Rate ($)*", min_value=0.0, value=0.0, step=1000.0)
        runway_months = st.number_input("Current Runway (months)*", min_value=0, value=0, step=1)
    with col3:
        gross_margin = st.slider("Gross Margin (%)", 0, 100, 50)
        operating_margin = st.slider("Operating Margin (%)", -100, 100, -50)
    with col4:
        cac = st.number_input("Customer Acquisition Cost ($)*", min_value=0.0, value=0.0, step=10.0)
        ltv = st.number_input("Customer Lifetime Value ($)*", min_value=0.0, value=0.0, step=10.0)
    
    # Revenue & Profitability
    st.markdown("#### Revenue Model & Path to Profitability")
    revenue_streams = st.text_area(
        "Describe all revenue streams and their contribution",
        placeholder="Primary: Subscription (70%)\nSecondary: Professional Services (20%)\nOther: Training (10%)",
        height=80,
        key="revenue_streams"
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        revenue_projection_1y = st.number_input("Revenue Projection Year 1 ($)", min_value=0.0, value=0.0)
    with col2:
        revenue_projection_3y = st.number_input("Revenue Projection Year 3 ($)", min_value=0.0, value=0.0)
    with col3:
        profitability_timeline = st.text_input("Expected Time to Profitability", placeholder="e.g., 24 months")
    
    financial_doc = st.file_uploader(
        "Upload financial projections or P&L",
        type=['pdf', 'docx', 'txt', 'xlsx'],
        key="financial_doc"
    )
    
    # Section 4: About Market and Competition
    st.markdown("---")
    st.subheader("4️⃣ About the Market and Competition")
    
    # Competition Analysis
    st.markdown("#### Competition Analysis")
    competitors = st.text_area(
        "Who are your competitors? What are their strengths and weaknesses?*",
        placeholder="Competitor 1: [Name] - Strengths: [list], Weaknesses: [list]\nCompetitor 2: ...",
        height=120,
        key="competitors"
    )
    
    competitive_advantage = st.text_area(
        "What gives you a sustainable competitive advantage?*",
        placeholder="Technology moat, network effects, brand, cost structure, team expertise...",
        height=80,
        key="competitive_advantage"
    )
    
    # Market Dynamics
    st.markdown("#### Market Growth & Customer Acquisition")
    market_growth = st.text_area(
        "How fast is the market growing? What are the key trends?",
        placeholder="Market growing at X% CAGR, driven by trends like...",
        height=80,
        key="market_growth"
    )
    
    customer_acquisition = st.text_area(
        "How will you acquire customers? What channels will you use?*",
        placeholder="Describe customer acquisition strategy, channels, and unit economics...",
        height=100,
        key="customer_acquisition"
    )
    
    col1, col2, col3 = st.columns(3)
    with col1:
        current_customers = st.number_input("Current Customer Count", min_value=0, value=0)
    with col2:
        monthly_growth_rate = st.number_input("Monthly Growth Rate (%)", min_value=0.0, value=0.0, step=1.0)
    with col3:
        churn_rate = st.number_input("Monthly Churn Rate (%)", min_value=0.0, value=0.0, step=0.1)
    
    competitive_analysis_doc = st.file_uploader(
        "Upload competitive analysis document",
        type=['pdf', 'docx', 'txt'],
        key="competitive_doc"
    )
    
    # Section 5: Other Important Areas
    st.markdown("---")
    st.subheader("5️⃣ Risk Factors & Strategic Planning")
    
    # Risks
    st.markdown("#### Risk Assessment")
    legal_risks = st.text_area(
        "What potential legal risks do you foresee?",
        placeholder="IP disputes, contract risks, compliance issues...",
        height=80,
        key="legal_risks"
    )
    
    regulatory_risks = st.text_area(
        "What regulatory hurdles might you face?",
        placeholder="Industry regulations, licensing requirements, compliance costs...",
        height=80,
        key="regulatory_risks"
    )
    
    other_risks = st.text_area(
        "Other key risk factors and mitigation strategies*",
        placeholder="Market risks, technology risks, execution risks, and how you'll address them...",
        height=100,
        key="other_risks"
    )
    
    # Exit Strategy
    st.markdown("#### Exit Strategy")
    exit_strategy = st.text_area(
        "How do you envision exiting the business?",
        placeholder="Potential acquirers, IPO timeline, strategic partnerships...",
        height=80,
        key="exit_strategy"
    )
    
    # Additional Documents
    st.markdown("#### Additional Documents")
    additional_doc = st.file_uploader(
        "Upload any additional supporting documents",
        type=['pdf', 'docx', 'txt'],
        key="additional_doc",
        help="Legal documents, contracts, letters of intent, etc."
    )
    
    # Submit button
    submitted = st.form_submit_button("🔍 Analyze Proposal", use_container_width=True)

# Process form submission
if submitted:
    try:
        # Show URL processing notice
        url_fields_to_check = ['problem_solution', 'market_info', 'business_model_desc', 
                              'uniqueness', 'progress', 'team_experience', 'competitors',
                              'competitive_advantage', 'customer_acquisition']
        
        # Collect all form data
        form_data = {
            # Basic Info
            'company_name': company_name,
            'founding_year': founding_year,
            'website': website,
            'industry': industry,
            'stage': stage,
            'location': location,
            
            # Business & Product
            'problem_solution': problem_solution,
            'market_info': market_info,
            'tam': tam,
            'sam': sam,
            'som': som,
            'business_model_desc': business_model_desc,
            'revenue_model': revenue_model,
            'pricing_model': pricing_model,
            'uniqueness': uniqueness,
            'ip_assets': ip_assets,
            'progress': progress,
            
            # Team
            'team_experience': team_experience,
            'team_structure': team_structure,
            'team_size': team_size,
            'technical_team': technical_team,
            'advisors_count': advisors_count,
            'team_dynamics': team_dynamics,
            'hiring_strategy': hiring_strategy,
            
            # Financials
            'funding_raised': funding_raised,
            'funding_seeking': funding_seeking,
            'funding_type': funding_type,
            'valuation': valuation,
            'use_of_funds': use_of_funds,
            'current_mrr': current_mrr,
            'arr': arr,
            'burn_rate': burn_rate,
            'runway_months': runway_months,
            'gross_margin': gross_margin,
            'operating_margin': operating_margin,
            'cac': cac,
            'ltv': ltv,
            'revenue_streams': revenue_streams,
            'revenue_projection_1y': revenue_projection_1y,
            'revenue_projection_3y': revenue_projection_3y,
            'profitability_timeline': profitability_timeline,
            
            # Market & Competition
            'competitors': competitors,
            'competitive_advantage': competitive_advantage,
            'market_growth': market_growth,
            'customer_acquisition': customer_acquisition,
            'current_customers': current_customers,
            'monthly_growth_rate': monthly_growth_rate,
            'churn_rate': churn_rate,
            
            # Risks & Strategy
            'legal_risks': legal_risks,
            'regulatory_risks': regulatory_risks,
            'other_risks': other_risks,
            'exit_strategy': exit_strategy
        }
        
        # Check and process URLs in text fields (Pro mode only)
        if st.session_state.mode == "Pro":
            try:
                with st.expander("📎 URL Content Detection", expanded=False):
                    st.info("Pro mode can fetch content from URLs in your responses. Processing...")
                    
                    urls_found = False
                    for field in url_fields_to_check:
                        if field in form_data and form_data[field]:
                            if is_valid_url(form_data[field]):
                                urls_found = True
                                original_content = form_data[field]
                                enhanced_content = process_text_with_urls(original_content)
                                form_data[field] = enhanced_content
                                
                                # Show what URLs were processed
                                urls = extract_urls_from_text(original_content)
                                st.success(f"✓ Fetched content from {len(urls)} URL(s) in {field.replace('_', ' ').title()}")
                    
                    if not urls_found:
                        st.info("No URLs detected in text fields.")
            except Exception as e:
                st.warning("⚠️ URL content fetching encountered an issue. Proceeding with manual input only.")
        
        # Process uploaded documents
        uploaded_docs = {}
        doc_mapping = {
            'problem_doc': problem_doc,
            'market_doc': market_doc,
            'business_plan_doc': business_plan_doc,
            'team_doc': team_doc,
            'financial_doc': financial_doc,
            'competitive_doc': competitive_analysis_doc,
            'additional_doc': additional_doc
        }
        
        for doc_name, doc_file in doc_mapping.items():
            if doc_file is not None:
                uploaded_docs[doc_name] = process_uploaded_file(doc_file)
        
        form_data['uploaded_docs'] = uploaded_docs
        
        # Validation
        required_fields = ['company_name', 'problem_solution', 'market_info', 'business_model_desc',
                          'uniqueness', 'team_experience', 'team_structure', 'funding_seeking',
                          'use_of_funds', 'cac', 'ltv', 'burn_rate', 'runway_months',
                          'competitors', 'competitive_advantage', 'customer_acquisition', 'other_risks']
        
        missing_fields = [field for field in required_fields if not form_data.get(field)]
        
        if missing_fields:
            st.error(f"Please fill in all required fields: {', '.join(missing_fields)}")
        else:
            # Calculate metrics
            st.markdown("---")
            st.header("📊 Comprehensive Analysis Results")
            
            metrics = calculate_comprehensive_metrics(form_data)
            
            # Display key metrics dashboard
            st.subheader("🎯 Key Performance Indicators")
            
            col1, col2, col3, col4, col5, col6 = st.columns(6)
            
            with col1:
                st.metric("LTV/CAC Ratio", f"{metrics['ltv_cac_ratio']:.2f}", 
                         "✅ Good" if metrics['ltv_cac_ratio'] >= 3 else "⚠️ Needs Work")
            
            with col2:
                st.metric("Efficiency Score", f"{metrics['efficiency_score']:.0f}/100")
            
            with col3:
                st.metric("Growth Score", f"{metrics['growth_score']:.0f}/100")
            
            with col4:
                st.metric("Market Score", f"{metrics['market_score']:.0f}/100")
            
            with col5:
                st.metric("Team Score", f"{metrics['team_score']:.0f}/100")
            
            with col6:
                st.metric("Traction Score", f"{metrics['traction_score']:.0f}/100")
            
            # Overall Investment Score
            st.markdown("### 🏆 Overall Investment Score")
            
            score_color = "green" if metrics['overall_score'] >= 70 else "orange" if metrics['overall_score'] >= 50 else "red"
            
            fig_gauge = go.Figure(go.Indicator(
                mode = "gauge+number+delta",
                value = metrics['overall_score'],
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "Investment Readiness Score", 'font': {'size': 24}},
                delta = {'reference': 70, 'increasing': {'color': "green"}},
                gauge = {
                    'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
                    'bar': {'color': score_color},
                    'bgcolor': "white",
                    'borderwidth': 2,
                    'bordercolor': "gray",
                    'steps': [
                        {'range': [0, 50], 'color': 'rgba(255, 0, 0, 0.1)'},
                        {'range': [50, 70], 'color': 'rgba(255, 255, 0, 0.1)'},
                        {'range': [70, 100], 'color': 'rgba(0, 255, 0, 0.1)'}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            
            fig_gauge.update_layout(height=400, font={'size': 16})
            st.plotly_chart(fig_gauge, use_container_width=True)
            
            # Detailed Analysis Sections
            col1, col2 = st.columns(2)
            
            with col1:
                # Financial Analysis
                st.markdown("### 💰 Financial Analysis")
                
                financial_metrics = {
                    'Metric': ['LTV/CAC Ratio', 'Burn Multiple', 'Runway', 'Gross Margin', 'Monthly Growth', 'Churn Rate'],
                    'Value': [
                        f"{metrics['ltv_cac_ratio']:.2f}",
                        f"{metrics['burn_multiple']:.2f}" if metrics['burn_multiple'] != float('inf') else "N/A",
                        f"{form_data['runway_months']} months",
                        f"{form_data['gross_margin']}%",
                        f"{form_data['monthly_growth_rate']}%",
                        f"{form_data['churn_rate']}%"
                    ],
                    'Benchmark': ['≥ 3.0', '≤ 2.0', '≥ 18 months', '≥ 70%', '≥ 10%', '≤ 5%'],
                    'Status': [
                        '✅' if metrics['ltv_cac_ratio'] >= 3 else '❌',
                        '✅' if metrics['burn_multiple'] <= 2 else '❌',
                        '✅' if form_data['runway_months'] >= 18 else '❌',
                        '✅' if form_data['gross_margin'] >= 70 else '❌',
                        '✅' if form_data['monthly_growth_rate'] >= 10 else '❌',
                        '✅' if form_data['churn_rate'] <= 5 else '❌'
                    ]
                }
                
                financial_df = pd.DataFrame(financial_metrics)
                st.dataframe(financial_df, use_container_width=True, hide_index=True)
                
                # Revenue Projections
                st.markdown("### 📈 Revenue Trajectory")
                
                years = ['Current', 'Year 1', 'Year 2', 'Year 3']
                revenues = [
                    form_data['arr'],
                    form_data['revenue_projection_1y'],
                    form_data['revenue_projection_1y'] * 2.5,  # Estimated
                    form_data['revenue_projection_3y']
                ]
                
                fig_revenue = go.Figure()
                fig_revenue.add_trace(go.Scatter(
                    x=years,
                    y=revenues,
                    mode='lines+markers',
                    name='Revenue',
                    line=dict(color='blue', width=3),
                    marker=dict(size=10)
                ))
                
                # Add annotations
                for i, (year, revenue) in enumerate(zip(years, revenues)):
                    fig_revenue.add_annotation(
                        x=year,
                        y=revenue,
                        text=f"${revenue/1000000:.1f}M",
                        showarrow=True,
                        arrowhead=2,
                        arrowsize=1,
                        arrowwidth=2,
                        arrowcolor="gray",
                        ax=0,
                        ay=-40
                    )
                
                fig_revenue.update_layout(
                    title="Revenue Growth Projection",
                    xaxis_title="Timeline",
                    yaxis_title="Revenue ($)",
                    showlegend=False,
                    height=400,
                    hovermode='x unified'
                )
                
                st.plotly_chart(fig_revenue, use_container_width=True)
            
            with col2:
                # Market Analysis
                st.markdown("### 🌍 Market Opportunity")
                
                market_data = {
                    'Market Segment': ['TAM', 'SAM', 'SOM', 'Current Capture'],
                    'Value ($M)': [
                        form_data['tam'],
                        form_data['sam'] if form_data['sam'] > 0 else form_data['tam'] * 0.1,
                        form_data['som'] if form_data['som'] > 0 else form_data['tam'] * 0.01,
                        form_data['arr'] / 1000000
                    ]
                }
                
                fig_market = go.Figure(data=[
                    go.Bar(
                        x=market_data['Market Segment'],
                        y=market_data['Value ($M)'],
                        text=[f"${v:.0f}M" for v in market_data['Value ($M)']],
                        textposition='auto',
                        marker_color=['lightblue', 'blue', 'darkblue', 'green']
                    )
                ])
                
                fig_market.update_layout(
                    title="Market Size Analysis",
                    xaxis_title="Market Segment",
                    yaxis_title="Market Size ($M)",
                    showlegend=False,
                    height=400
                )
                
                st.plotly_chart(fig_market, use_container_width=True)
                
                # Competitive Positioning
                st.markdown("### 🎯 Competitive Positioning")
                
                # Simple competitive matrix
                comp_factors = ['Product Features', 'Market Share', 'Team Strength', 'Funding', 'Technology']
                company_scores = [85, 20, metrics['team_score'], 60, 80]  # Example scores
                industry_avg = [70, 50, 60, 65, 70]
                
                fig_spider = go.Figure()
                
                fig_spider.add_trace(go.Scatterpolar(
                    r=company_scores,
                    theta=comp_factors,
                    fill='toself',
                    name=form_data['company_name']
                ))
                
                fig_spider.add_trace(go.Scatterpolar(
                    r=industry_avg,
                    theta=comp_factors,
                    fill='toself',
                    name='Industry Average'
                ))
                
                fig_spider.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100]
                        )),
                    showlegend=True,
                    height=400
                )
                
                st.plotly_chart(fig_spider, use_container_width=True)
            
            # Pro Mode AI Insights
            ai_insights = {}  # Initialize ai_insights
            if st.session_state.mode == "Pro" and st.session_state.api_key:
                st.markdown("---")
                st.markdown("## 🤖 AI-Powered Investment Analysis")
                
                with st.spinner("Generating comprehensive AI insights..."):
                    try:
                        ai_insights = generate_ai_insights(form_data, st.session_state.api_key)
                        
                        if "error" in ai_insights:
                            st.error(f"⚠️ {ai_insights['error']}")
                            ai_insights = {}  # Reset to empty dict
                        else:
                            # Investment Recommendation
                            col1, col2 = st.columns([2, 1])
                            with col1:
                                st.markdown("### 📋 Investment Thesis")
                                st.info(ai_insights.get('investment_thesis', 'No thesis generated'))
                            with col2:
                                st.markdown("### 🎯 Recommendation")
                                rec = ai_insights.get('investment_recommendation', 'HOLD')
                                rec_color = {"STRONG BUY": "🟢", "BUY": "🟢", "HOLD": "🟡", "PASS": "🔴"}.get(rec.split()[0], "⚪")
                                st.markdown(f"# {rec_color} {rec.split()[0]}")
                            
                            # Detailed Analysis
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                st.markdown("### ✅ Key Strengths")
                                strengths = ai_insights.get('key_strengths', [])
                                for strength in strengths:
                                    st.markdown(f"• {strength}")
                                
                                st.markdown("### 📊 Growth Potential")
                                st.write(clean_markdown(ai_insights.get('growth_potential', 'No assessment available')))
                                
                                st.markdown("### 👥 Team Assessment")
                                st.write(clean_markdown(ai_insights.get('team_assessment', 'No assessment available')))
                            
                            with col2:
                                st.markdown("### ⚠️ Key Concerns")
                                concerns = ai_insights.get('key_concerns', [])
                                for concern in concerns:
                                    st.markdown(f"• {concern}")
                                
                                st.markdown("### 🎯 Competitive Position")
                                st.write(clean_markdown(ai_insights.get('competitive_position', 'No assessment available')))
                                
                                st.markdown("### ⏰ Market Timing")
                                st.write(ai_insights.get('market_timing', 'No assessment available'))
                            
                            # Due Diligence & Next Steps
                            st.markdown("### 🔍 Due Diligence Priorities")
                            dd_priorities = ai_insights.get('due_diligence_priorities', [])
                            cols = st.columns(len(dd_priorities) if dd_priorities else 1)
                            for i, priority in enumerate(dd_priorities):
                                with cols[i]:
                                    st.info(f"**Priority {i+1}:**\n{priority}")
                            
                            # Investment Terms
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.markdown("### 💰 Valuation Assessment")# Remove markdown formatting from the text
                                st.text(ai_insights.get('valuation_assessment', 'No assessment available'))
                            
                            with col2:
                                st.markdown("### 📜 Recommended Terms")
                                st.write(clean_markdown(ai_insights.get('recommended_terms', 'No recommendations available')))
                            
                            with col3:
                                st.markdown("### 🤝 Post-Investment Support")
                                support_areas = ai_insights.get('post_investment_support', [])
                                for area in support_areas:
                                    st.markdown(f"• {area}")
                            
                            # Risk Assessment
                            st.markdown("### ⚠️ Risk Assessment")
                            risk_level = ai_insights.get('risk_assessment', 'MEDIUM')
                            risk_color = {"LOW": "success", "MEDIUM": "warning", "HIGH": "error"}.get(risk_level.split()[0], "info")
                            st.write(risk_level)
                            
                            # Comparable Exits
                            st.markdown("### 🚀 Comparable Exits")
                            st.info(ai_insights.get('comparable_exits', 'No comparable data available'))
                            
                    except Exception as e:
                        st.error("⚠️ Unable to generate AI insights. Please check your API key and try again.")
                        ai_insights = {}
                        # Log error for debugging (optional)
                        print(f"AI Error: {str(e)}")
            
            # Recommendations Section (for both modes)
            st.markdown("---")
            st.markdown("## 💡 Action Items & Recommendations")
            
            recommendations = []
            
            # Financial recommendations
            if metrics['ltv_cac_ratio'] < 3:
                recommendations.append({
                    'area': 'Unit Economics',
                    'issue': f"LTV/CAC ratio is {metrics['ltv_cac_ratio']:.1f} (below 3.0 benchmark)",
                    'action': "Focus on improving customer retention and reducing acquisition costs"
                })
            
            if form_data['runway_months'] < 18:
                recommendations.append({
                    'area': 'Financial Health',
                    'issue': f"Runway is only {form_data['runway_months']} months",
                    'action': "Extend runway to 18-24 months through fundraising or burn reduction"
                })
            
            if form_data['gross_margin'] < 70:
                recommendations.append({
                    'area': 'Business Model',
                    'issue': f"Gross margin is {form_data['gross_margin']}% (below SaaS benchmark)",
                    'action': "Optimize pricing strategy and reduce COGS to improve margins"
                })
            
            if form_data['monthly_growth_rate'] < 10:
                recommendations.append({
                    'area': 'Growth',
                    'issue': f"Monthly growth rate is {form_data['monthly_growth_rate']}%",
                    'action': "Accelerate growth through improved sales/marketing efficiency"
                })
            
            if form_data['churn_rate'] > 5:
                recommendations.append({
                    'area': 'Customer Retention',
                    'issue': f"Monthly churn rate is {form_data['churn_rate']}%",
                    'action': "Implement customer success initiatives to reduce churn below 5%"
                })
            
            if not recommendations:
                st.success("🎉 Congratulations! Your metrics are strong across all key areas. Focus on execution and scaling.")
            else:
                for rec in recommendations:
                    with st.expander(f"🔧 {rec['area']}: {rec['issue']}"):
                        st.write(f"**Recommended Action:** {rec['action']}")
            
            # Export Report
            st.markdown("---")
            st.markdown("### 📥 Export Analysis Report")
            
            # Generate PDF report
            with st.spinner("Generating PDF report..."):
                try:
                    pdf_data = generate_pdf_report(
                        form_data=form_data,
                        metrics=metrics,
                        ai_insights=ai_insights if st.session_state.mode == "Pro" and "error" not in ai_insights else None,
                        recommendations=recommendations
                    )
                    
                    st.download_button(
                        label="📄 Download Professional PDF Report",
                        data=pdf_data,
                        file_name=f"investment_analysis_{form_data['company_name']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                        mime="application/pdf",
                        help="Download a comprehensive PDF report with all analysis, metrics, and recommendations"
                    )
                    
                except Exception as e:
                    st.warning("⚠️ PDF generation encountered an issue. You can download the text version below.")
                    
                    # Fallback to text report
                    report_date = datetime.now().strftime('%Y-%m-%d %H:%M')
                    
                    report = f"""
# INVESTMENT ANALYSIS REPORT
# {form_data['company_name']}
Generated: {report_date}

## EXECUTIVE SUMMARY
Overall Investment Score: {metrics['overall_score']:.0f}/100
Stage: {form_data['stage']}
Industry: {form_data['industry']}
Funding Seeking: ${form_data['funding_seeking']:,.0f}

## KEY METRICS SUMMARY
- LTV/CAC Ratio: {metrics['ltv_cac_ratio']:.2f}
- Monthly Growth Rate: {form_data['monthly_growth_rate']}%
- Burn Rate: ${form_data['burn_rate']:,.0f}/month
- Runway: {form_data['runway_months']} months
- Gross Margin: {form_data['gross_margin']}%
- ARR: ${form_data['arr']:,.0f}

## MARKET OPPORTUNITY
- TAM: ${form_data['tam']}M
- SAM: ${form_data['sam']}M
- SOM: ${form_data['som']}M

## SCORE BREAKDOWN
- Efficiency Score: {metrics['efficiency_score']:.0f}/100
- Growth Score: {metrics['growth_score']:.0f}/100
- Market Score: {metrics['market_score']:.0f}/100
- Team Score: {metrics['team_score']:.0f}/100
- Traction Score: {metrics['traction_score']:.0f}/100
- Risk Score: {metrics['risk_score']:.0f}/100

## KEY RECOMMENDATIONS
"""
                    for rec in recommendations:
                        report += f"\n### {rec['area']}\n"
                        report += f"- Issue: {rec['issue']}\n"
                        report += f"- Action: {rec['action']}\n"
                    
                    if st.session_state.mode == "Pro" and "error" not in ai_insights:
                        report += f"\n## AI INVESTMENT THESIS\n{ai_insights.get('investment_thesis', 'N/A')}\n"
                        report += f"\n## AI RECOMMENDATION\n{ai_insights.get('investment_recommendation', 'N/A')}\n"
                    
                    st.download_button(
                        label="📥 Download Text Report (Fallback)",
                        data=report,
                        file_name=f"investment_analysis_{form_data['company_name']}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                        mime="text/plain"
                    )
                    
    except Exception as e:
        st.error("⚠️ An unexpected error occurred while processing your submission. Please try again.")
        print(f"Form processing error: {str(e)}")  # For debugging


st.markdown("---")
st.markdown("""
**Contact & Connect**  
📧 Email: [iartzi@sensym.ai](mailto:iartzi@sensym.ai)  
🌐 Website: [www.sensym.ai](https://www.sensym.ai)  
💼 LinkedIn: [Connect with me](https://www.linkedin.com/in/isacartzi/)
""")
st.markdown("""
**Disclaimer**  
This tool is for informational purposes only and should not be used as a substitute for professional advice. SenSym, LLC does not provide investment advice or recommendations. The information provided is based on publicly available data and may not reflect the latest developments in the market. SenSym, LLC is not responsible for any losses incurred by users of this tool. Users should conduct their own due diligence before making any investment decisions. SenSym, LLC reserves the right to modify or discontinue this tool at any time without notice. SenSym, LLC is not responsible for any damages or losses arising from the use of this tool.
""")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>Built for entrepreneurs and investors to make data-driven decisions</p>
        <p>© 2025 - All Rights Reserved</p> SenSym, LLC</p>
        <p style='font-size: 12px;'>This tool provides guidance only. Always conduct thorough due diligence.</p>
    </div>
    """,
    unsafe_allow_html=True
)