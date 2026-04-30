# CytoAtlas — Scale Bar & Measurement Tool

Planning document for the Architect (Claude web/app).
Hand to the CytoAtlas implementer once reviewed.

---

## Background

BenchVision now writes `px_per_um` (pixels per micrometre at capture magnification),
`calibration_px_per_um`, and `calibration_magnification` into `stitch_manifest.json`
`case_metadata` after the Scale Bar Foundation change (April 2026). This value flows
into `cases.json` during the standard publishing step and unlocks two viewer features
described below.

---

## 1. cases.json schema update

Add `px_per_um` as an optional top-level field on each case entry. Absent or `0`
means calibration data is unavailable — both features degrade gracefully to hidden.

```json
{
  "id": "Case_20260428_085918",
  "magnification": "50x",
  "px_per_um": 6.34,
  ...
}
```

The value is copied directly from `case_metadata.px_per_um` in the manifest during
the Antigravity publishing step (`cases.json` update). No derivation needed at the
viewer side — the value is already at capture magnification.

---

## 2. Dynamic Scale Bar

### Behaviour

- Displayed in the **bottom-left** corner of the OpenSeadragon viewer, overlaid on
  the image, not on the surrounding chrome.
- Updates continuously on `viewport-change` (pan/zoom) and on initial `open`.
- Shows a horizontal line with a label: `──── 50 µm` (or whatever round value fits).
- Hidden if `px_per_um` is absent or zero for the current case.
- Does not interfere with annotation markers or the zoom toolbar.

### Round-value selection

Pick the largest value from the candidate list whose rendered bar width falls
between `BAR_MIN_PX` (60) and `BAR_MAX_PX` (180) at the current zoom:

```
candidates = [1, 2, 5, 10, 20, 25, 50, 100, 200, 500]  // µm
```

If none fit, use the candidate that minimises distance to the target midpoint
(`(BAR_MIN_PX + BAR_MAX_PX) / 2`).

### OpenSeadragon coordinate math

At any zoom level, the number of screen pixels per image pixel is:

```javascript
function screenPxPerImagePx(viewer) {
    // OSD viewport zoom is expressed relative to "home" (fit-to-container).
    // Converting a 1-image-pixel horizontal segment to screen pixels:
    const imgPt0 = new OpenSeadragon.Point(0, 0);
    const imgPt1 = new OpenSeadragon.Point(1, 0);
    const item   = viewer.world.getItemAt(0);
    const vp0    = item.imageToViewportCoordinates(imgPt0);
    const vp1    = item.imageToViewportCoordinates(imgPt1);
    const sc0    = viewer.viewport.viewportToViewerElementCoordinates(vp0);
    const sc1    = viewer.viewport.viewportToViewerElementCoordinates(vp1);
    return sc1.x - sc0.x;   // screen pixels per image pixel at current zoom
}
```

Then:

```javascript
const sppu    = screenPxPerImagePx(viewer) * caseData.px_per_um; // screen px per µm
const barUm   = pickRoundValue(sppu, BAR_MIN_PX, BAR_MAX_PX, candidates);
const barPx   = Math.round(barUm * sppu);
```

### DOM structure

A single `<div id="scale-bar-overlay">` absolutely positioned over the viewer
container. Contains two children: a `<div class="scale-bar-line">` (the bar itself,
width set in JS) and a `<span class="scale-bar-label">` (`"50 µm"`). Use the actual
µ character — this is HTML, not cv2.

Position: `bottom: 18px; left: 18px`. Z-index above the OSD canvas but below
annotation markers and the toolbar.

Styling: white bar, 2px solid, with a thin drop-shadow for legibility on bright
backgrounds. Label above the bar, centred, same white-on-shadow treatment.

---

## 3. Click-to-Measure Ruler

### Behaviour

- **Mode toggle**: a ruler icon button in the toolbar (or a keyboard shortcut, `m`).
  When active, the cursor changes to crosshair and the toolbar button is highlighted.
  Panning is disabled while the tool is active.
- **Two-click interaction**: first click sets point A, second click sets point B,
  draws the measurement line, and displays the distance. A third click resets and
  starts a new measurement from the new point A.
- **Display**: a line drawn on a `<canvas>` overlay (same size as the OSD viewer
  element), with the distance label floating at the midpoint: `14.3 µm`. Endpoint
  dots at A and B.
- **Escape** or toggling the ruler button off clears the current measurement and
  returns to normal pan/zoom mode.
- Hidden/disabled if `px_per_um` is absent or zero.

### Coordinate conversion

OSD pointer events give screen coordinates. Convert to image pixels:

```javascript
function screenToImagePx(viewer, screenX, screenY) {
    const viewerEl  = viewer.element;
    const rect      = viewerEl.getBoundingClientRect();
    const viewerPt  = new OpenSeadragon.Point(screenX - rect.left, screenY - rect.top);
    const viewportPt = viewer.viewport.pointFromPixel(viewerPt);
    const item       = viewer.world.getItemAt(0);
    return item.viewportToImageCoordinates(viewportPt);   // image pixels
}
```

Distance in µm:

```javascript
const dx      = imgB.x - imgA.x;   // image pixels
const dy      = imgB.y - imgA.y;
const distUm  = Math.sqrt(dx*dx + dy*dy) / caseData.px_per_um;
```

For the canvas overlay line, convert A and B back from image → viewport → screen
at draw time (called on every `viewport-change`) so the line stays pinned to the
correct image locations as the user pans/zooms after placing a measurement.

### Canvas overlay

A `<canvas>` element absolutely positioned over the OSD viewer, same dimensions,
`pointer-events: none` when in pan mode, `pointer-events: all` when ruler is active.
The canvas is cleared and redrawn on every OSD `viewport-change` event while a
measurement is active. Redraw is a no-op when ruler is inactive with no pending
measurement.

---

## 4. Implementation notes

- Both features read `caseData.px_per_um` from the currently loaded case in
  `cases.json`. Hook into the existing case-load event / function that switches
  the viewer to a new case.
- Register the `viewport-change` handler once on viewer init; inside it, check
  `currentCase.px_per_um` to decide whether to update the scale bar or redraw
  the ruler canvas.
- No new dependencies. Canvas and DOM overlays only.
- Immutable constraints (CSS variables, annotation marker colours, OSD CDN pin,
  font imports) are not touched.

---

## 5. Publishing pipeline update

When Antigravity adds a new case to `cases.json`, it must copy `px_per_um` from
`stitch_manifest.json` → `case_metadata.px_per_um` into the new `cases.json` entry.
If the field is absent from the manifest (pre-calibration cases), omit it from
`cases.json` — do not write `0` or `null`.
