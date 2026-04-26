# Claude Instructions — Icon Library

## Mandatory Post-Icon Workflow

After saving any new `.svg` file to `src/`, always run both steps below in order before considering the task done.

---

### Step 1 — Run the build script

```
python build.py
```

This script handles everything: reads all SVGs from `src/`, rebuilds `docs/index.html`, and updates the `CATALOG.md` total count. Do not write `docs/index.html` or update the count manually.

### Step 2 — Commit and push

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
