# 🚀 Investor Proposal Vetting Tool

A comprehensive Streamlit application that helps investors and entrepreneurs evaluate startup proposals through data-driven analysis and AI-powered insights.

![Python](https://img.shields.io/badge/python-v3.8+-blue.svg)
![Streamlit](https://img.shields.io/badge/streamlit-1.28+-red.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## 📋 Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Demo](#demo)
- [Installation](#installation)
- [Usage](#usage)
- [Deployment](#deployment)
- [Technology Stack](#technology-stack)
- [Privacy & Security](#privacy--security)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

The Investor Proposal Vetting Tool is designed to streamline the investment evaluation process by providing:
- **Quantitative analysis** of key startup metrics
- **AI-powered insights** for deeper understanding
- **Professional PDF reports** for documentation
- **Privacy-focused** design with no data retention

The tool operates in two modes:
- **Light Mode**: Pure data analytics without AI
- **Pro Mode**: Enhanced with OpenAI GPT integration for comprehensive analysis

## ✨ Features

### Core Functionality
- 📊 **Comprehensive Scoring System**: Evaluates startups across 6 key dimensions
- 📈 **Financial Analysis**: LTV/CAC ratios, burn rate, runway calculations
- 🌍 **Market Opportunity Assessment**: TAM/SAM/SOM analysis with visualizations
- 👥 **Team Evaluation**: Experience, structure, and capability scoring
- 📉 **Risk Assessment**: Financial health and operational risk analysis

### Pro Mode Features (AI-Enhanced)
- 🤖 **AI Investment Thesis**: GPT-generated executive summaries
- 💡 **Smart Recommendations**: Actionable insights and next steps
- 🔗 **URL Content Analysis**: Automatically fetches and analyzes linked content
- 📊 **Competitive Intelligence**: AI-powered market positioning analysis

### Document Processing
- 📄 **Multi-format Support**: Upload PDF, DOCX, TXT files
- 🌐 **URL Content Fetching**: Analyze pitch decks and websites directly
- 📑 **Professional PDF Reports**: Download comprehensive analysis reports

### Visualizations
- Interactive Plotly charts
- Investment readiness gauge
- Revenue projections
- Market opportunity waterfall
- Competitive positioning radar charts

## 🖥️ Demo

### Light Mode
Perfect for quick assessments using pure data analytics:
- No API key required
- Instant quantitative analysis
- Basic scoring and recommendations

### Pro Mode
Enhanced with AI for deeper insights:
- Requires OpenAI API key
- Natural language analysis
- Investment recommendations
- Due diligence priorities

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment (recommended)

### Setup Instructions

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/investor-vetting-tool.git
cd investor-vetting-tool
```

2. **Create a virtual environment**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Mac/Linux
python3 -m venv venv
source venv/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the application**
```bash
streamlit run app.py
```

The app will open in your default browser at `http://localhost:8501`

### Requirements.txt
```txt
streamlit
pandas
numpy
plotly
openai>=1.0.0
pypdf
python-docx
reportlab
requests
beautifulsoup4
```

## 📖 Usage

### Getting Started

1. **Select Analysis Mode**
   - Choose between Light (no AI) or Pro (AI-enhanced) mode
   - For Pro mode, enter your OpenAI API key

2. **Complete the Questionnaire**
   - Fill in company information
   - Provide business details
   - Enter financial metrics
   - Describe market and competition
   - Outline risks and strategy

3. **Upload Supporting Documents** (Optional)
   - Upload pitch decks, business plans, financial projections
   - In Pro mode, paste URLs to online resources

4. **Analyze and Export**
   - Review comprehensive scoring and analysis
   - Download professional PDF report

### Questionnaire Sections

1. **About the Business & Product**
   - Problem/Solution fit
   - Market size and evolution
   - Business model and revenue streams
   - Competitive advantages
   - Progress and milestones

2. **About the Team**
   - Experience and track record
   - Organizational structure
   - Domain expertise
   - Hiring strategy

3. **About the Financials**
   - Funding requirements
   - Unit economics (CAC, LTV)
   - Burn rate and runway
   - Revenue projections
   - Path to profitability

4. **About Market and Competition**
   - Competitive analysis
   - Market growth trends
   - Customer acquisition strategy
   - Market positioning

5. **Risk Factors & Strategic Planning**
   - Legal and regulatory risks
   - Risk mitigation strategies
   - Exit strategy

## 🚀 Deployment

### Streamlit Cloud Deployment

1. **Prepare your repository**
   - Ensure `app.py` and `requirements.txt` are in the root directory
   - Push to GitHub

2. **Deploy on Streamlit Cloud**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Select the branch and main file path
   - Click "Deploy"

3. **Configuration**
   - No secrets or environment variables needed
   - Users provide their own OpenAI API keys

### Local Deployment Options

**Using Docker:**
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
EXPOSE 8501
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Using Heroku:**
Create a `setup.sh`:
```bash
mkdir -p ~/.streamlit/
echo "\
[server]\n\
headless = true\n\
port = $PORT\n\
enableCORS = false\n\
\n\
" > ~/.streamlit/config.toml
```

And `Procfile`:
```
web: sh setup.sh && streamlit run app.py
```

## 🔧 Technology Stack

- **Frontend**: Streamlit
- **Data Processing**: Pandas, NumPy
- **Visualizations**: Plotly
- **AI Integration**: OpenAI GPT-3.5/4
- **PDF Generation**: ReportLab
- **Document Processing**: pypdf, python-docx
- **Web Scraping**: BeautifulSoup4, Requests

## 🔒 Privacy & Security

### Data Protection
- ✅ No user data is stored on servers
- ✅ All processing happens in real-time
- ✅ Session data is cleared after use
- ✅ API keys are never logged or stored

### Security Best Practices
- Users provide their own API keys
- HTTPS encryption for all communications
- No database or persistent storage
- Regular security updates

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guide
- Add docstrings to new functions
- Update README for new features
- Test thoroughly before submitting PR

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Streamlit team for the amazing framework
- OpenAI for GPT API
- All contributors and users

## 📞 Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Contact: [your-email@example.com]

---

**Disclaimer**: This tool is for informational purposes only and should not be used as the sole basis for investment decisions. Always conduct thorough due diligence and consult with qualified professionals before making investment choices.