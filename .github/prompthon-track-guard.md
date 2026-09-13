# Contribution track guard

The guard uses explicit contribution choices and linked Issue/PR labels,
rejecting conflicting values. See [classification help](./contribution-classification.md).
Adding or changing a PR label or editing the PR description triggers a new check.

The allowed paths are defined in `scripts/prompthon-activity-policy.mjs`
relative to this `.github/` directory. Entries ending in `/` allow a
directory; all other entries match one exact repository-relative filename.

All contributor tracks (Explorer, Practitioner, and Builder) may modify the
root `docs.json` in the same PR as their contribution. This exact-file allowance
lets contributors add required navigation without a separate maintainer PR;
it does not allow other root files or expand their track-specific directories.
Reviewers remain responsible for the scope and correctness of navigation and
other site configuration changes. Normal independent review, JSON/Mintlify
validation, and required CI checks still apply.

Practitioner contributions include skills, snippets, workshops, templates,
specialization pages, and their matching `zh-Hans/` directories. Course
contributions may also update the environment setup and sample
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
