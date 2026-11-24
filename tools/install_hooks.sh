#!/bin/sh
# Enable the repository's git hooks (leak guard) for this clone.
set -eu

cd "$(git rev-parse --show-toplevel)"
git config core.hooksPath tools/hooks
chmod +x tools/hooks/pre-push
echo "Hooks enabled (core.hooksPath=tools/hooks). Word list expected at ../CentrifugalPump-data/wordlist.txt or \$PUMP_WORDLIST."
