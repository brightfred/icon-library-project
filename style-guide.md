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

## Drawing Approach

Before writing any SVG, work through these steps mentally:

1. **Identify 3-6 anatomical parts** of the object. Microscope: eyepiece, body tube, stage, arm, base. Fish: body, tail, fin, eye.
2. **Map one path to each part.** Every path must have a named purpose. If you cannot name what anatomical part a path represents, remove it.
3. **Trace real silhouettes with curves.** Use `path` with bezier curves to follow the actual contour of the object. Reserve `line` only for genuinely straight isolated strokes — baselines, crosshairs, tick marks.
4. **Test at 16px mentally.** Would someone immediately know what this is without a label? If no — redraw.

**Bad — microscope as disconnected lines:**
These lines could be anything. They do not read as a microscope.
```
<circle cx="12" cy="5" r="2"/>
<line x1="12" y1="7" x2="12" y2="13"/>
<line x1="7" y1="13" x2="17" y2="13"/>
```

**Good — microscope as traced shapes:**
Each path traces a real anatomical part. The C-arm curve makes it instantly recognisable.
```
<path d="M 9,6 L 9,3 L 13,3 L 13,6"/>       <!-- eyepiece U-shape -->
<path d="M 8,12 L 8,6 L 13,6 L 13,12"/>      <!-- body tube -->
<line x1="5" y1="15" x2="13" y2="15"/>       <!-- stage platform -->
<path d="M 13,6 C 21,6 21,22 15,22"/>        <!-- C-arm bezier -->
<line x1="3" y1="22" x2="21" y2="22"/>       <!-- base -->
```

**Using an existing icon as reference (e.g. Lucide — MIT licensed):**
- Study how it maps paths to anatomical parts
- Differentiate deliberately: change proportions, curve direction, body width, detail level
- Every path in your version must differ meaningfully from the reference
- Document what anatomical part each path represents before committing

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
- Collections of disconnected lines that only vaguely suggest the object

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
- [ ] Every path maps to a named anatomical part
- [ ] No disconnected lines that only vaguely suggest the object
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