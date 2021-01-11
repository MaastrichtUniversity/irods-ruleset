# Makefile to build and install the iRODS ruleset
#
#   make - combine rules and copy it to the "/etc/irods" dir
#

# Input files.

RULE_FILES = $(wildcard *.py)

# Output files.

RULESET_NAME = core.py
RULES_DEST ?= /etc/irods
RULESET_FILE := $(RULES_DEST)/$(RULESET_NAME)

# Make targets.

all: $(RULESET_FILE)

$(RULESET_FILE): $(RULE_FILES)
	cat $(RULE_FILES) > $(RULESET_FILE)

