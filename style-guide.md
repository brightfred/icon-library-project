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
- Stroke linecap: `round`
- Stroke linejoin: `round`
- Stroke color: `currentColor` — never hardcode a color
- Fill: `none` on all paths and shapes

### Stroke width by category

| Category | Stroke width | Reason |
|---|---|---|
| action, nav, ui, status, social, comm, file, device, commerce, media | `2` | Simple shapes — bold and clear at small sizes |
| science, aquaculture, engineering, environment | `1.5` | Complex detail — finer lines preserve readability |

Always set stroke-width on the root `<svg>` element only, never on individual paths.

## Geometry

- Prefer clean numbers: coordinates divisible by 0.5 or 1
- Circles: use `cx`, `cy`, `r` — not approximated with paths
- Rectangles with rounded corners: use `rx="2"` unless the shape is intentionally sharp
- Arrows: arrowheads drawn with two short lines at ~45 degrees — not filled triangles
- Chevrons: two lines meeting at a point, not a closed path

## Research Before Drawing

Before drawing any icon, search online for reference images of the real object.
Use what you find to understand the key visual features that make the object recognisable.
Then simplify to the minimum strokes needed to communicate the concept clearly.

Good sources: Wikipedia diagrams, scientific illustration references, engineering schematics.

## What Makes a Good Icon

- Recognisable at 16px and 48px
- One clear idea — no icon tries to show two concepts
- Visually balanced — weight distributed evenly, not heavy on one side
- Original enough to be distinctive — avoid copying Heroicons, Lucide, or Feather exactly
- Negative space used intentionally — breathing room matters
- Based on real reference — not a guess at what the object looks like

## What to Avoid

- Drop shadows, gradients, or filters
- Text or letters inside icons
- More than one stroke width in the same icon
- Decorative details that disappear at small sizes
- Closed filled paths used as a shortcut for a shape
- Drawing from memory without checking a reference first

## Quality Over Quantity

One well-drawn icon is worth more than ten mediocre ones.
If an icon does not clearly communicate its concept at 16px, it must be revised before it is committed.
Do not move on to the next icon until the current one passes the full quality checklist.

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
- `science` — laboratory and research (microscope, flask, atom, dna)
- `aquaculture` — marine and fish farming (fish, net, tank, shrimp)
- `engineering` — technical and mechanical (gear, circuit, valve, blueprint)
- `environment` — nature and ecology (leaf, wave, solar, wind)

## SVG File Format

Simple categories (stroke-width 2):
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <!-- icon paths here -->
</svg>
```

Complex categories (stroke-width 1.5):
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <!-- icon paths here -->
</svg>
```

No `<title>`, no `<desc>`, no comments in production files.
No inline styles — all stroke properties are on the root `<svg>` element.
No transforms on the root element.

## Quality Checklist

Before an icon is added to the library, it must pass all of these:

- [ ] Web reference checked before drawing
- [ ] ViewBox is exactly `0 0 24 24`
- [ ] No hardcoded colors — only `currentColor`
- [ ] No filled paths
- [ ] Correct stroke-width for the category (1.5 or 2) on root element only
- [ ] Looks correct at 16px, 24px, and 48px
- [ ] Named correctly following the naming convention
- [ ] Does not closely duplicate an existing icon in the library
- [ ] Visually balanced — not heavier on one side
- [ ] Concept is immediately readable without a label

## Flagging Icons for Revision

- `too-generic` — looks like every other icon pack
- `too-complex` — too much detail, will not read at small sizes
- `unbalanced` — visually heavier on one side
- `wrong-style` — filled shape, wrong stroke width, hardcoded color
- `unclear` — concept not immediately readable
- `good` — approved, no changes needed

Store flags in `CATALOG.md` next to each icon entry.