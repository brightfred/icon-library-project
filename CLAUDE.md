# Claude Instructions — Icon Library

## Queue Mode

When a session starts without a specific icon request, run the queue:

1. Read `queue.json`
2. If the array is empty, say "Queue is empty" and stop
3. Take the first entry
4. Create that icon following `style-guide.md`, save to `src/`
5. Remove that entry from `queue.json` (write the file back with it removed)
6. Run `python build.py`
7. `git add -A && git commit -m "add [icon-name] icon" && git push`
8. Return to step 1

Stop early (before the queue empties) if the context window is approaching its limit. Report how many icons were completed and how many remain.

## Session Order

For every icon batch:
1. Read `style-guide.md` once at the start — do not re-read it between icons
2. Create and save all icons in the batch
3. Run `python build.py` once after all icons are saved — not after each one
4. Commit and push once at the end

## Mandatory Post-Icon Workflow

After saving all `.svg` files for the batch, run both steps below in order before considering the task done.

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
