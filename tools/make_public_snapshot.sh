#!/bin/sh
# Build a fresh, single-commit public snapshot of HEAD in DEST.
#
# Usage: tools/make_public_snapshot.sh DEST [WORDLIST]
#
# WORDLIST defaults to ${PUMP_WORDLIST:-<repo root>/../CentrifugalPump-data/wordlist.txt}.
# The snapshot is leak-scanned before anything is committed.  Nothing is pushed.
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
    echo "usage: $0 DEST [WORDLIST]" >&2
    exit 2
fi

root=$(git rev-parse --show-toplevel)
dest=$1
wordlist=${2:-${PUMP_WORDLIST:-$root/../CentrifugalPump-data/wordlist.txt}}

if [ ! -f "$wordlist" ]; then
    echo "snapshot: word list not found: $wordlist" >&2
    exit 2
fi

if [ -e "$dest" ]; then
    if [ ! -d "$dest" ] || [ -n "$(ls -A "$dest")" ]; then
        echo "snapshot: DEST must not exist or be an empty directory: $dest" >&2
        exit 2
    fi
fi

if [ -n "$(git -C "$root" status --porcelain --untracked-files=no)" ]; then
    echo "snapshot: warning: uncommitted changes are NOT included (snapshot is of HEAD)" >&2
fi

mkdir -p "$dest"
git -C "$root" archive --format=tar HEAD | tar -x -C "$dest"

if ! "${PYTHON:-python3}" "$root/tools/leak_scan.py" --words "$wordlist" "$dest"; then
    echo "snapshot: confidential words found; nothing committed" >&2
    case "$dest" in
        "" | "/" | "." | "..") ;;
        *) rm -rf -- "$dest" ;;
    esac
    exit 1
fi

name=${GIT_AUTHOR_NAME:-$(git -C "$root" config user.name)}
email=${GIT_AUTHOR_EMAIL:-$(git -C "$root" config user.email)}

(
    cd "$dest"
    git init -q -b main
    git add -A
    git -c user.name="$name" -c user.email="$email" -c commit.gpgsign=false \
        commit -q -m "Initial public release"
    sh tools/install_hooks.sh
)

cat <<MSG
snapshot: created $dest with a single commit.
Next steps (nothing was pushed):
  1. Create the public repository on GitHub.
  2. git -C "$dest" remote add origin <url>
  3. git -C "$dest" push -u origin main
MSG
