# Claude Instructions — Icon Library

Icon rules live in `style-guide.md`. This file covers workflow only.

---

## Queue Mode

When a session starts without a specific icon request:

1. Read `queue.json`
2. If empty, say "Queue is empty" and stop
3. Take the first entry
4. Create the icon following `style-guide.md`, save to `src/`
5. Remove that entry from `queue.json`
6. Run `python build.py`
7. `git add -A && git commit -m "add [icon-name] icon" && git push`
8. Return to step 1

Stop early if the context window is approaching its limit. Report how many icons remain.

---

## Workflow for Every Icon

1. Read `style-guide.md` once per session — not before each icon
2. Search the web for a reference image of the concept before drawing
3. Draw the icon, check the quality checklist in `style-guide.md`
4. Save to `src/`, add to `CATALOG.md` with status `needs-review`
5. After all icons in the session are saved, run `python build.py`
6. `git add -A && git commit -m "add [icon-name] icon" && git push`

One good icon per session is better than five mediocre ones.
Do not move on until the current icon passes the full quality checklist.

---

## Build Script

```
python build.py
```

Reads all SVGs from `src/`, rebuilds `docs/index.html`, updates `CATALOG.md` count.
Never write `docs/index.html` manually.