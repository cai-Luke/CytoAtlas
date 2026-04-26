# PATCH: Annotation marker centering + zoom-drift fixes
**File:** `atlas.html` only.

---

## Bug 1 — Triangle tip not centered under badge

**Root cause:** The codebase applies `box-sizing: border-box` globally via `* { box-sizing: border-box }`. The CSS border-triangle trick on `.ann-tip` uses `width: 0; height: 0` — but with border-box, the 5+5 px of horizontal borders can't fit inside a 0 px box. The browser collapses the layout width to 0, so the element's position in the flex container is unpredictable and the visible triangle floats off-center.

**Fix:** Override `box-sizing` to `content-box` on `.ann-tip` so that borders are additive (layout width = 10 px, height = 7 px), giving the flex container a real dimension to center.

Locate `.ann-tip {` and add one line:

```css
.ann-tip {
  box-sizing: content-box;          /* ← ADD: overrides global border-box */
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top-width: 7px;
  border-top-style: solid;
}
```

---

## Bug 2 — Pins drift toward top of image on zoom out

**Root cause:** Two independent mechanisms are both shifting the pin upward:

1. `placement: OpenSeadragon.Placement.BOTTOM` — OSD positions the element so its bottom edge is at the target coordinate.
2. `transform: translate(-50%, -100%)` on `.ann-marker` — CSS then shifts the element up by another full element height.

At any zoom level this is a fixed ~33 px screen-pixel error. But 33 screen pixels corresponds to a much larger image-space distance at low zoom than at high zoom, so the pins visually drift away from their features as you zoom out.

**Fix:** Remove the CSS transform from `.ann-marker` entirely. `placement: BOTTOM` already handles all positioning. Also update the `.ann-marker.active` rule which chains off that transform.

**Find and replace `.ann-marker {`:**

```css
/* BEFORE */
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

/* AFTER */
.ann-marker {
  display: flex;
  flex-direction: column;
  align-items: center;
  cursor: pointer;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, .65));
  transition: filter .15s, transform .15s;
  user-select: none;
  font-family: 'DM Sans', sans-serif;
}
```

**Find and replace `.ann-marker.active {`:**

```css
/* BEFORE */
.ann-marker.active {
  transform: translate(-50%, -100%) translateY(-3px);
  filter: drop-shadow(0 5px 14px rgba(0, 0, 0, .85)) brightness(1.15);
}

/* AFTER */
.ann-marker.active {
  transform: translateY(-3px);
  filter: drop-shadow(0 5px 14px rgba(0, 0, 0, .85)) brightness(1.15);
}
```

No JS changes — `placement: BOTTOM` in `addAnnotationOverlays()` is correct and stays as-is.

---

## Verification checklist

- [ ] Triangle tip is horizontally centered under the circular badge at all annotation numbers.
- [ ] Pin tips stay fixed to their image coordinates at all zoom levels (zoom out to minimum, pins should not drift).
- [ ] Active state lifts the pin 3 px upward without any horizontal shift.
- [ ] No other CSS or JS changes.
