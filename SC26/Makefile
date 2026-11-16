SHELL := /bin/sh

SC26_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
DEMO_DIR := $(SC26_DIR)/tutorial_demo/opencode_e2e
RUN_DIR := $(DEMO_DIR)/runs/opencode_latest

.PHONY: clean help

help:
	@printf '%s\n' \
		'SC26 Beyond Code Pairs hands-on' \
		'' \
		'  make clean  Remove generated run artifacts so the exercise can be rerun'

clean:
	@test -f "$(SC26_DIR)/SC26_START_HERE.md"
	@test -f "$(DEMO_DIR)/harness.py"
	@rm -rf -- \
		"$(RUN_DIR)" \
		"$(DEMO_DIR)/__pycache__" \
		"$(DEMO_DIR)/tests/__pycache__" \
		"$(DEMO_DIR)/.pytest_cache"
	@printf '%s\n' \
		'Cleaned generated Beyond Code Pairs run artifacts.' \
		'Source code, fixtures, tests, .opencode configuration, and this Makefile were preserved.'
