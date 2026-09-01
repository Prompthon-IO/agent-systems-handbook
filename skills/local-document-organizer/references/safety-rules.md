# Safety Rules

Readable rules that govern how `local_document_organizer.py` decides what is
safe to move. Keep this file legible to people and agents.

## Hard Prohibitions

- **Never delete files.** The script does not call `unlink` or `rmtree`.
- **Never overwrite files.** If the destination path already exists, the move
  is recorded as `conflict` and skipped.
- **Never move without preview.** The `scan` command writes a plan and a
  Markdown report; the `apply` command refuses to run unless the user passes
  `--confirm ORGANIZE`.
- **Never act outside the user-named folder.** No recursive moves into other
  drives, system folders, or cloud-sync folders unless the user names them.

## Refused Targets

The scanner refuses to operate on any of these paths:

- `/`, `/System`, `/Library`, `/Applications`, `/usr`, `/var`, `/etc`,
  `/private`, `/bin`, `/sbin`
- `~/Library` (macOS user library)
- `~/.ssh`, `~/.gnupg`, `~/.aws` (credential directories)
- The home directory itself (must name a subfolder)

## Confidence And Move Eligibility

Each rule in `classification-rules.csv` has a confidence: `high`, `medium`, or
`low`.

- `high` and `medium` matches are eligible to move by default.
- `low` matches and unmatched files default to `Unknown/` and are **not
  moved** unless the user passes `--include-low-confidence`. They appear in
  the preview report so the user can see what would be touched.

## Conflict Handling

- Destination collision (a file with the same name already exists in the
  target subfolder): skip, log `status=conflict`. No rename, no overwrite.
- Source no longer exists at `apply` time: skip, log `status=missing`.
- Permission denied: skip, log `status=permission_error`. The run continues
  with the next file.

## Undo Boundary

- The `apply` command writes an action log before each move and updates it
  with the result.
- The `undo` command reads an action log and reverses every `status=moved`
  entry by moving the file back to its original path. It refuses to overwrite
  if the original path now contains a different file.

## Data That Stays Local

- The runtime database lives at
  `~/.codex/state/local-document-organizer/organizer.sqlite`.
- Reports, plans, and action logs live under the same directory.
- None of these are committed to git unless the user explicitly asks for
  sample artifacts.

## Professional AI Agent Course adapter

The course adapter reuses existing classification rules and preview generation. Moves stay within the selected directory and use atomic no-clobber hard links before removing the old directory entry; no file contents are deleted. It fails safely on filesystems without hard-link support. It refuses stale/tampered plans, changed sources, symlinks, collisions and replayed plans. Every intent and action is fsynced in a local journal. Undo checks content hashes and refuses collisions; use `--storage local` for recovery while the remote API is down. It does not upload file binaries.
