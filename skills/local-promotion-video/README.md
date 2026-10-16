# Local Promotion Video

Create a short product video from a brief, local screenshots and optional audio. Codex writes or revises the scenes; native Remotion renders an MP4. There is no required model API, hosted service, Hugging Face quota or course database.

## Setup and first use

Use Node 22.12+ (the verification used Node 24), Python 3.10+ for the copy helper, and a local Chrome/Chromium executable. FFmpeg/ffprobe are useful for checking the final file. Review Remotion's [license](https://www.remotion.dev/license) for the actual organization and use.

From the handbook root:

```bash
python3 skills/course-support/scripts/setup_course_skills.py --lesson 6
python3 skills/local-promotion-video/scripts/init_project.py .local-state/my-promotion
cd .local-state/my-promotion
npm ci --ignore-scripts --no-audit --no-fund
```

Set `REMOTION_BROWSER_EXECUTABLE` to an existing Chrome/Chromium executable. For example, on a Mac with Chrome installed:

```bash
export REMOTION_BROWSER_EXECUTABLE="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
npm run check
npm run preview
npm run render
```

On PowerShell, set `$env:REMOTION_BROWSER_EXECUTABLE` to your installed browser's executable. The starter does not silently download a browser or a model. Prepare dependencies and a successful test render before class. It does not require Linux bubblewrap or call the private Pathway wrapper.

Invoke in Codex:

> Use $local-promotion-video with my existing product description and screenshots. Make a 25-second vertical video. Show one real use case and one real action. Keep the project editable, preview it, then render locally. Use no paid generation service.

## Edit, preview and render

Edit `brief.json`: product name, audience, frame size, FPS, colors and timed scenes. Copy permitted images/audio into `public/`; use relative file names in the brief. Scene text and layout remain editable in `src/Promotion.tsx`. The bundled fictional task-list example is not evidence of a real product or user result.

`npm run check` validates the brief and local asset paths. `npm run preview` creates a midpoint PNG for every scene plus `preview.html` in a new output directory. Open the HTML locally, inspect the frames and revise. Preview is a contact sheet, not an interactive Remotion Studio or a full-motion check. `npm run render` writes `promotion.mp4` and a receipt in a separate run directory. No earlier render is overwritten.

A useful revision: replace the opening sentence with the user's problem, increase the product demonstration time, then shorten another scene to keep the total duration. Rerun preview and render in the same project.

Optional audio goes in `brief.audio` with a local `file`, a `kind` (`voiceover` or `music`) and a `volume`. Record its source and permission in `sources.md`. The starter does not generate a voice or music, and it does not automatically create synchronized subtitles. Use readable screen text for a silent draft. When adding narration, align its real timing and verify the finished audio; a music-only track is not a voiceover.

## Classroom exercise

Use the [GW02 Lesson 6 guide](../course-support/lessons/lesson-6.md), also available [in Chinese](../course-support/zh-Hans/lesson-6.md). Spend about 40 minutes on brief, scene plan, local code, preview, one revision and export. Installation happens before class. The lesson's browser experiments are separate optional inputs; they never block the minimum screenshot-and-text video.

Only the project folder and its outputs are local state. No shared course backend is provisioned, no production post is created and no remote schedule is saved. Keep completed renders and source for recovery; create a new project folder instead of deleting unrelated files.

## Checks

```bash
python3 -m unittest discover -s skills/local-promotion-video/tests -p 'test_*.py'
node --test skills/local-promotion-video/assets/starter/scripts/brief.test.mjs
```

Actual end-to-end render results belong in the task's execution report, with environment and media parameters. Do not treat these validation commands as a successful MP4 render. [Source notes](references/source-notes.md) distinguish the original starter from upstream APIs.
