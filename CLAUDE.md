# CytoAtlas — Claude Code Instructions

Static GitHub Pages site. Body fluid cytology virtual slide reference.
Live at: https://cai-luke.github.io/CytoAtlas/
Sister project: HemeAtlas (https://cai-luke.github.io/HemeAtlas)

---

## Repo structure

```
CytoAtlas/
├── atlas.html          ← Single-file viewer app (OpenSeadragon + annotation UI)
├── index.html          ← Welcome hub / pipeline explainer (entry point)
├── cases.json          ← Case metadata, annotations, interpretation text
├── CLAUDE.md           ← This file
└── assets/
    ├── tile_r0_c0_full.jpg          ← Eyepiece full-frame (used in splash animation)
    ├── tile_r0_c0.jpg … tile_r2_c2.jpg  ← 3×3 tile set (splash animation)
    └── Case_*_composite_trimmed.jpg ← Stitched composites (one per case)
```

Pipeline scripts (`stitch_composite_v12.py`, `pull_and_ingest.py`, `ingest_case.py`, `trim_composite.py`) live in the PARENT Android app project directory, not in this repo. 
Final handoff artifact is always: `assets/Case_<timestamp>_composite_trimmed.jpg`

---

## Design system

Do not modify these — they are intentionally consistent with HemeAtlas.

**Fonts (Google Fonts, already imported):**
- `Instrument Serif` — display headings, logo mark, italic emphasis
- `DM Sans` — body, UI labels, buttons
- `DM Mono` — monospace labels, eyebrow text, metadata

**CSS variables (defined in `:root`):**
```
--bg: #0e1118          background
--surface: #1c2133     card / panel background
--surface2: #232a3d    nested surface
--surface3: #2a3150    deep nested
--border: #2e3655      default border
--border2: #3a4468     stronger border
--text: #eef0f6        primary text
--text2: #b0b9d4       secondary text
--text3: #7a84a0       muted text
--text4: #505870       very muted / labels
--accent: #7c9ef8      primary accent (periwinkle)
--accent-dim: #1e2d5c  accent background tint
--accent-bright: #a0b8ff  accent hover state
```

Annotation marker colors (do not change — also used in HemeAtlas):
`--ann1: #fbbf24` (amber) `--ann2: #34d399` (emerald) `--ann3: #f87171` (rose)
`--ann4: #a78bfa` (violet) `--ann5: #38bdf8` (sky)

---

## Do not modify

- **OpenSeadragon CDN** in `index.html`: `cdnjs.cloudflare.com/ajax/libs/openseadragon/4.1.1/`
  Tested and working. Do not bump the version without explicit instruction.
- **Annotation coordinate system**: fractional 0–1, origin top-left, x left→right, y top→bottom.
  Used in `cases.json` and the marker placement logic in `index.html`. Do not change the convention.
- **CSS variables listed above** — changes here break HemeAtlas visual consistency.
- **Font imports** — do not add, remove, or swap fonts.
- **`cases.json` structure** — see schema below before editing.

---

## cases.json schema

```json
{
  "cases": [
    {
      "id": "Case_20260418_155022",
      "title": "Pleural Fluid — 50×",
      "specimen_type": "Pleural fluid",
      "magnification": "50×",
      "grid": "3×3",
      "date": "2026-04-18",
      "image": "assets/Case_20260418_155022_composite_trimmed.jpg",
      "annotations": [
        {
          "x": 0.42,
          "y": 0.35,
          "label": "Reactive mesothelial cell",
          "description": "2–3 sentences of teaching commentary."
        }
      ],
      "interpretation": "Overall case interpretation paragraph.",
      "ai_generated": true
    }
  ]
}
```

`ai_generated: false` removes the "AI-generated draft" badge from the viewer.
`annotations` may be an empty array if not yet annotated.

---

## Author mode

Append `?author=true` to the URL to enable annotation authoring tools (Gemini API key input,
generate/reroll/export buttons). Do not expose this flow to normal visitors — it is intentionally
unlisted.

---

## Adding a case

1. Run `stitch_composite_v12.py` and `trim_composite.py` on the case directory (done outside this repo).
2. Copy `{case_id}_composite_trimmed.jpg` to `assets/`.
3. Add a new entry to `cases.json` with `annotations: []` and `ai_generated: true`.
4. Open `?author=true`, select the case, generate annotations with Gemini, export JSON, paste back into `cases.json`.
5. Replace `interpretation` and set `ai_generated: false` once pathologist commentary is written.

---

## Splash animation (splash.html)

The pipeline animation uses real tile images from Case_20260418_155022 (3×3 pleural fluid).
Asset paths in the animation are relative: `assets/tile_r0_c0_full.jpg`, `assets/tile_r0_c0.jpg`
through `assets/tile_r2_c2.jpg`, and `assets/Case_20260418_155022_composite_trimmed.jpg`.

The animation is self-contained JS — no external dependencies. Timing constants are at the
top of the `PipelineAnim` class (`this.TOTAL`, tile delay values). The ORB match point
coordinates in `drawOrbFrame()` are hardcoded relative to the grid's known position in the
4:3 stage (grid occupies x: 12.5%–87.5%, seams at x=37.5%, 62.5%, y=33.3%, 66.7%).

---

## Gemini API

Model string: `gemini-3.1-pro` (hardcoded in `callGemini()` in `index.html`).
If this model is deprecated, update the model string — it is the only change needed.
The API key is entered by the user at runtime and stored in `localStorage` under
`cytoatlas_gemini_key`. It is never committed to the repo.

---

## Gemini-Authored / API-Verified Code — Do Not Modify Without Explicit Instruction

The following sections contain API details that postdate Claude's knowledge cutoff
or reflect live API testing. Do not "correct" model names, endpoint paths, or request
schemas in these blocks. Each contains an inline comment explaining the decisions made.
Treat that comment as authoritative and do not second-guess it:

- `atlas.html` → `callGemini()` — Gemini API call for annotation generation. Uses
  `gemini-3.1-pro` model string. Intentional and verified working. Do not change
  the model name or generation config schema.

If a bug is suspected in this function, flag it to Luke rather than making a unilateral
change. Luke will verify against the live API or consult Gemini directly.
