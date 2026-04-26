# Claude Instructions — Icon Library

## Mandatory Post-Icon Workflow

After saving any new `.svg` file to `src/`, always run all three steps below in order before considering the task done.

---

### Step 1 — Rebuild `index.html`

Use Glob to list every `.svg` file currently in `src/`. Then Read each file individually. Then fully overwrite `index.html` as a static icon gallery containing ALL of them — not just the ones added in the current session.

Required process (do not skip any step):
1. `Glob("src/*.svg")` — discover the full current file list
2. `Read` each file returned by Glob — get the exact SVG source
3. `Write` a brand-new `index.html` that embeds every file found in step 1

Rules for the generated HTML:
- One card per icon, laid out in a CSS grid
- Each card inlines the raw SVG markup verbatim from the Read result (do not use `<img src>`, do not reconstruct from memory)
- Each card shows the filename (without `.svg`) as a label beneath the icon
- The subtitle shows the total icon count from step 1
- Match the visual style of `review.html` (same grid, card, and typography classes) but without flag buttons or review log — index.html is a clean read-only gallery
- Always overwrite the full file from scratch — never append or partially update

### Step 2 — Update `CATALOG.md` total count

Count the `.svg` files in `src/` and update the `**Total icons:**` line in `CATALOG.md` to match.

### Step 3 — Commit and push

Run exactly:

```
git add -A && git commit -m "add [icon-name] icon" && git push
```

Replace `[icon-name]` with the icon filename minus the `.svg` extension — e.g., `add action-upload icon`.

---

## Icon Rules

All icons must follow `style-guide.md` exactly. Quick reference:

- ViewBox: `0 0 24 24`, `width="24"`, `height="24"`
- `fill="none"`, `stroke="currentColor"`, `stroke-width="2"`, `stroke-linecap="round"`, `stroke-linejoin="round"` — on the root `<svg>` only
- Stroke only — no filled shapes
- No `<title>`, `<desc>`, comments, inline styles, or root transforms
- Optical padding: minimum 1.5px from all edges
- Arrowheads: two lines at ~45° — not filled triangles
- Naming: `[category]-[descriptor].svg`

Add every new icon to the `CATALOG.md` table for its category with status `needs-review`.
