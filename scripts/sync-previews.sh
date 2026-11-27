#!/bin/bash
# Copy unlisted preview pages from sibling project repos into public/preview/<slug>/.
#
# A preview is a finished interactive page that is published but not linked
# anywhere on the site (no post, no feed, no index entry) and carries
# <meta name="robots" content="noindex">, so the owner can check it before it
# becomes a real post. The page is GENERATED in the project repo; never
# hand-edit public/preview — regenerate there and run this script.
set -euo pipefail
cd "$(dirname "$0")/.."

sync_page() { # repo-dir-name  source-file  slug
  local repo="$1" src="$2" slug="$3"
  local from="../$repo/$src"
  if [ ! -f "$from" ]; then
    echo "skip $slug (no $repo/$src — is the repo checked out alongside this one?)"
    return
  fi
  mkdir -p "public/preview/$slug"
  {
    printf '%s\n' '<!doctype html>' '<html lang="en">' '<head>' \
      '<meta charset="utf-8">' \
      '<meta name="viewport" content="width=device-width, initial-scale=1">' \
      '<meta name="robots" content="noindex, nofollow">'
    # The source is a page fragment: <title>, <meta>, <link>, <style>, then the body.
    cat "$from"
    printf '%s\n' '</html>'
  } > "public/preview/$slug/index.html"
  echo "synced $slug from $repo/$src"
}

sync_page glyphbits docs/explainer/index.html how-small-can-writing-get

echo "done — previews are at /preview/<slug>/ and are not linked from the site"
