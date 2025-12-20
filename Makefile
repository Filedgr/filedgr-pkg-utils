PROJECT_NAME = filedgr_pkg_utils
DATE    ?= $(shell date +%FT%T%z)
MIN = 40

.PHONY: bumpver help

########## PACKAGING ##########
bumpver: ## Bump the python package version, use PARAM=(--patch, --minor, --major) to define with step to use.
	@pip install bumpver
	@bumpver update $(PARAM)

package:
	@pip install build
	@python -m build

upload-package:
	@pip install twine
	@twine upload --repository codeartifact dist/*

########## TESTING ##########
test-coverage: ## Runs the coverage tests for the python package
	@pip install -r requirements-test.txt
	@pytest tests --cov=src/filedgr_pkg_utils --cov-fail-under=${MIN} --cov-report term-missing


########## UTILITIES ##########
lint:
	@pip install flake8
	flake8 src

clean: ## Cleans the workspace
	rm -rf .mypy_cache
	rm -rf .pytest_cache
	rm -rf dist
	rm -f .coverage
	rm -rf */*.egg-info

help: ## Show the help
	@echo ""
	@echo "usage: make <target>"
	@echo ""
	@echo "targets:"
	@awk 'BEGIN {FS=":.*##"} /^[a-zA-Z0-9_-]+:.*##/ {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
