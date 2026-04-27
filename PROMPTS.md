# Claude Code Prompt Templates

Quick reference for common tasks. Icon rules are in `style-guide.md`.

---

## Generate one icon

```
Search the web for reference images of: [object name]
Create icon: [category]-[name]
Concept: [specific description]
Follow style-guide.md. Save to src/. Add to CATALOG.md as needs-review.
Then run: python build.py && git add -A && git commit -m "add [category]-[name] icon" && git push
```

---

## Revise a flagged icon

```
Search the web for reference images of: [object name]
Revise: src/[filename]
Problem: [exactly what is wrong]
Follow style-guide.md. Overwrite the file. Update CATALOG.md status to needs-review.
Then run: python build.py && git add -A && git commit -m "revise [filename]" && git push
```

---

## Work through the queue

```
Work through the queue.
```

---

## Add to the queue

```
Add these to queue.json:
- [category]-[name]: [concept]
- [category]-[name]: [concept]
```

---

## OpenClaw voice

> "Create an icon for [concept] and save it to my icons library."
> "Flag [icon name] as [reason]."
> "Mark [icon name] as good."