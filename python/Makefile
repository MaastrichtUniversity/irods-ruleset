# Makefile to build and install the iRODS ruleset
#
#   make - combine rules and copy it to the "/etc/irods" dir
#

# Input files.

RULE_FILES = $(wildcard *.py)
# Filter out core.py to be able to position it first during the concatenation
FILTER := $(filter-out core.py,$(RULE_FILES))

# Output files.

RULESET_NAME = core.py
RULES_DEST ?= /etc/irods
RULESET_FILE := $(RULES_DEST)/$(RULESET_NAME)

# Make targets.

all: $(RULESET_FILE)


$(RULESET_FILE): $(FILTER)
    # Concatenate all *.py with core.py on the first position
	cat core.py $(FILTER) > $(RULESET_FILE)

