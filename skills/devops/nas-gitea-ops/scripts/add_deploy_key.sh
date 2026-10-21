#!/bin/sh
# Attach a peer's SSH public key as a repo-scoped Write deploy key on the NAS Gitea.
#
# Runs INSIDE the gitea container (it needs the `gitea` CLI and the sqlite DB):
#
#   printf '%s\n' "ssh-ed25519 AAAA... peer@node" | \
#     ssh DY@192.168.199.2 \
#       'sudo -n docker exec -u git -i gitea sh /tmp/add_deploy_key.sh anc/a2a-bus peer-node'
#
# Key arrives on STDIN (never argv — argv is visible in `ps`).
# Mints its own short-lived admin token and deletes it before exiting.
# Prints an end-state assertion so a partial failure cannot pass as success.
set -e

REPO=${1:?usage: add_deploy_key.sh <owner>/<repo> <title>}
TITLE=${2:-deploy-key}
ADMIN=${GITEA_ADMIN:-anc}
CFG=/data/gitea/conf/app.ini
DB=/data/gitea/gitea.db

read -r PUB
case "$PUB" in
  ssh-ed25519\ *|ssh-rsa\ *|ecdsa-sha2-*) : ;;
  *) echo "ERR: stdin is not an SSH public key (expected 'ssh-ed25519 AAAA... comment')"; exit 2 ;;
esac

case "$PUB" in
  *'"'*|*'\\'*) echo "ERR: public key contains quote/backslash, cannot build JSON safely"; exit 2 ;;
esac

echo "PUB_LEN=${#PUB}  TITLE=$TITLE  REPO=$REPO"

# deploy_key has id,key_id,repo_id,name,fingerprint,mode,created_unix,updated_unix.
# public_key has owner_id/read_only instead — do not copy column names between the two.
BEFORE=$(sqlite3 "$DB" 'SELECT count(*) FROM deploy_key;')
TOKENS_BEFORE=$(sqlite3 "$DB" 'SELECT count(*) FROM access_token;')
echo "deploy_key rows before=$BEFORE  access_token before=$TOKENS_BEFORE"

TNAME="tmp-dk-$(date +%s)-$$"
TOK=$(/usr/local/bin/gitea admin user generate-access-token --username "$ADMIN" \
        --token-name "$TNAME" --raw --config "$CFG" 2>/dev/null | tail -1)
if [ -z "$TOK" ]; then echo "ERR: could not mint admin token"; exit 3; fi

BODY=$(printf '{"title":"%s","key":"%s","read_only":false}' "$TITLE" "$PUB")
HTTP=$(curl -s -o /tmp/dk.json -w '%{http_code}' -X POST \
  "http://localhost:3000/api/v1/repos/$REPO/keys" \
  -H "Authorization: token $TOK" -H 'Content-Type: application/json' -d "$BODY")
echo "POST keys -> HTTP $HTTP"
head -c 300 /tmp/dk.json; echo ""

# always drop the token, even on the failure path
sqlite3 "$DB" "DELETE FROM access_token WHERE name='$TNAME';"

if [ "$HTTP" != "201" ]; then
  echo "FAIL: deploy key not created"
  echo "access_token after=$(sqlite3 "$DB" 'SELECT count(*) FROM access_token;') (expected $TOKENS_BEFORE)"
  exit 4
fi

sqlite3 -header "$DB" "SELECT id,key_id,repo_id,name,mode,fingerprint FROM deploy_key WHERE name='$TITLE';"
KID=$(sqlite3 "$DB" "SELECT max(id) FROM deploy_key WHERE name='$TITLE';")
echo "DEPLOY_KEY_ID=$KID  (DELETE /api/v1/repos/$REPO/keys/$KID takes this id, not key_id)"

# --- end-state assertions -------------------------------------------------
AFTER=$(sqlite3 "$DB" 'SELECT count(*) FROM deploy_key;')
TOKENS_AFTER=$(sqlite3 "$DB" 'SELECT count(*) FROM access_token;')
echo "deploy_key rows after=$AFTER (expected $((BEFORE + 1)))  access_token after=$TOKENS_AFTER (expected $TOKENS_BEFORE)"
[ "$AFTER" = "$((BEFORE + 1))" ] || { echo "WARN: deploy_key count off — a previous aborted run may have left a key"; exit 5; }
[ "$TOKENS_AFTER" = "$TOKENS_BEFORE" ] || { echo "WARN: token table not restored"; exit 6; }
echo "OK: key attached. Peer clones with:"
echo "  GIT_SSH_COMMAND='ssh -i ~/.ssh/id_ed25519_gitea -o StrictHostKeyChecking=no -p 2222' git clone ssh://git@<host>:2222/$REPO.git"
