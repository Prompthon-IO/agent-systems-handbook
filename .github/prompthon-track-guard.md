# Contribution track guard

The guard reads the first linked issue's track, then falls back to the PR's
`track: explorer`, `track: practitioner`, or `track: builder` label. Link an
issue with a closing keyword such as `Closes #123`. A maintainer-approved
direct PR without an issue still needs a track label on the PR itself.
Adding or changing a PR label triggers a new check.

The allowed paths are defined in `scripts/prompthon-activity-policy.mjs`
relative to this `.github/` directory. Entries ending in `/` allow a
directory; all other entries match one exact repository-relative filename.

Practitioner contributions include skills, snippets, workshops, templates,
specialization pages, and their matching `zh-Hans/` directories. Course
contributions may also update `docs.json`, the environment setup and sample
projects reading-path pages, and their Chinese translations. This does not
allow unrelated reading paths, foundations, repository scripts, or workflows.

The workflow checks out the PR's base branch, so editing policy inside a PR
does not authorize that PR's paths. A policy repair must first pass review
and merge into the base branch. Then re-run the failed check using a run
whose event already includes the correct track label, or change the PR label
to trigger a fresh event. All normal review and required CI checks still apply.

The workflow uses `issues: read` to inspect linked issues and
`pull-requests: write` for PR failure comments. It executes only the trusted
base-branch guard and does not persist checkout credentials. Validation
failures are also written to the Actions log and job summary, even if the
comment request fails. Comment delivery never decides whether paths pass.

Run the regression checks locally:

```sh
node --test .github/scripts/prompthon-activity-policy.test.mjs .github/scripts/prompthon-track-guard.test.mjs
```

The read-only `validate-mintlify` PR workflow runs these tests against proposed
code; the privileged track guard continues to execute base-branch code only.
