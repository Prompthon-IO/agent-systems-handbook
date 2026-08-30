# Source and license notes

Reviewed 2026-08-30. Behavioral reference: [upstream package](https://github.com/vercel-labs/agent-skills/blob/063bee94c3f4df8453406c830b0a7df0f2860278/skills/deploy-to-vercel/SKILL.md). License finding: No applicable license file was located in the source audit; no upstream code or text was copied.

Copied: nothing. Rewritten: all skill instructions, templates, fixtures and Python helpers are original for this repository. Prompthon adaptations: distinct Deploy boundary, synthetic course workflow, shared scoped persistence, safety gates, readback, bilingual labs and reset guidance. No model prompt or script from another repository is vendored.

Primary API references: [Codex skills](https://developers.openai.com/codex/skills), [Playwright Python](https://playwright.dev/python/docs/intro), [Vercel deploy CLI](https://vercel.com/docs/cli/deploy), [Vercel deployment readback](https://vercel.com/docs/rest-api/deployments/get-a-deployment-by-id-or-url). See the [shared source audit](../../course-support/references/source-audit.json) for pinned review evidence. Recheck provider behavior before updating this package.
