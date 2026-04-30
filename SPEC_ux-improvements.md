# CytoAtlas Feature Specs — UX Improvements (Amended)

All changes are to `index.html` only unless stated. Immutable constraints (CSS
variables, fonts, annotation colours, OSD CDN pin, cases.json schema) are not
touched. `px_per_um` field addition to `cases.json` is covered separately in
`CYTOATLAS_SCALE_MEASUREMENT.md`.

---

## Spec 1 — Scale Bar & Measurement Ruler

Implement exactly as described in `CYTOATLAS_SCALE_MEASUREMENT.md`, with strict attention to event routing to avoid blocking OpenSeadragon.

**State:** Use `activeCase` (already exists). Add `let measureMode = false;`.

**Scale bar:** Insert `<div id="scale-bar">` inside `#viewer-wrap`, absolutely
positioned. Create once in HTML. Hide (display: none) when `activeCase.px_per_um` is absent or zero.

**Ruler canvas:** Insert `<canvas id="ruler-canvas">` inside `#viewer-wrap`,
same dimensions as `#osd-viewer`, `position: absolute; inset: 0`.
*CRITICAL:* Default to `pointer-events: none`. Only set `pointer-events: auto` when `measureMode === true` to prevent blocking OSD pan/zoom. 

**Toolbar Toggle:** Add ruler toggle button to the viewer toolbar (Spec 2) using the ↔ glyph. When clicked, toggle `measureMode`, update canvas `pointer-events`, and toggle an `.active` class on the button.

**z-index stack (bottom → top):**
OSD canvas          (OSD managed)
scale-bar-overlay   z-index: 8
ruler-canvas        z-index: 9
ann-marker overlays (OSD managed, ~10)
viewer toolbar      z-index: 15
edit-layer          z-index: 20


---

## Spec 2 — Viewer Controls Toolbar

*This spec supersedes `SPEC_viewer-controls-and-preview-grid.md` § Feature A.*

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
`loadViewer()` before swapping the image.

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
```

## Spec 3 — Annotation Chip Counter-Rotation

### Fix

```javascript
function updateChipRotations() {
  const deg = viewer ? viewer.viewport.getRotation() : 0;
  document.querySelectorAll('.ann-chip').forEach(el => {
    // Note: transform-origin MUST be bottom left for the chip to orbit the corner correctly
    el.style.transformOrigin = 'bottom left';
    el.style.transform = `translateY(-100%) rotate(${-deg}deg)`;
  });
}
```

### Hooks:

1. `viewer.addHandler('rotate', updateChipRotations)`
2. End of `addAnnotationOverlays()`
3. In `loadViewer()`, inside the `addTiledImage` success callback.

---

## Spec 4 — Annotation Hover Tooltips

### DOM

#### HTML
```html
<div id="ann-tooltip"></div>
```

#### CSS
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
#ann-tooltip.visible { opacity: 1; }
```

### Behaviour
In `addAnnotationOverlays()`, add:

```javascript
el.addEventListener('mouseenter', e => {
  const tt = document.getElementById('ann-tooltip');
  tt.textContent = ann.label;
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

*CRITICAL:* Hide tooltip on `viewer.addHandler('pan')` and `viewer.addHandler('zoom')` to prevent it from floating in empty space. Hide in `clearOverlays()`.

---

## Spec 5 — Brightness / Contrast / Saturation

### Approach
CSS filter applied to `.openseadragon-container`.

### State & Apply function

```javascript
let imgFilters = { brightness: 1, contrast: 1, saturation: 1 };

function applyImgFilters() {
  const el = document.querySelector('.openseadragon-container');
  if (el) el.style.filter =
    `brightness(${imgFilters.brightness}) contrast(${imgFilters.contrast}) saturate(${imgFilters.saturation})`;
}
```
Reset to defaults and call `applyImgFilters()` in `loadViewer()`.

### Popover DOM

#### HTML
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

#### CSS
```css
#img-filter-popover {
  position: absolute;
  bottom: 58px;
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
.ifp-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px; font-size: 12px; color: var(--text3); }
.ifp-row input[type=range] { flex: 1; accent-color: var(--accent); }
#ifp-reset { width: 100%; padding: 5px; font-size: 12px; border: 1px solid var(--border2); border-radius: var(--radius); background: transparent; color: var(--text3); cursor: pointer; font-family: 'DM Sans', sans-serif; }
#ifp-reset:hover { color: var(--text); border-color: var(--accent); }
```

---

## Spec 6 — Prev / Next Case Navigation

### DOM (in .ip-header)

#### HTML
```html
<div class="ip-nav-row">
  <button class="ip-nav-btn" id="ip-prev" onclick="stepCase(-1)">← Prev</button>
  <span class="ip-nav-count" id="ip-nav-count"></span>
  <button class="ip-nav-btn" id="ip-next" onclick="stepCase(1)">Next →</button>
</div>
```

### Logic

```javascript
function stepCase(dir) {
  const filtered = getFilteredCases();
  if (filtered.length === 0) return;
  
  const idx = filtered.findIndex(c => c.id === activeCase.id);
  // CRITICAL FIX: If activeCase is filtered out, jump to the first item in the new filtered view.
  if (idx === -1) {
    selectCase(filtered[0]);
    return;
  }
  
  const next = filtered[(idx + dir + filtered.length) % filtered.length];
  selectCase(next);
}

function updateNavCount() {
  const filtered = getFilteredCases();
  const idx = filtered.findIndex(c => c.id === activeCase.id);
  document.getElementById('ip-nav-count').textContent =
    idx >= 0 ? `${idx + 1} / ${filtered.length}` : '';
  
  const btnPrev = document.getElementById('ip-prev');
  const btnNext = document.getElementById('ip-next');
  if (btnPrev && btnNext) {
    btnPrev.disabled = filtered.length <= 1;
    btnNext.disabled = filtered.length <= 1;
  }
}
```

---

## Spec 7 — Smooth Viewer Transitions

### Approach
Refactor `loadViewer()` to use `viewer.world` item management. Ensure all per-case initialization runs in the success callback, not just the open handler.

```javascript
function loadViewer(c) {
  document.getElementById('preview-grid').classList.remove('visible');
  document.getElementById('osd-viewer').style.display = 'block';
  document.getElementById('viewer-loading').classList.remove('hidden');
  clearOverlays();
  if (editMode) exitEditMode();

  // Reset per-case state
  imgFilters = { brightness: 1, contrast: 1, saturation: 1 };
  applyImgFilters();
  
  // Reset Ruler/Measure State
  measureMode = false;
  const rulerCanvas = document.getElementById('ruler-canvas');
  if (rulerCanvas) {
      rulerCanvas.style.pointerEvents = 'none';
      rulerCanvas.getContext('2d').clearRect(0, 0, rulerCanvas.width, rulerCanvas.height);
  }
  const rulerBtn = document.querySelector('#viewer-toolbar button[title="Ruler"]');
  if (rulerBtn) rulerBtn.classList.remove('active');

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
    viewerRotation = 0;
    viewer.world.removeAllItems();
    viewer.addTiledImage({ tileSource: { type: 'image', url: c.image }, opacity: 0,
      success: function(e) {
        const item = e.item;
        let opacity = 0;
        const fadeIn = setInterval(() => {
          opacity = Math.min(1, opacity + 0.08);
          item.setOpacity(opacity);
          if (opacity >= 1) {
            clearInterval(fadeIn);
            document.getElementById('viewer-loading').classList.add('hidden');
            
            // CRITICAL FIX: Mirror the 'open' handler logic here for subsequent loads
            addAnnotationOverlays(c);
            updateNavCount();
            if (typeof updateScaleBar === 'function') updateScaleBar();
            updateChipRotations();
            
            const rulerBtn = document.querySelector('#viewer-toolbar button[title="Ruler"]');
            if (rulerBtn) {
               rulerBtn.style.display = c.px_per_um ? 'flex' : 'none';
            }
          }
        }, 16);
      }
    });
  }
}

function attachViewerHandlers() {
  viewer.addHandler('open', () => {
    document.getElementById('viewer-loading').classList.add('hidden');
    addAnnotationOverlays(activeCase);
    updateChipRotations();
    updateNavCount();
    if (typeof updateScaleBar === 'function') updateScaleBar();
    document.getElementById('viewer-toolbar').style.display = 'flex';
    
    const rulerBtn = document.querySelector('#viewer-toolbar button[title="Ruler"]');
    if (rulerBtn) {
       rulerBtn.style.display = activeCase.px_per_um ? 'flex' : 'none';
    }
  });
  viewer.addHandler('open-failed', () => {
    document.querySelector('#viewer-loading div:last-child').textContent = 'Failed to load image';
  });
  viewer.addHandler('rotate', updateChipRotations);
  viewer.addHandler('zoom', () => {
      updateZoomLabel();
      document.getElementById('ann-tooltip')?.classList.remove('visible'); // Spec 4 fix
  });
  viewer.addHandler('pan', () => {
      document.getElementById('ann-tooltip')?.classList.remove('visible'); // Spec 4 fix
  });
  viewer.addHandler('viewport-change', () => {
    if (typeof updateScaleBar === 'function') updateScaleBar();
    if (typeof redrawRulerCanvas === 'function') redrawRulerCanvas(); 
  });
}
```

---

## Spec 8 — Mobile Filter Pills

### Approach

#### HTML
```html
<div class="sb-filter-wrap" id="sb-filter-wrap"></div>
```

#### CSS
```css
.sb-filter-wrap { display: none; padding: 4px 8px 6px; flex-wrap: wrap; gap: 5px; }
@media (max-width: 599px) { .sb-filter-wrap { display: flex; } }
```

In `buildFilterPills()`, set `el.dataset.filter = type` on every pill, and clone the `.filter-pill` elements into `#sb-filter-wrap`. Update `setFilter()` to toggle `.active` by matching `dataset.filter` across all `.filter-pill` elements rather than looking up by id.
