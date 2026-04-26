# Claude Code Prompt Templates

Copy and paste these into Claude Code. Fill in the brackets.

---

## Generate a new icon

```
Create an SVG icon for: [icon name]
Concept: [what it represents — be specific]
Style guide: /icons/style-guide.md — follow it exactly.
Save to: /icons/src/[category]-[name].svg
Add an entry to: /icons/CATALOG.md with status `needs-review`

Rules:
- ViewBox must be 0 0 24 24
- stroke="currentColor" only — no hardcoded colors
- fill="none" on all elements
- stroke-width="2" on root SVG only
- stroke-linecap="round" stroke-linejoin="round"
- No fills, no gradients, no text
```

---

## Revise a flagged icon

```
Revise the icon: /icons/src/[filename]
Flag reason: [too-generic / too-complex / unbalanced / unclear]
Specific feedback: [describe exactly what is wrong]
Style guide: /icons/style-guide.md — follow it exactly.
Overwrite the existing file.
Update status in /icons/CATALOG.md to `needs-review` after revision.

Do not change the viewBox, stroke properties, or file name.
```

---

## Generate a batch of icons

```
Generate icons for the following concepts.
Style guide: /icons/style-guide.md — follow it exactly for every icon.
Save each to /icons/src/ with correct category prefix.
Add each to /icons/CATALOG.md with status `needs-review`.

Icons to generate:
- [category]-[name]: [concept description]
- [category]-[name]: [concept description]
- [category]-[name]: [concept description]

After generating, list the file names created.
```

---

## OpenClaw voice prompt (say this out loud)

> "Create an icon for [concept]. Save it to my icons library."

OpenClaw will pass this to Claude Code using the generate template above.
It will confirm the file name when done.

---

## Review session (OpenClaw)

> "Open my icon library. Show me everything flagged as needs-review."

OpenClaw will list icons from CATALOG.md and can display them on your phone screen.
Say "flag [icon name] as [reason]" to update the catalog.
Say "this one is good" to mark it approved.
