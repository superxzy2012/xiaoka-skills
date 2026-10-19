# Writing into host-owned directories from inside the Hermes container

The Hermes container runs as `hermes` (uid 10000) and sees the NAS filesystem through a
bind mount. A large part of that mount belongs to other uids, so "the path exists and I can
read it" says nothing about writing. This file is the measured map, how to re-derive it, and
the recipe that lands a file anyway.

## The map — re-derive it, never quote it

| container path | owner (uid:gid) | mode | writable as hermes |
|---|---|---|---|
| `/opt/data` (home, scratch, memories, skills) | 10000:10000 | — | ✅ |
| `/opt/nas/volume2/2-AI/skills` | 1000:uucp | 777 | ✅ |
| `/opt/nas/volume2/2-AI/A2A/{inbox,outbox,processed,tasks,results}` | 1005:10 | 755 | ❌ Permission denied |
| `/opt/nas/volume2/2-AI/obsidian_vault` | 1005:10 (+ACL) | 755 | ❌ Permission denied |

Re-derive in three commands; the third is the only one that is evidence:

```bash
id                       # 10000:10000 — not in the NAS owner groups
ls -nd <dir>             # numeric owner + mode; group *names* (uucp vs admin) differ per host
ls -l <dir> | head -3     # existing files' owner tells you what to chown back to
touch <dir>/.wtest 2>/dev/null && { echo writable; rm -f <dir>/.wtest; } || echo NOT-writable
```

`755` + owner 1005 or 1000 = read-only for the container. Do not carry a previous session's
conclusion forward: directories get re-permissioned, and a stored "writable" claim is how a
turn gets spent on a `PermissionError` halfway through.

## The recipe: stage locally → land as root → hand ownership back

1. **Build the artifact under `/opt/data` first** (write_file, or a small python script). Never
   try to author it directly at the destination — a partial write into a shared drop directory
   is worse than no write, because peers poll it.
2. **Push to the host's `/tmp` over ssh**, base64-piped (`scp`/`sftp` are limited on this host,
   and `ssh host 'cmd'` does not forward your stdin):

   ```python
   subprocess.run(["ssh","-o","BatchMode=yes","-o","StrictHostKeyChecking=no",
                   "-i","/opt/data/.ssh/id_ed25519","-o","ConnectTimeout=8",
                   "DY@192.168.199.2",
                   "rm -rf /tmp/stage && mkdir -p /tmp/stage && base64 -d > /tmp/stage/<name>"],
                  input=base64.b64encode(payload), capture_output=True)
   ```

3. **Land it with a root container that mounts the host directory**, chowning back in the same
   step:

   ```sh
   sudo -n docker run --rm -v /volume2/2-AI/A2A/outbox:/o -v /tmp/stage:/p alpine \
     sh -c "cp /p/<name> /o/<name> && chown 1005:10 /o/<name> && chmod 644 /o/<name>"
   ```

   - Mount the **directory**, never a single file: a bind-mounted file cannot be replaced, and
     `docker cp` onto one fails with `device or resource busy`.
   - **chown back to the parent directory's numeric owner** (from `ls -nd`). A file left as
     `root:root` is unreadable-as-owner for the host-side app or sync bridge, which then cannot
     move or rewrite it — you have created a new blocker while removing one.
   - Same recipe works for `docker exec` into an existing container when the target path is
     already mounted there.
4. **Verify by reading the file back through the mount path from inside the container**, then
   assert content and `ls -l` owner. `PUSH_OK` on stdout is a statement about the code path, not
   about the disk.
5. **Clean the staging dir** (`rm -rf /tmp/stage` in the same ssh call that landed it, or right
   after).

## The trap that makes this expensive

Inside the root container, a host path that is **not mounted** still accepts writes — they land
in the container's writable layer and disappear with `--rm`, while `cp`, `mkdir`, `ls` and
echoed success messages all behave normally. So: only a read-back through the mount, from the
container that did the write, is proof. The same trap applies to `docker exec` into a container
whose volume you mis-identified.

## When the target is a service's own state

If the directory is a panel-managed app's data root, a root-container copy is the wrong tool: the
app rewrites its own config from a database on restart and your file is reverted. Use its API
(see the parent skill's pitfall on GUI-managed configs).
