# Provider workflow

Prefer the existing Git-linked Vercel flow. Use a dedicated demo project provisioned by the instructor before class, not the handbook website's production project. Read its README, project/team identity, Git connection, environment and baseline deployment. Creating a new provider project is outside the helper.

For a site copied to a separate Git repository, commit the intended files, then use Web Builder's `record` command with a reviewed JSON argv such as `["node", "--check", "app.js"]`. Run Test after any source/README/ignore-file changes so source fingerprints agree. `.git`, `.vercel`, dependency directories, environment files and course markers are excluded from the manifest. Secrets must still be excluded from the deployment bundle using the project's normal ignore rules; a metadata manifest is not a deployment-file filter.

A Git push is an external write: review and obtain authorization unless the user's existing request covers it. Do not change remote branches or protection settings to force a preview. Retrieve the actual Vercel deployment id from the provider, then run `verify` as shown in the README. Provider commit attribution is mandatory; if absent, fix the Git integration rather than fabricate a SHA.

The CLI fallback requires an installed, authenticated Vercel CLI and `.vercel/project.json`. This tool does not place tokens on the command line. The API verifier separately uses `VERCEL_ACCESS_TOKEN` or a private `--vercel-token-file`. Treat course API and Vercel credentials as different scopes.

```text
python3 skills/vercel-deploy/scripts/course_deploy.py --dry-run deploy --project <project-path> --test-id <test-id> --expected-commit <commit> --expected-text <page-marker> --baseline-deployment <existing-ready-id> --attempt <unique-reviewed-attempt>
```

After explicit preview approval, remove `--dry-run` and add `--confirm PREVIEW`. The helper runs `vercel deploy --target preview --yes` only after verifying a READY deployment in the linked project, avoiding the new-project first-deployment hazard documented by Vercel. It does not bypass provider login, billing, team access, or deployment protection. Preview URLs can be public: inspect the actual bundle and never include private student files.

For production, separately review impact and obtain action-time authorization; use `--target production --confirm PRODUCTION --production-approved`. Do not promote or alias automatically. An approval flag is an assertion by the caller, not a source of authority.

An attempt journal is written before submission. If the process dies after provider acceptance, its state may remain `outcome_unknown`. Recover that deployment through Vercel and call `verify`. Reusing the attempt is refused. A failed or protected URL stays unverified; it is not safe to remove access controls just to pass this check. Reset never deletes provider deployments.
