# Source and license notes

Reviewed 2026-08-30. Behavioral reference: [upstream package](https://github.com/anthropics/skills/blob/3b3fad96af16a10759d930941b4520ba0c40edae/skills/webapp-testing/SKILL.md). License finding: Apache-2.0 in that package's LICENSE.txt.

Copied: nothing. Rewritten: all skill instructions, templates, fixtures and Python helpers are original for this repository. Prompthon adaptations: distinct Test boundary, synthetic course workflow, shared scoped persistence, safety gates, readback, bilingual labs and reset guidance. No model prompt or script from another repository is vendored.

Primary API references: [Codex skills](https://developers.openai.com/codex/skills), [Playwright Python](https://playwright.dev/python/docs/intro), [Vercel deploy CLI](https://vercel.com/docs/cli/deploy), [Vercel deployment readback](https://vercel.com/docs/rest-api/deployments/get-a-deployment-by-id-or-url). See the [shared source audit](../../course-support/references/source-audit.json) for pinned review evidence. Recheck provider behavior before updating this package.
