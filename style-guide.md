# Icon Library — Style Guide

This is the single source of truth for icon rules.
All other files defer to this one. No icon rules live anywhere else.

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

| Category | Stroke width |
|---|---|
| action, nav, ui, status, social, comm, file, device, commerce, media | `2` |
| science, aquaculture, engineering, environment | `1.5` |

Set stroke-width on the root `<svg>` element only — never on individual paths.

## Geometry

- Prefer clean numbers: coordinates divisible by 0.5 or 1
- Circles: use `cx`, `cy`, `r` — not approximated with paths
- Rectangles with rounded corners: use `rx="2"` unless the shape is intentionally sharp
- Arrows: arrowheads drawn with two short lines at ~45 degrees — not filled triangles
- Chevrons: two lines meeting at a point, not a closed path

## Research

Search the web for a real reference before drawing any icon.
Do not draw from memory. Use what you find to identify the minimum strokes needed to communicate the concept.

## What Makes a Good Icon

- Recognisable at 16px and 48px
- One clear idea — no icon tries to show two concepts
- Visually balanced — weight distributed evenly
- Negative space used intentionally
- Immediately readable without a label

## What to Avoid

- Drop shadows, gradients, or filters
- Text or letters inside icons
- More than one stroke width in the same icon
- Details that disappear at small sizes
- Filled paths used as a shortcut for a shape
- Drawing without checking a reference first

## File Format

Simple categories (`stroke-width="2"`):
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
  <!-- paths -->
</svg>
```

Complex categories (`stroke-width="1.5"`):
```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
  <!-- paths -->
</svg>
```

No `<title>`, no `<desc>`, no comments. No inline styles. No transforms on root element.

## Naming

Format: `[category]-[descriptor].svg`

Categories: action, nav, ui, media, file, comm, social, status, device, commerce, science, aquaculture, engineering, environment

## Quality Checklist

- [ ] Web reference checked before drawing
- [ ] ViewBox is exactly `0 0 24 24`
- [ ] No hardcoded colors — only `currentColor`
- [ ] No filled paths
- [ ] Correct stroke-width for the category on root element only
- [ ] Readable at 16px, 24px, and 48px
- [ ] Named correctly
- [ ] Not a duplicate of an existing icon
- [ ] Visually balanced
- [ ] Concept is immediately readable without a label

## Review Flags

- `good` — approved
- `too-generic` — looks like every other icon pack
- `too-complex` — too much detail for small sizes
- `unbalanced` — visually heavier on one side
- `wrong-style` — fill, wrong stroke width, or hardcoded color
- `unclear` — concept not immediately readable