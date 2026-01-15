# 🤖 GovGPT UAE Government Chatbot - Self-Healing UI Automation Framework

[![Allure Report](https://img.shields.io/badge/📊_Allure-Report-green?logo=qameta)](https://namangupt5.github.io/GovtGPT_UI/)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?logo=python)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Latest-45ba4b?logo=playwright)](https://playwright.dev)

A self-adapting UI automation framework for validating UAE Government chatbot (GovGPT) responses using **local AI/ML libraries only** (no paid APIs).

## 🎯 Features

- ✅ **BDD + Cucumber** - Behavior-driven testing with Gherkin syntax
- ✅ **Strict Page Object Model** - Clean separation of concerns
- ✅ **Excel-Driven Testing** - All prompts from Excel (single source of truth)
- ✅ **Self-Healing Locators** - Auto-adapts to UI changes
- ✅ **Local AI Validation** - Uses free, offline ML libraries
- ✅ **Allure Reporting** - Rich test reports with step-level attachments
- ✅ **CI/CD Ready** - GitHub Actions with auto-published reports

## 📋 Test Coverage

| Risk Level | Scenarios | Validation Type |
|------------|-----------|-----------------|
| 🔴 High Risk | HR-01 to HR-14 | Safety, Injection Detection, PII Check |
| 🟠 Medium Risk | MR-01 to MR-04 | Relevance, Grammar, Groundedness |
| 🟢 Low Risk | LR-01 to LR-02 | Semantic Consistency, Clarity |

## 🏗️ Project Structure

```
UAsk/
├── features/                    # BDD Feature Files
│   ├── chatbot_validation.feature
│   ├── environment.py          # Test hooks & setup
│   └── steps/
│       └── chatbot_steps.py    # Step definitions
├── pages/                       # Page Object Model
│   ├── base_page.py
│   ├── login_page.py
│   └── chat_page.py
├── validators/                  # AI Validation (Local Only)
│   ├── safety_validator.py     # Detoxify, injection detection
│   ├── relevance_validator.py  # Sentence-transformers
│   ├── grammar_validator.py    # Textstat
│   └── semantic_validator.py   # Multilingual embeddings
├── utils/
│   ├── excel_reader.py         # Excel prompt loader
│   ├── config_loader.py        # YAML config
│   ├── self_healing_locator.py # Dynamic locator discovery
│   └── audit_logger.py         # Audit trail
├── data/
│   └── uae_gov_chatbot_prompts.xlsx  # Test prompts
├── config/
│   └── config.yaml             # Framework configuration
├── reports/
│   ├── allure-results/         # Allure JSON results
│   ├── allure-report/          # Generated HTML report
│   └── screenshots/            # Test screenshots
└── .github/
    └── workflows/
        └── ci.yml              # CI/CD Pipeline with Allure
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Allure CLI (for local report viewing)

### Installation

```bash
# Clone repository
git clone https://github.com/YOUR_ORG/UAsk.git
cd UAsk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### Configuration

Create a `.env` file:

```env
# Application Credentials
UASK_USERNAME=your_username@dge.gov.ae
UASK_PASSWORD=your_password
UASK_BASE_URL=https://govgpt.sandbox.dge.gov.ae/

# Test Settings
TEST_ENV=staging
HEADLESS_MODE=false
```

### Running Tests

```bash
# Using test runner (recommended)
python run_tests.py run                    # Run all tests
python run_tests.py run --tags @high-risk  # Run high-risk tests
python run_tests.py run --tags @LR-01      # Run single scenario
python run_tests.py high-risk              # Shortcut for high-risk
python run_tests.py low-risk               # Shortcut for low-risk

# Direct behave commands
behave                                     # Run all tests
behave --tags @high-risk                   # Run by risk level
behave --tags @HR-01                       # Run single scenario

# Run in headless mode (CI/CD)
HEADLESS_MODE=true behave
```

### Generate Allure Report

```bash
# Using test runner (recommended)
python run_tests.py report-gen    # Generate static HTML report
python run_tests.py report-open   # Open report in browser
python run_tests.py report        # Serve with live reload

# Using Allure CLI
brew install allure               # Install on macOS
allure serve reports/allure-results
```

## 📊 Allure Report Features

Step-level attachments for detailed test analysis:

| Step | Attachments |
|------|-------------|
| Navigate to App | 🌐 Application URL |
| Login | 🔐 Login Credentials |
| Send Prompt | 📝 Excel Prompt Data (ID, Risk, Intent, Text) |
| Capture Response | 🤖 AI Response, 📊 Response Data (JSON) |
| Safety Validation | 🛡️ Validation Result + Summary |
| Relevance Validation | 🎯 Validation Result + Summary |
| Grammar Validation | 📝 Validation Result + Summary |
| Semantic Validation | 🔗 Validation Result + Summary |
| On Failure | ❌ Failure Screenshot |


## 🔧 Validators

### Safety Validator (High-Risk)
- **Detoxify** - Toxicity detection 
- **Sentence-Transformers** - ML-based injection detection using semantic similarity
- **PII detection** - Emirates ID, phone, email patterns

### Relevance Validator (Medium-Risk)
- **Sentence-Transformers** - Semantic similarity
- **Keyword coverage** - Topic alignment
- **Length evaluation** - Response completeness

### Grammar Validator (Medium-Risk)
- **Textstat** - Readability scores (Flesch-Kincaid)
- **Structure analysis** - Sentence completeness

### Semantic Validator (Low-Risk)
- **Multilingual embeddings** - Cross-lingual similarity
- **Coherence analysis** - Internal consistency

## 🔄 CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) provides:

### Features
1. **Static Analysis**: Ruff linter for code quality & security checks
2. **Triggers**: Push to main/develop, Pull Requests, Manual dispatch
3. **Environment**: Ubuntu with Python 3.11, Playwright (headless)
4. **Tests**: Runs Behave scenarios with Allure formatter
5. **History**: Preserves test trends across runs
6. **Reports**: Auto-deploys to GitHub Pages
7. **Summary**: Test results in GitHub Actions UI

### Static Analysis (Ruff)

Run locally before committing:
```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix

# Check formatting
ruff format --check .
```

### GitHub Secrets Required

| Secret | Description |
|--------|-------------|
| `UASK_USERNAME` | Application username |
| `UASK_PASSWORD` | Application password |
| `UASK_BASE_URL` | Application URL |


### Run Tests Manually

1. Go to **Actions** tab in GitHub
2. Select **CI - GovGPT Tests** workflow
3. Click **Run workflow**
4. (Optional) Enter tags like `@high-risk` or `@LR-01`
5. Click **Run workflow**

### Artifacts

Each CI run uploads:
- `allure-results` - Raw JSON results (30 days)
- `allure-report` - HTML report (30 days)
- `allure-history` - Test history for trends (90 days)
- `screenshots` - Failure screenshots (14 days)

## 🛡️ Non-Negotiable Constraints

- ✅ **Prompts from Excel only** (no hardcoding)
- ✅ **Strict POM** (no locators in steps)
- ✅ **Self-healing locators** (adapts to UI changes)

## 📁 Excel Test Data

The `data/uae_gov_chatbot_prompts.xlsx` file contains:

| Column | Description |
|--------|-------------|
| ID | Unique identifier (HR-01, MR-01, LR-01) |
| Prompt (EN) | English prompt text |
| Expected Intent | Expected behavior category |
| Risk Level | High, Medium, or Low |
| Multi-turn | Whether prompt is part of conversation |

## 🔍 Self-Healing Locators

The framework discovers locators dynamically:

```python
# Priority order
1. Role-based (ARIA)
2. Text-based
3. Placeholder
4. Label
5. TestID
6. CSS (fallback)
7. XPath (last resort)
```

Discovered locators are cached in `logs/discovered_locators.json`.

## 🐛 Debugging

```bash
# Run with verbose logging
behave --no-capture --logging-level=DEBUG

# Run single scenario in headed mode
HEADLESS_MODE=false behave --tags @LR-01

# Verify framework setup
python run_tests.py verify
```

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

**Built for UAE Government Digital Excellence** 🇦🇪
