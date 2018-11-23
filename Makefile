TESTIMONY_TOKENS="bz, caseautomation, casecomponent, caseimportance, caselevel, caseposneg, expectedresults, id, requirement, setup, subtype1, steps, testtype, upstream"
TESTIMONY_MINIMUM_TOKENS="id, requirement, caseautomation, caselevel, casecomponent, testtype, caseimportance, upstream"
TESTIMONY_OPTIONS=--tokens=$(TESTIMONY_TOKENS) --minimum-tokens=$(TESTIMONY_MINIMUM_TOKENS)

# Commands --------------------------------------------------------------------

help:
	@echo "Please use \`make <target>' where <target> is one of"
	@echo "  pyc-clean                  to delete all temporary artifacts"
	@echo "  can-i-push?                to check if local changes are suitable to push"
	@echo "  install-commit-hook        to install pre-commit hook to check if changes are suitable to push"
	@echo "  gitflake8                  to check flake8 styling only for modified files"
	@echo "  lint                       to check code style"
	@echo "  test-docstrings            to check minimum required test docstrings"


pyc-clean: ## remove Python file artifacts
	$(info "Removing unused Python compiled files, caches and ~ backups...")
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

gitflake8:
	$(info "Checking style and syntax errors with flake8 linter...")
	@which flake8 >> /dev/null || pip install flake8
	@flake8 $(shell git diff --name-only) --show-source upgrade upgrade_tests

can-i-push?: gitflake8
	$(info "!!! Congratulations your changes are good to fly, make a great PR! ${USER}++ !!!")

install-commit-hook:
	$(info "Installing git pre-commit hook...")
	@touch .git/hooks/pre-commit
	@grep -q '^make can-i-push?' .git/hooks/pre-commit || echo "make can-i-push?" >> .git/hooks/pre-commit

lint:
	flake8 --max-line-length=99 upgrade upgrade_tests

test-docstrings:
	testimony $(TESTIMONY_OPTIONS) validate upgrade_tests


# Special Targets -------------------------------------------------------------

.PHONY: help docs docs-clean pyc-clean can-i-push? install-commit-hook gitflake8
