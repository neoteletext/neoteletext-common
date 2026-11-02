#!/usr/bin/env bash
# neoteletext-common's one check script, on the gate machinery it keeps for
# every repository (gates.md): the original in gates/, not a copy, and its
# hooks are gates/ itself (git config core.hooksPath gates).
#   scripts/check.sh commit   the machinery's own test, on what is staged
#   scripts/check.sh push     the same
#   scripts/check.sh full     the same
set -euo pipefail
cd "$(dirname "$0")/.."

# What the gates read.
readonly CHECKED_PATHS=(gates scripts)
# A review dated 24 October 2026, as it was read then.
readonly DELETED_DOCUMENT_HISTORY=(reviews/2026-10-24-security/A4-adversarial-input-review.md)

. gates/gate.sh

commit_steps() {
    step "the machinery's own test"
    gates/test
}

gate_main "$@"
