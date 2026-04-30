# CytoAtlas Feature Specs — UX Improvements

All changes are to `index.html` only unless stated. Immutable constraints (CSS
variables, fonts, annotation colours, OSD CDN pin, cases.json schema) are not
touched. `px_per_um` field addition to `cases.json` is covered separately in
`CYTOATLAS_SCALE_MEASUREMENT.md`.

---

## Spec 1 — Scale Bar & Measurement Ruler

Implement exactly as described in `CYTOATLAS_SCALE_MEASUREMENT.md`. Notes on
anchoring into the existing codebase:

**State:** Add `let currentCase = null` alias or reuse `activeCase` — the planning
doc's `caseData` references whichever variable holds the active case object. Use
`activeCase` (already exists).

**Scale bar:** Insert `<div id="scale-bar">` inside `#viewer-wrap`, absolutely
positioned. Create once in HTML, show/hide in `loadViewer()` / `hideViewer()`.
Update on OSD `viewport-change` and `open` events. Hide (display: none) when
`activeCase.px_per_um` is absent or zero.

**Ruler canvas:** Insert `<canvas id="ruler-canvas">` inside `#viewer-wrap`,
same dimensions as `#osd-viewer`, `position: absolute; inset: 0`. Add ruler toggle
button to the viewer toolbar (Spec 2 below) — an icon button using the ⊹ or ↔
glyph, highlights with `--accent` when active. Ruler state resets in `loadViewer()`.

**z-index stack (bottom → top):**
```
OSD canvas          (OSD managed)
scale-bar-overlay   z-index: 8
ruler-canvas        z-index: 9
ann-marker overlays (OSD managed, ~10)
viewer toolbar      z-index: 15
edit-layer          z-index: 20
```

---

## Spec 2 — Viewer Controls Toolbar

*This spec supersedes `SPEC_viewer-controls-and-preview-grid.md` § Feature A if
not yet implemented. If already implemented, extend the existing toolbar.*

### Toolbar button order (left → right)

| Element | Glyph | Action |
|---------|-------|--------|
| Rotate CCW | ↺ | `viewport.setRotation(getRotation() - 90)` |
| Zoom Out | − | `viewport.zoomBy(0.6, null, true)` |
| Zoom indicator | — | Read-only label, e.g. **4.2×** |
| Zoom In | + | `viewport.zoomBy(1.6, null, true)` |
| Rotate CW | ↻ | `viewport.setRotation(getRotation() + 90)` |
| Reset | ⌂ | `viewport.goHome(true); viewport.setRotation(0)` |
| Ruler | ↔ | Toggle measure mode (Spec 1). Hidden if no `px_per_um`. |
| Brightness | ☀ | Toggle brightness popover (Spec 5). |

### Zoom indicator

`viewer.addHandler('zoom', () => { ... })` — compute
`(viewer.viewport.getZoom(true) / viewer.viewport.getHomeZoom()).toFixed(1) + '×'`.
Font: `DM Mono` 11px, `--text2`, min-width 44px, text-align center.

### Rotation

90° steps. `viewport.getRotation()` returns current degrees. Reset to 0 in
`loadViewer()` before creating the new viewer instance. After implementing Spec 3
(chip counter-rotation), verify chips stay upright at each step.

### Toolbar CSS

```css
#viewer-toolbar {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 2px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 4px 6px;
  box-shadow: var(--shadow);
  z-index: 15;
}

#viewer-toolbar button {
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--text3);
  border-radius: var(--radius);
  font-size: 16px;
  cursor: pointer;
  transition: background .12s, color .12s;
}

#viewer-toolbar button:hover {
  background: var(--surface2);
  color: var(--text);
}

#viewer-toolbar button.active {
  background: var(--accent-dim);
  color: var(--accent);
}

#viewer-toolbar .tb-sep {
  width: 1px;
  height: 18px;
  background: var(--border);
  margin: 0 2px;
}
```

Toolbar hidden in `hideViewer()`, shown in the `open` handler of `loadViewer()`.

---

## Spec 3 — Annotation Chip Counter-Rotation

### Problem

`.ann-chip` badges (numbered markers) inherit viewport rotation from their
`.ann-marker` parent overlay and become unreadable when the image is rotated.

### Fix

```js
function updateChipRotations() {
  const deg = viewer ? viewer.viewport.getRotation() : 0;
  document.querySelectorAll('.ann-chip').forEach(el => {
    el.style.transform = `translateY(-100%) rotate(${-deg}deg)`;
  });
}
```

**Hooks:**
1. `viewer.addHandler('rotate', updateChipRotations)` — inside `loadViewer()` after
   viewer creation.
2. Call `updateChipRotations()` at the end of `addAnnotationOverlays()` (after the
   forEach loop).
3. Call `updateChipRotations()` at the end of the existing `open` handler, after
   `addAnnotationOverlays(c)`.

`.edit-chip` elements (author edit mode) are out of scope.

---

## Spec 4 — Annotation Hover Tooltips

### What

On `.ann-marker` hover, show a small tooltip with the annotation label near the
marker. Click behavior unchanged (pan + highlight sidebar item).

### DOM

One singleton tooltip div, added to `#viewer-wrap`:

```html
<div id="ann-tooltip"></div>
```

```css
#ann-tooltip {
  position: absolute;
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text);
  box-shadow: var(--shadow);
  pointer-events: none;
  white-space: nowrap;
  z-index: 12;
  opacity: 0;
  transition: opacity .12s;
}

#ann-tooltip.visible {
  opacity: 1;
}
```

### Behaviour

In `addAnnotationOverlays()`, alongside the existing `el.onclick`, add:

```js
el.addEventListener('mouseenter', e => {
  const tt = document.getElementById('ann-tooltip');
  tt.textContent = ann.label;
  // Position above the marker chip using the OSD overlay element's bounding rect
  const wrapRect = document.getElementById('viewer-wrap').getBoundingClientRect();
  const markerRect = el.getBoundingClientRect();
  tt.style.left = (markerRect.left - wrapRect.left) + 'px';
  tt.style.top  = (markerRect.top  - wrapRect.top - 32) + 'px';
  tt.classList.add('visible');
});

el.addEventListener('mouseleave', () => {
  document.getElementById('ann-tooltip').classList.remove('visible');
});
```

Hide tooltip in `clearOverlays()`: `document.getElementById('ann-tooltip').classList.remove('visible')`.

Tooltip is not shown on touch devices (mouseenter doesn't fire on touch; no
additional handling needed).

---

## Spec 5 — Brightness / Contrast / Saturation

### What

A popover with three sliders that apply CSS filters to the OSD canvas. Accessed via
the ☀ button in the viewer toolbar (Spec 2).

### Approach

CSS `filter` applied to `.openseadragon-container`. Three properties: brightness
(0.5–1.5, default 1.0), contrast (0.5–1.5, default 1.0), saturation (0–2,
default 1.0).

### State

```js
let imgFilters = { brightness: 1, contrast: 1, saturation: 1 };
```

Reset to defaults in `loadViewer()`.

### Apply function

```js
function applyImgFilters() {
  const el = document.querySelector('.openseadragon-container');
  if (el) el.style.filter =
    `brightness(${imgFilters.brightness}) contrast(${imgFilters.contrast}) saturate(${imgFilters.saturation})`;
}
```

### Popover DOM

```html
<div id="img-filter-popover">
  <div class="ifp-row">
    <span>Brightness</span>
    <input type="range" id="ifp-brightness" min="0.5" max="1.5" step="0.05" value="1">
  </div>
  <div class="ifp-row">
    <span>Contrast</span>
    <input type="range" id="ifp-contrast" min="0.5" max="1.5" step="0.05" value="1">
  </div>
  <div class="ifp-row">
    <span>Saturation</span>
    <input type="range" id="ifp-saturation" min="0" max="2" step="0.05" value="1">
  </div>
  <button id="ifp-reset">Reset</button>
</div>
```

```css
#img-filter-popover {
  position: absolute;
  bottom: 58px;           /* sits above the toolbar */
  left: 50%;
  transform: translateX(-50%);
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: var(--radius-lg);
  padding: 14px 16px;
  width: 220px;
  box-shadow: var(--shadow-lg);
  z-index: 16;
  display: none;
}

#img-filter-popover.visible { display: block; }

.ifp-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  font-size: 12px;
  color: var(--text3);
}

.ifp-row input[type=range] { flex: 1; accent-color: var(--accent); }

#ifp-reset {
  width: 100%;
  padding: 5px;
  font-size: 12px;
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  background: transparent;
  color: var(--text3);
  cursor: pointer;
  font-family: 'DM Sans', sans-serif;
}

#ifp-reset:hover { color: var(--text); border-color: var(--accent); }
```

Each slider `oninput` updates `imgFilters` and calls `applyImgFilters()`. Reset
button restores defaults, resets slider values, calls `applyImgFilters()`. Clicking
☀ toolbar button toggles `.visible` on `#img-filter-popover`.

Reset `imgFilters` and call `applyImgFilters()` in `loadViewer()`.

---

## Spec 6 — Prev / Next Case Navigation

### What

Two buttons in the info panel that cycle through cases in the current filtered set.

### DOM

Add to the `.ip-header` div, after `#ip-meta-row`:

```html
<div class="ip-nav-row">
  <button class="ip-nav-btn" id="ip-prev" onclick="stepCase(-1)">← Prev</button>
  <span class="ip-nav-count" id="ip-nav-count"></span>
  <button class="ip-nav-btn" id="ip-next" onclick="stepCase(1)">Next →</button>
</div>
```

```css
.ip-nav-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 10px;
  gap: 8px;
}

.ip-nav-btn {
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  background: transparent;
  color: var(--text3);
  cursor: pointer;
  transition: all .12s;
  font-family: 'DM Sans', sans-serif;
}

.ip-nav-btn:hover { color: var(--text); border-color: var(--accent); }
.ip-nav-btn:disabled { opacity: .3; cursor: default; }

.ip-nav-count {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--text4);
}
```

### Logic

Requires `getFilteredCases()` (introduced in preview grid refactor). If that
function doesn't exist yet, inline the same filter logic here.

```js
function stepCase(dir) {
  const filtered = getFilteredCases();
  const idx = filtered.findIndex(c => c.id === activeCase.id);
  if (idx === -1) return;
  const next = filtered[(idx + dir + filtered.length) % filtered.length];
  selectCase(next);
}
```

Update the count label in `showInfoPanel()`:

```js
function updateNavCount() {
  const filtered = getFilteredCases();
  const idx = filtered.findIndex(c => c.id === activeCase.id);
  document.getElementById('ip-nav-count').textContent =
    idx >= 0 ? `${idx + 1} / ${filtered.length}` : '';
}
```

Call `updateNavCount()` at the end of `showInfoPanel()`. Also call it from
`buildSidebar()` when `activeCase` is set (filter pill changes update the count).

Disable `#ip-prev` / `#ip-next` when `filtered.length <= 1`.

---

## Spec 7 — Smooth Viewer Transitions

### What

Eliminate the flash between cases. Instead of destroy/recreate, keep the OSD viewer
alive and swap images using `viewer.addTiledImage()` with opacity crossfade.

### Approach

Refactor `loadViewer()` to use `viewer.world` item management instead of
`viewer.destroy()`.

```js
function loadViewer(c) {
  document.getElementById('viewer-empty').style.display = 'none';
  document.getElementById('osd-viewer').style.display = 'block';
  document.getElementById('viewer-loading').classList.remove('hidden');
  clearOverlays();
  if (editMode) exitEditMode();

  // Reset per-case state
  imgFilters = { brightness: 1, contrast: 1, saturation: 1 };
  applyImgFilters();

  if (!viewer) {
    // First load — create viewer
    viewer = OpenSeadragon({
      id: 'osd-viewer',
      prefixUrl: 'https://cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.1/images/',
      tileSources: { type: 'image', url: c.image },
      showNavigator: true, navigatorPosition: 'BOTTOM_RIGHT', navigatorSizeRatio: 0.15,
      minZoomLevel: 0.5, maxZoomLevel: 20, visibilityRatio: 0.5,
      constrainDuringPan: false, animationTime: 0.4,
      gestureSettingsMouse: { scrollToZoom: true, clickToZoom: false, dblClickToZoom: true },
      gestureSettingsTouch: { pinchToZoom: true, dblClickToZoom: true },
      showZoomControl: false, showHomeControl: false, showFullPageControl: false
    });
    attachViewerHandlers();
  } else {
    // Subsequent loads — swap image
    viewer.viewport.setRotation(0);
    viewer.world.removeAllItems();
    viewer.addTiledImage({ tileSource: { type: 'image', url: c.image }, opacity: 0,
      success: function(e) {
        const item = e.item;
        // Fade in new image
        let opacity = 0;
        const fadeIn = setInterval(() => {
          opacity = Math.min(1, opacity + 0.08);
          item.setOpacity(opacity);
          if (opacity >= 1) {
            clearInterval(fadeIn);
            document.getElementById('viewer-loading').classList.add('hidden');
            addAnnotationOverlays(c);
            updateNavCount();
            updateScaleBar();     // Spec 1, no-op if not yet implemented
            updateChipRotations(); // Spec 3
          }
        }, 16);
      }
    });
    return; // early return — open handler not used on swap
  }
}

function attachViewerHandlers() {
  viewer.addHandler('open', () => {
    document.getElementById('viewer-loading').classList.add('hidden');
    addAnnotationOverlays(activeCase);
    updateChipRotations();
    updateNavCount();
    updateScaleBar();
    document.getElementById('viewer-toolbar').style.display = 'flex';
  });
  viewer.addHandler('open-failed', () => {
    document.querySelector('#viewer-loading div:last-child').textContent = 'Failed to load image';
  });
  viewer.addHandler('rotate', updateChipRotations);
  viewer.addHandler('zoom', updateZoomLabel);
  viewer.addHandler('viewport-change', () => {
    updateScaleBar();      // Spec 1
    redrawRulerCanvas();   // Spec 1
  });
}
```

`hideViewer()` remains: `viewer.destroy(); viewer = null;` — this is only called
from `goHome()` where the viewer is no longer needed at all.

### Loading overlay on swap

During the `removeAllItems` → `addTiledImage` swap the old image is gone
immediately, leaving a blank canvas. Show the loading overlay for this window:
`viewer-loading` is already shown at the top of `loadViewer()`, and is hidden inside
the fadeIn completion callback.

---

## Spec 8 — Mobile Filter Pills

### What

Filter pills are currently hidden at ≤599px. Add them to the sidebar so mobile
users can filter.

### Approach

Add a second pill container in the sidebar, below `.sb-search-wrap`:

```html
<div class="sb-filter-wrap" id="sb-filter-wrap"></div>
```

```css
.sb-filter-wrap {
  display: none;
  padding: 4px 8px 6px;
  flex-wrap: wrap;
  gap: 5px;
}

@media (max-width: 599px) {
  .sb-filter-wrap { display: flex; }
}
```

In `buildFilterPills()`, after populating `#filter-pills`, clone the same pills
into `#sb-filter-wrap`. Each pill's `onclick` still calls `setFilter()` —
`setFilter()` calls `document.querySelectorAll('.filter-pill')` to toggle `.active`,
so the correct pill activates in both locations automatically (both sets share the
same `.filter-pill` class and the `#fp-${type}` id scheme — use `data-filter`
instead of id on sidebar copies to avoid duplicate id violations).

Simplest implementation: in `setFilter()`, toggle `.active` by matching
`dataset.filter` across all `.filter-pill` elements rather than looking up by id.
Update `buildFilterPills()` to set `el.dataset.filter = type` on every pill.

---

## Implementation order

Dependencies exist between specs:

1. **Spec 2** (Toolbar) — build first; Specs 1 and 5 add buttons to it.
2. **Spec 3** (Chip rotation) — can go alongside Spec 2.
3. **Spec 7** (Smooth transitions) — refactors `loadViewer()`; do before Spec 1
   since Spec 1 hooks into `viewport-change` which is registered in
   `attachViewerHandlers()`.
4. **Spec 1** (Scale bar + ruler) — hooks into toolbar (Spec 2) and viewer events
   (Spec 7). Implement last among viewer features.
5. **Specs 4, 5, 6, 8** — independent, any order.

---

## Files modified

`index.html` only. `cases.json` schema update (`px_per_um` field) is handled by the
BenchVision publishing pipeline as documented in `CYTOATLAS_SCALE_MEASUREMENT.md`.
