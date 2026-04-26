# SPEC: Annotation Marker Pin Redesign
**File:** `atlas.html` only — no other files change.

---

## Problem summary

The current `.ann-marker` elements are 40 px circles positioned with `transform: translate(-50%, -50%)` and OSD `placement: CENTER`. This **centers the circle directly on top of the feature being annotated**, obscuring it. Secondary issues: the `outline` rings, heavy scale animations, and `letter-spacing: -.3px` on a number that doesn't need tracking all add unnecessary noise. The `.ip-ann-num` badges in the info panel also lack `line-height: 1`, causing slightly off-center numbers.

---

## Design: teardrop pin

Replace the circle with a **pin shape**: a circular badge on top with a downward-pointing triangular tip at the bottom. The **tip** sits at the exact annotated coordinate; the badge floats above it, keeping the feature visible.

```
   ┌───┐      ← .ann-badge  (26 × 26 px circle, colored per ann1–5)
   │ 2 │
   └─┬─┘
     ▼         ← .ann-tip   (CSS border-triangle, 10 × 7 px, same color as badge)
     ·          ← exact coordinate
```

Total pin height: 26 + 7 = **33 px**. The element's bottom edge (tip) aligns to the coordinate.

---

## Constraints — do not change

- CSS variables `--ann1` through `--ann5` and `--ann1-glow` through `--ann5-glow` in `:root`. (Used by HemeAtlas.)
- OSD CDN version, viewer config, `panToAnnotation` logic, sidebar, info panel layout.
- `cases.json`.

---

## Change 1 — CSS: replace the annotation marker block

**Locate** the comment `/* ── ANNOTATION MARKERS ── */` (line ≈ 446).
Keep the `:root` block with `--ann1` … `--ann5-glow` variables **unchanged**.

**Replace** everything from `.ann-marker {` down through the last `.ann-marker[data-n="5"].active { … }` rule (lines ≈ 466–558) with the following:

```css
/* ── ANNOTATION MARKERS — pin style ── */
.ann-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  /* translate(-50%, -100%) anchors the pin tip (bottom-center) to the coordinate */
  transform: translate(-50%, -100%);
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, .65));
  transition: filter .15s, transform .15s;
  user-select: none;
  font-family: 'DM Sans', sans-serif;
}

.ann-badge {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 800;
  line-height: 1;
  color: #0a0e18;
}

.ann-tip {
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  /* border-top-color set per data-n below */
  border-top-width: 7px;
  border-top-style: solid;
}

/* Per-annotation colors */
.ann-marker[data-n="1"] .ann-badge { background: var(--ann1); }
.ann-marker[data-n="2"] .ann-badge { background: var(--ann2); }
.ann-marker[data-n="3"] .ann-badge { background: var(--ann3); }
.ann-marker[data-n="4"] .ann-badge { background: var(--ann4); }
.ann-marker[data-n="5"] .ann-badge { background: var(--ann5); }

.ann-marker[data-n="1"] .ann-tip { border-top-color: var(--ann1); }
.ann-marker[data-n="2"] .ann-tip { border-top-color: var(--ann2); }
.ann-marker[data-n="3"] .ann-tip { border-top-color: var(--ann3); }
.ann-marker[data-n="4"] .ann-tip { border-top-color: var(--ann4); }
.ann-marker[data-n="5"] .ann-tip { border-top-color: var(--ann5); }

/* Hover: subtle brightness lift — no scale, no glow rings */
.ann-marker:hover {
  filter: drop-shadow(0 3px 10px rgba(0, 0, 0, .75)) brightness(1.1);
}

/* Active: lift pin 3 px upward + stronger shadow */
.ann-marker.active {
  transform: translate(-50%, -100%) translateY(-3px);
  filter: drop-shadow(0 5px 14px rgba(0, 0, 0, .85)) brightness(1.15);
}
```

**Why `drop-shadow` instead of `box-shadow`:** `box-shadow` applies to the rectangular bounding box and ignores the triangle tip. `filter: drop-shadow` follows the actual rendered shape (badge + tip), producing a coherent pin shadow.

---

## Change 2 — CSS: fix `.ip-ann-num` centering

**Locate** `.ip-ann-num {` in the info panel CSS (line ≈ 683). Add `line-height: 1;` to the rule:

```css
.ip-ann-num {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  color: #0a0e18;
  font-size: 11px;
  font-weight: 900;
  line-height: 1;          /* ← ADD THIS */
  margin-right: 8px;
  flex-shrink: 0;
  vertical-align: middle;
}
```

---

## Change 3 — JS: update marker element creation

**Locate** `addAnnotationOverlays()` (line ≈ 1416). Change the marker element construction from a flat `textContent` assignment to a two-child structure:

**Before:**
```javascript
const el = document.createElement('div');
el.className = 'ann-marker';
el.dataset.n = i + 1;
el.textContent = i + 1;
el.onclick = (e) => { e.stopPropagation(); highlightAnnotation(i); };
```

**After:**
```javascript
const el = document.createElement('div');
el.className = 'ann-marker';
el.dataset.n = i + 1;
el.innerHTML = `<div class="ann-badge">${i + 1}</div><div class="ann-tip"></div>`;
el.onclick = (e) => { e.stopPropagation(); highlightAnnotation(i); };
```

---

## Change 4 — JS: update OSD overlay placement

On the same `viewer.addOverlay(…)` call (line ≈ 1433), change `CENTER` to `BOTTOM`:

**Before:**
```javascript
viewer.addOverlay({ element: el, location: vpPt, placement: OpenSeadragon.Placement.CENTER });
```

**After:**
```javascript
viewer.addOverlay({ element: el, location: vpPt, placement: OpenSeadragon.Placement.BOTTOM });
```

**Note:** Both the CSS `translate(-50%, -100%)` and `placement: BOTTOM` express the same anchor intent. Setting both is intentional — it makes the desired behavior explicit at the OSD API level and the CSS level. If OSD applies BOTTOM positioning on top of the CSS transform and the pin appears double-offset (tip too high), **remove the CSS `translate(-50%, -100%)` and keep only `placement: BOTTOM`**. Test after the change.

---

## Verification checklist

- [ ] Pin tips land on the annotated coordinates at all zoom levels.
- [ ] Clicking the badge fires `highlightAnnotation` and scrolls the panel.
- [ ] Clicking a panel list item pans to the annotation and the correct pin gains `.active`.
- [ ] `drop-shadow` follows the pin shape (badge + tip), not a rectangle.
- [ ] Numbers are optically centered in both `.ann-badge` and `.ip-ann-num`.
- [ ] Active pins lift slightly upward with no scale jump.
- [ ] No regressions to sidebar, info panel, filter pills, or author tools.
