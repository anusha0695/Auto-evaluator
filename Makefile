# ============================================================
#  Agentic Evaluation Pipeline — Makefile
# ============================================================

PYTHON       := python3
VENV         := venv_new
PIP          := $(VENV)/bin/pip
PYTEST       := $(VENV)/bin/pytest
JUPYTER      := $(VENV)/bin/jupyter

# Default PDF for quick runs (override with: make classify PDF=data/input/raw_documents/doc2_6.pdf)
PDF          ?= data/input/raw_documents/doc2_1.pdf
OUTPUT       ?= output/classification_result.json

.DEFAULT_GOAL := help

# ── Help ─────────────────────────────────────────────────────
.PHONY: help
help:
	@echo ""
	@echo "  Agentic Evaluation Pipeline"
	@echo "  ─────────────────────────────────────────────────"
	@echo "  Setup"
	@echo "    make install          Install Python dependencies"
	@echo "    make env              Copy .env.example → .env (edit before use)"
	@echo ""
	@echo "  Classification"
	@echo "    make classify         Run full pipeline on default PDF ($(PDF))"
	@echo "    make classify PDF=<path>  Run on a specific PDF"
	@echo "    make classify-dual    Run dual-prompt comparison classification"
	@echo ""
	@echo "  SME Review"
	@echo "    make sme-notebook     Launch SME review Jupyter notebook"
	@echo "    make sme-list         List pending SME review packets"
	@echo ""
	@echo "  Testing"
	@echo "    make test             Run all unit tests"
	@echo "    make test-unit        Run fast unit tests only (no LLM calls)"
	@echo "    make test-agents      Run verification agent tests"
	@echo "    make test-e2e         Run end-to-end pipeline test"
	@echo "    make test-sme         Run SME interface tests"
	@echo "    make test-cov         Run tests with coverage report"
	@echo ""
	@echo "  Utilities"
	@echo "    make clean-output     Remove generated output files"
	@echo "    make clean-cache      Remove Python cache and .pytest_cache"
	@echo "    make clean            clean-output + clean-cache"
	@echo "    make validate         Validate Phase 6 architecture"
	@echo "    make debug-docai      Run Document AI debug script"
	@echo "  ─────────────────────────────────────────────────"
	@echo ""

# ── Setup ────────────────────────────────────────────────────
.PHONY: venv
venv:
	@if [ ! -d "$(VENV)" ]; then \
		echo "🐍 Creating virtual environment: $(VENV)..."; \
		$(PYTHON) -m venv $(VENV); \
		echo "✅ Virtual environment created."; \
	else \
		echo "✅ Virtual environment $(VENV) already exists."; \
	fi

.PHONY: install
install: venv
	@echo "📦 Installing dependencies into $(VENV)..."
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✅ Done. Activate with: source $(VENV)/bin/activate"

.PHONY: env
env:
	@if [ -f .env ]; then \
		echo "⚠️  .env already exists — skipping. Edit it manually."; \
	else \
		cp .env.example .env; \
		echo "✅ Created .env from .env.example. Fill in your API keys before running."; \
	fi

# ── Classification ───────────────────────────────────────────
.PHONY: classify
classify:
	@echo "🔬 Running full classification pipeline on: $(PDF)"
	$(PYTHON) run_classification.py $(PDF) --output $(OUTPUT)

.PHONY: classify-dual
classify-dual:
	@echo "🔬 Running dual-prompt comparison classification on: $(PDF)"
	$(PYTHON) run_dual_classification.py $(PDF)

# ── SME Review ───────────────────────────────────────────────
.PHONY: sme-notebook
sme-notebook:
	@echo "📓 Launching SME Review notebook..."
	$(JUPYTER) notebook notebooks/sme_review_interface.ipynb

.PHONY: sme-list
sme-list:
	@echo "📋 Pending SME review packets:"
	@$(PYTHON) -c "\
from src.evaluation.review_helper import SMEReviewHelper; \
h = SMEReviewHelper(); \
packets = h.list_pending_reviews(); \
[print(f'  • {p[\"doc_id\"]} — {p[\"total_issues\"]} issue(s)') for p in packets] \
if packets else print('  No pending reviews.')"

# ── Testing ──────────────────────────────────────────────────
.PHONY: test
test:
	@echo "🧪 Running all tests..."
	$(PYTEST)

.PHONY: test-unit
test-unit:
	@echo "🧪 Running unit tests (no LLM calls)..."
	$(PYTEST) -m "not llm and not integration and not slow"

.PHONY: test-agents
test-agents:
	@echo "🧪 Running verification agent tests..."
	$(PYTEST) test_verification_agents.py -v

.PHONY: test-e2e
test-e2e:
	@echo "🧪 Running end-to-end auto-retry test..."
	$(PYTEST) test_e2e_autoretry.py -v

.PHONY: test-sme
test-sme:
	@echo "🧪 Running SME interface tests..."
	$(PYTEST) test_sme_interface.py -v

.PHONY: test-cov
test-cov:
	@echo "🧪 Running tests with coverage..."
	$(PYTEST) --cov=src --cov-report=term-missing --cov-report=html:output/coverage
	@echo "📊 HTML coverage report: output/coverage/index.html"

# ── Utilities ────────────────────────────────────────────────
.PHONY: validate
validate:
	@echo "✅ Validating Phase 6 architecture..."
	$(PYTHON) validate_phase6_architecture.py

.PHONY: debug-docai
debug-docai:
	@echo "🔍 Running Document AI debug script..."
	$(PYTHON) debug_layout_parser.py

.PHONY: clean-output
clean-output:
	@echo "🗑️  Removing generated output files..."
	rm -rf output/classification_result.json \
	       output/document_bundles \
	       output/sme_packets \
	       output/ground_truth \
	       output/agent_outputs
	@echo "✅ Output cleaned."

.PHONY: clean-cache
clean-cache:
	@echo "🗑️  Removing Python cache files..."
	find . -type d -name "__pycache__" -not -path "./venv*" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -not -path "./venv*" -delete 2>/dev/null || true
	rm -rf .pytest_cache
	@echo "✅ Cache cleaned."

.PHONY: clean
clean: clean-output clean-cache
