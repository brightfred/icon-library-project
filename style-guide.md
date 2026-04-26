# Icon Library — Style Guide

This is the source of truth for every icon in this library.
Any tool, agent, or contributor generating icons must follow these rules exactly.
No exceptions without updating this document first.

---

## Grid & ViewBox

- ViewBox: `0 0 24 24`
- All icons are square
- Optical padding: minimum 1.5px from viewBox edge on all sides
- Align to pixel grid where possible — avoid sub-pixel coordinates unless necessary for curves

## Stroke

- Style: stroke only — no filled shapes
- Stroke width: `2`
- Stroke linecap: `round`
- Stroke linejoin: `round`
- Stroke color: `currentColor` — never hardcode a color
- Fill: `none` on all paths and shapes

## Geometry

- Prefer clean numbers: coordinates divisible by 0.5 or 1
- Circles: use `cx`, `cy`, `r` — not approximated with paths
- Rectangles with rounded corners: use `rx="2"` unless the shape is intentionally sharp
- Arrows: arrowheads drawn with two short lines at ~45 degrees — not filled triangles
- Chevrons: two lines meeting at a point, not a closed path

## What Makes a Good Icon

- Recognisable at 16px and 48px
- One clear idea — no icon tries to show two concepts
- Visually balanced — weight distributed evenly, not heavy on one side
- Original enough to be distinctive — avoid copying Heroicons, Lucide, or Feather exactly
- Negative space used intentionally — breathing room matters

## What to Avoid

- Drop shadows, gradients, or filters
- Text or letters inside icons
- More than one stroke width in the same icon
- Decorative details that disappear at small sizes
- Closed filled paths used as a shortcut for a shape

## Naming Convention

Format: `[category]-[descriptor].svg`

Categories:
- `action` — things users do (add, delete, edit, search, upload)
- `nav` — navigation (arrow, chevron, menu, close, back)
- `ui` — interface elements (bell, badge, toggle, checkbox, modal)
- `media` — audio, video, image (play, pause, camera, mic, volume)
- `file` — documents and data (file, folder, download, upload, attach)
- `comm` — communication (chat, mail, phone, send, reply)
- `social` — social concepts (share, heart, star, bookmark, user)
- `status` — states and feedback (check, warning, info, error, loading)
- `device` — hardware (mobile, desktop, tablet, wifi, battery)
- `commerce` — business (cart, bag, card, receipt, tag)

Examples:
- `action-search.svg`
- `nav-arrow-left.svg`
- `ui-bell.svg`
- `status-check.svg`

## SVG File Format

Every icon file must follow this exact structure:

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <!-- icon paths here -->
</svg>
```

No `<title>`, no `<desc>`, no comments in production files.
No inline styles — all stroke properties are on the root `<svg>` element.
No transforms on the root element.

## Quality Checklist

Before an icon is added to the library, it must pass all of these:

- [ ] ViewBox is exactly `0 0 24 24`
- [ ] No hardcoded colors — only `currentColor`
- [ ] No filled paths
- [ ] Stroke width is `2` on root element only
- [ ] Looks correct at 16px, 24px, and 48px
- [ ] Named correctly following the naming convention
- [ ] Does not closely duplicate an existing icon in the library
- [ ] Visually balanced — not heavier on one side

## Prompt Template for Claude Code

When asking Claude Code to generate a new icon, use this exact format:

```
Create an SVG icon for: [icon name]
Concept: [what it should represent]
Follow /icons/style-guide.md exactly.
Save to /icons/src/[category]-[name].svg
Do not add fills. Do not hardcode colors. ViewBox must be 0 0 24 24.
Check the quality checklist before saving.
```

## Flagging Icons for Revision

When reviewing icons (via OpenClaw or manually), use these flag labels:

- `too-generic` — looks like every other icon pack
- `too-complex` — too much detail, will not read at small sizes  
- `unbalanced` — visually heavier on one side
- `wrong-style` — filled shape, wrong stroke width, hardcoded color
- `unclear` — concept not immediately readable
- `good` — approved, no changes needed

Store flags in `CATALOG.md` next to each icon entry.
