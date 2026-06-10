#!/usr/bin/env bash
# One-command installer for the HubSpot Companion Claude Code skill.
#
#   Remote (no clone needed):
#     curl -fsSL https://raw.githubusercontent.com/GustavoGomezPG/hubspot-companion-skill/main/install.sh | bash
#
#   Local (from a clone):
#     ./install.sh
#
# Installs into ~/.claude/skills/hubspot-companion (personal, all projects).
# Pass a different target dir as the first arg, e.g.:
#     ./install.sh /path/to/project/.claude/skills/hubspot-companion
set -euo pipefail

REPO="https://github.com/GustavoGomezPG/hubspot-companion-skill.git"
DEST="${1:-$HOME/.claude/skills/hubspot-companion}"

echo "==> HubSpot Companion installer"
echo "    target: $DEST"

# 1. install or update the skill folder
if [ -d "$DEST/.git" ]; then
  echo "==> already installed — updating (git pull)"
  git -C "$DEST" pull --ff-only
else
  echo "==> cloning skill"
  mkdir -p "$(dirname "$DEST")"
  git clone --depth 1 "$REPO" "$DEST"
fi

cd "$DEST"

# 2. set up the .env (never overwrite an existing real key)
[ -f .env ] || cp .env.example .env

needs_key() { ! [ -f .env ] || grep -q "your-service-key-here" .env; }

if [ -n "${HUBSPOT_SERVICE_KEY:-}" ]; then
  printf 'HUBSPOT_SERVICE_KEY=%s\n' "$HUBSPOT_SERVICE_KEY" > .env
  echo "==> used HUBSPOT_SERVICE_KEY from your environment"
elif needs_key && [ -t 0 ]; then
  echo
  echo "==> Paste your HubSpot Service Key (input hidden), or press Enter to add it later:"
  read -rs KEY || KEY=""
  echo
  if [ -n "${KEY:-}" ]; then
    printf 'HUBSPOT_SERVICE_KEY=%s\n' "$KEY" > .env
    echo "==> saved key to $DEST/.env"
  fi
fi

# 3. validate (if a key is present and python3 is available)
if command -v python3 >/dev/null 2>&1 && ! needs_key; then
  echo "==> validating key..."
  python3 scripts/hs_client.py validate || echo "    (validation failed — check the key/scopes)"
else
  echo "==> no key set yet — add it to $DEST/.env, then run:  python3 $DEST/scripts/hs_client.py validate"
fi

cat <<EOF

==> Installed as a plain skill at: $DEST

    NEXT: restart Claude Code, then type  /hubspot-companion
    (Claude Code only picks up a brand-new skills directory on restart. If ~/.claude/skills
     already existed, the skill is live now — no restart needed.)

    Need a key? HubSpot > Settings > Account Management > Integrations > Service Keys
    > Create service key > add scopes:  content  hubdb  files  > copy it into $DEST/.env
EOF
