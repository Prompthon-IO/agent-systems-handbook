# Reusable Layout Catalog

Use this catalog during inventory planning. Choose the smallest set that covers
the story; a template does not need every layout.

| Layout id | Best used for | Core placeholders | Avoid when |
| --- | --- | --- | --- |
| `title` | Opening a deck with one clear promise | title, subtitle, presenter, date | The slide needs detailed context |
| `agenda` | Previewing three to seven sections | title, ordered sections | The talk is too short to need navigation |
| `section-divider` | Resetting attention between major chapters | section label, title, optional motif | Every slide would become a divider |
| `problem` | Framing the user pain or opportunity | headline, evidence, affected audience | Evidence is not yet available |
| `key-message` | Landing one memorable claim | message, support line, optional visual | Several equal ideas must be compared |
| `two-column` | Contrasting or pairing related ideas | left title/body, right title/body | Content lengths are badly unbalanced |
| `comparison` | Comparing options on consistent criteria | option names, criteria, values, takeaway | The options use unrelated criteria |
| `process` | Showing three to seven sequential steps | step labels, descriptions, connectors | The sequence has many branches |
| `timeline` | Showing dated phases or milestones | dates, events, status | Exact timing is unknown or unimportant |
| `metrics` | Highlighting one to four headline measures | metric value, label, context, source | The numbers lack definitions or sources |
| `chart-and-insight` | Pairing one chart with the conclusion it supports | chart, insight, source | The chart needs extensive explanation |
| `quote` | Giving a short attributed voice a full beat | quote, speaker, affiliation/source | The quote is long or weakly sourced |
| `case-study` | Summarizing context, action, and result | challenge, approach, outcome, evidence | Results cannot be verified |
| `team` | Introducing a small group and roles | person, role, short credential, image | The group is too large for legible cards |
| `image-focus` | Letting one licensed visual carry the slide | image, caption, credit | The visual is decorative or low resolution |
| `closing` | Ending with one action or memorable takeaway | takeaway, call to action, contact | Several unrelated next steps remain |
| `appendix` | Holding supporting detail outside the main story | title, body/table/chart, source | The content is required to follow the main argument |

## Inventory Heuristics

- Include `title`, `section-divider`, and `closing` for most reusable decks.
- Add both `process` and `timeline` only when the template must support
  sequence and calendar views.
- Prefer `comparison` over improvised columns when criteria must align.
- Pair every data layout with a source placeholder.
- Keep placeholder counts low enough that a user can scan the slide in seconds.
- Use usage notes to prevent a layout from becoming a generic dumping ground.

## Placeholder Kinds

Use these portable kinds in the manifest:

- `text`
- `rich-text`
- `image`
- `chart`
- `table`
- `metric`
- `date`
- `source`
- `logo`

Backend adapters may map these kinds to native PowerPoint or Slides objects.
