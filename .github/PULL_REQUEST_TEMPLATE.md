## Summary

Describe the change in 2-5 sentences. Keep the scope concrete.

## Target Branch

- Normal contributor work targets `develop`.
- Release PRs target `main` only when opened by `dprat0821` from same-repository `develop`.
- `main` is the production Mintlify branch and should not receive direct feature PRs.

## Contribution Type

Select the best match and remove the rest.

- lab article
- major revision to existing page
- radar note
- source project
- curated reference note
- repo/process/meta

## Placement

- Target path:
- Links or indexes updated:
- Related issue:

## Source Lineage

List the outside sources, imported references, or existing repo pages that shaped this change.

## Review Checklist

- [ ] The contribution type is explicit.
- [ ] The file or folder is in the correct path for that artifact type.
- [ ] I followed the matching template or contributor guidance where relevant.
- [ ] The change stays repo-native and does not copy upstream material into public tracked paths.
- [ ] Citations, source notes, or attribution boundaries are clear where needed.
- [ ] Relevant README, reading-path, or contributor links were added or updated for discoverability.
- [ ] If I added or revised a practitioner skill package, it includes a human-facing `README.md` and an agent-facing `SKILL.md`.
- [ ] Status and maintenance expectations are clear.
- [ ] The linked issue has the correct `track:*` and `kind:*` labels, and this PR only changes paths allowed for that track.
- [ ] If I changed example code, I ran `python3 scripts/verify_example_projects.py`.
- [ ] If I renamed files or changed paths, I ran `python3 scripts/check_filename_casing.py`.
