# Temporarily append security mitigations to the main iRODS rulebase.

RULE_FILE = mitigations.r
RULES_DEST ?= /etc/irods
RULESET_FILE := $(RULES_DEST)/core.re
BEGIN_MARKER = \# BEGIN temporary iRODS security mitigations

all: install

install:
	@test -f "$(RULESET_FILE)" || { \
		echo "$(RULESET_FILE) does not exist" >&2; \
		exit 1; \
	}
	@if grep -Fqx '$(BEGIN_MARKER)' "$(RULESET_FILE)"; then \
		echo "Mitigations are already present in $(RULESET_FILE)"; \
	else \
		{ printf '\n'; cat "$(RULE_FILE)"; } >> "$(RULESET_FILE)" && \
		echo "Appended mitigations to $(RULESET_FILE)"; \
	fi

.PHONY: all install
