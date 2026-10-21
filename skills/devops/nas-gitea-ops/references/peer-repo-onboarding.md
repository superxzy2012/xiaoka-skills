# Onboarding a peer's existing repo onto the bus repo

A peer says "push 待授权 / `Permission denied (publickey)`" and asks you to grant something. Two
independent faults produce that sentence, and granting a key fixes only one of them.

## 1. Is the key registered at all?

```bash
sudo -n docker exec -u git gitea sqlite3 /data/gitea/gitea.db \
  "SELECT id,key_id,repo_id,name,fingerprint,mode FROM deploy_key;"
sudo -n docker exec -u git gitea sqlite3 /data/gitea/gitea.db \
  "SELECT id,owner_id,name,fingerprint FROM public_key;"
```

An empty `deploy_key` table plus a `public_key` list that does not contain the peer's fingerprint
means the key was **never added** — nothing to "authorize". The failure text is identical to a key
added read-only, so check the table before changing any permission.

Register it as a user key (there is no `gitea admin` subcommand for this):

```bash
TOK=$(gitea admin user generate-access-token --username anc --token-name "tmp-$(date +%s)" --raw)
curl -s -X POST http://localhost:3000/api/v1/user/keys \
  -H "Authorization: token $TOK" -H 'Content-Type: application/json' \
  -d '{"title":"<peer-key-name>","key":"ssh-ed25519 AAAA… <comment>","read_only":false}'
sqlite3 /data/gitea/gitea.db "DELETE FROM access_token WHERE name='tmp-…';"
```

A **deploy key** is per-repo and read-only by default; a **user key** carries the user's repo
permissions. For a peer that should push to one bus repo, user key + collaborator write is simpler
and shows up correctly in commit attribution.

## 2. Does the local repo share history with the remote?

```bash
cd <peer-repo>; git remote -v            # empty remote = it was never wired up
GIT_SSH_COMMAND="ssh -i <peer-key> -o StrictHostKeyChecking=no -p 2222" git fetch origin
git merge-base master origin/main        # no output = unrelated histories
```

Unrelated histories are the normal case when the peer built its repo standalone and only later was
told to use the bus. **Do not force-push** — it destroys the shared branch for everyone else.
Realign instead:

```bash
git format-patch -3 master -o /tmp/patches        # keep the peer's original commits recoverable
git branch -m master master-orphan-backup         # never delete their work
git checkout -b master origin/main
git checkout master-orphan-backup -- <file1> <file2>
mkdir -p A2A && git mv <file1> A2A/               # bus layout, not repo root
```

Stage only files that do not collide. When a name exists on both sides, diff them and keep the
remote one if it is newer — then tell the peer which of their files was superseded and why, in the
receipt. Silently overwriting a peer's file to make your push clean is the one unrecoverable mistake
in this procedure.

## 3. Push with the peer's own key and attribution

```bash
export GIT_SSH_COMMAND="ssh -i <peer-key> -o StrictHostKeyChecking=no -p 2222"
git -C <peer-repo> config user.name "<peer display name>"
git -C <peer-repo> config user.email "<peer>@<domain>"
git -C <peer-repo> push origin master:main
```

Their local branch is often `master` while the remote default is `main`; use the refspec rather than
renaming. Commit as them and say in the receipt that you only performed the merge — the peer's
`DONE` claim keeps its own hash story, and a peer that later checks `git log --author` should see
themselves.

## 4. Prove it, then sync the other side

`git ls-remote origin refs/heads/main` must equal local `HEAD`. On the receiving machine (e.g. this
NAS worktree) the incoming files may already exist as untracked copies from an earlier transfer:
compare `md5sum` against `git show <remote>:<path> | md5sum`, delete only the identical ones, then
merge. If they differ, stop and look — a differing copy is content, not clutter.

After merging, run `git status --short` in the worktree. A stale local edit to a file the peer also
touched (e.g. an older copy of a shared doc) shows up as `M` and will ride along in the next commit;
`git checkout -- <path>` restores the remote version before you push anything.
