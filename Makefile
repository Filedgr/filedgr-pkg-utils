PROJECT_NAME = filedgr_pkg_utils
DATE    ?= $(shell date +%FT%T%z)
MIN = 70

.PHONY: bumpver package upload-package test-coverage generate-badges lint clean help

# Helper to check if a CLI tool exists; if not, install its pip package.
define require_cmd
	@command -v $(1) >/dev/null 2>&1 || { echo "Installing $(2)..."; pip install $(2); }
endef

# Helper to check if a Python module exists; if not, install its pip package.
define require_module
	@python -c "import $(1)" 2>/dev/null || { echo "Installing $(2)..."; pip install $(2); }
endef

########## PACKAGING ##########
bumpver: ## Bump the python package version, use PARAM=(--patch, --minor, --major) to define with step to use.
	$(call require_cmd,bumpver,bumpver)
	@bumpver update $(PARAM)

package: ## Build the package
	$(call require_module,build,build)
	@python -m build

upload-package: ## Upload the package using twine
	$(call require_cmd,twine,twine)
	@twine upload --repository codeartifact dist/*

########## TESTING & BADGES ##########
test-coverage: ## Runs the coverage tests for the python package
	$(call require_module,pytest,pytest)
	@python -c "import pytest_cov" 2>/dev/null || pip install -r requirements-test.txt
	@pytest tests --cov=src/filedgr_pkg_utils --cov-fail-under=${MIN} --cov-report term-missing

generate-badges: test-coverage ## Run tests and generate an SVG coverage badge
	$(call require_cmd,coverage-badge,coverage-badge)
	@coverage-badge -o coverage.svg -f
	@echo "Coverage badge generated at coverage.svg"

########## UTILITIES ##########
lint: ## Lint the codebase
	$(call require_cmd,flake8,flake8)
	@flake8 src

clean: ## Cleans the workspace
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf dist
	rm -f .coverage
	rm -rf */*.egg-info
	rm -f coverage.svg

help: ## Show the help
	@echo ""
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@awk 'BEGIN {FS=":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
