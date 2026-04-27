# Claude Instructions — Icon Library

## Queue Mode

When a session starts without a specific icon request, run the queue:

1. Read `queue.json`
2. If the array is empty, say "Queue is empty" and stop
3. Take the first entry
4. Search the web for reference images of the real object before drawing
5. Create that icon following `style-guide.md`, save to `src/`
6. Remove that entry from `queue.json` (write the file back with it removed)
7. Run `python build.py`
8. `git add -A && git commit -m "add [icon-name] icon" && git push`
9. Return to step 1

Stop early (before the queue empties) if the context window is approaching its limit. Report how many icons were completed and how many remain.

## Quality First

One well-drawn icon is worth more than ten mediocre ones.

- Search the web for a real reference before drawing any icon
- Do not guess what an object looks like — verify it
- If the result does not clearly communicate the concept at 16px, revise it before committing
- Do not move on to the next icon until the current one passes the full quality checklist in `style-guide.md`

## Session Order

For every icon batch:
1. Read `style-guide.md` once at the start — do not re-read it between icons
2. Search the web for each icon concept before drawing it
3. Create and save all icons in the batch
4. Run `python build.py` once after all icons are saved — not after each one
5. Commit and push once at the end

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

Replace `[icon-name]` with the icon filename minus the `.svg` extension.

---

## Icon Rules

All icons must follow `style-guide.md` exactly. Quick reference:

- ViewBox: `0 0 24 24`, `width="24"`, `height="24"`
- `fill="none"`, `stroke="currentColor"`, `stroke-linecap="round"`, `stroke-linejoin="round"` — on the root `<svg>` only
- Stroke width on root `<svg>` only:
  - `stroke-width="2"` for: action, nav, ui, status, social, comm, file, device, commerce, media
  - `stroke-width="1.5"` for: science, aquaculture, engineering, environment
- Stroke only — no filled shapes
- No `<title>`, `<desc>`, comments, inline styles, or root transforms
- Optical padding: minimum 1.5px from all edges
- Arrowheads: two lines at ~45° — not filled triangles
- Naming: `[category]-[descriptor].svg`

Add every new icon to the `CATALOG.md` table for its category with status `needs-review`.