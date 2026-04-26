# Claude Instructions — Icon Library

## Mandatory Post-Icon Workflow

After saving any new `.svg` file to `src/`, always run all three steps below in order before considering the task done.

---

### Step 1 — Rebuild `index.html`

Read every `.svg` file in `src/`. Generate (or fully overwrite) `index.html` as a static icon gallery:

- One card per icon, laid out in a CSS grid
- Each card inlines the raw SVG markup (do not use `<img src>`)
- Each card shows the filename (without `.svg`) as a label beneath the icon
- Match the visual style of `review.html` (same grid, card, and typography classes) but without the flag buttons or review log — index.html is a clean read-only gallery
- If `index.html` does not yet exist, create it from scratch

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
