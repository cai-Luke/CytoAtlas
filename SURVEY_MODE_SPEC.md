# CytoAtlas — Survey Mode Implementation Spec

## Overview

Survey mode (`?survey=true`) is a mobile-first, case-level triage assessment tool for
house staff. It is distinct from quiz mode (`?quiz=true`) and shares only the viewer.
The goal is to capture deferral decisions and reasons per case, per shift, to test the
hypothesis that off-shift staff defer at higher rates than senior staff.

All three modes (default, quiz, survey) are mutually exclusive. URL param switching must
strip the other two params before navigating (same pattern as `toggleQuizModeURL()`).

---

## cases.json changes

Add a `survey` boolean field to the case schema:

```json
{
  "id": "Case_20260418_155022",
  ...
  "survey": true
}
```

- `survey: true` — case appears in survey mode rotation
- `survey: false` or field absent — case is excluded from survey rotation
- Default for new cases: absent (i.e. excluded until explicitly opted in)

Only survey-flagged cases are shown when `?survey=true` is active. Non-survey cases are
not shown at all in this mode — no sidebar, no preview grid fallback.

---

## Author mode changes

Add a **"Include in Survey"** toggle to the author panel (alongside existing generate/export
controls). Flips `activeCase.survey` between `true` and `false`. Label clearly:
`Survey eligible` with a checkbox or toggle switch.

The toggle state is exported with the rest of the case JSON via the existing export flow.
No other author mode changes needed.

---

## Session state — shift collection

Shift is collected **once per browser session** via a pre-survey splash screen shown before
the first case. It is stored in `sessionStorage` under `cytoatlas_survey_shift`.

If `sessionStorage` already has a shift value when survey mode loads, skip the splash and
go directly to the first case.

**Shift options (radio, must pick one before proceeding):**
- Day (07:00–15:00)
- Evening (15:00–23:00)
- Night (23:00–07:00)

A "Begin Survey" button is disabled until a shift is selected.

---

## Per-case survey flow

Each survey case presents:

1. **Image** — full-width composite, OpenSeadragon viewer, same as default mode.
   No annotation markers in survey mode. No sidebar. No toolbar rotation controls
   (keep zoom in/out and reset only — unnecessary controls add noise on mobile).

2. **Survey panel** — bottom sheet pinned below the image on mobile. Contains:

### Step 1 — Deferral decision

```
Would you send this case for pathologist review?

  [ Yes ]   [ No ]
```

Both are large tap targets (min 48px height). Tapping either immediately triggers Step 2
(reasons) or submission (if No).

### Step 2 — Reasons (shown only if Yes)

```
Why? (select all that apply)

  [ ] Atypia suspect
  [ ] Malignancy suspect
  [ ] Infectious agents / organisms suspect
  [ ] Unfamiliar morphology
  [ ] Cell clusters / groups
  [ ] Other (optional free text, 100 char max)
```

Multi-select checkboxes. A **Submit** button appears once at least one reason is checked.

### Submission

On submit (Yes path) or No tap:
- POST payload to Apps Script endpoint (see below)
- Show a brief confirmation ("Response recorded") for 1.5s
- Auto-advance to next survey case

If this was the last survey case in the rotation, show an end screen:
```
Survey complete. Thank you.
```
With a "Back to Atlas" link that navigates to `index.html` (no params).

---

## Case rotation

Survey cases are served in a **randomised order per session** (Fisher-Yates shuffle on
the filtered `survey: true` case list at session start). Randomisation is seeded fresh
each session — no persistence.

Progress indicator in the survey panel header:
```
Case 2 of 5
```

No ability to go back to a previous case — forward-only. This is intentional to avoid
response editing.

---

## Mobile layout

Survey mode overrides the default two-column layout. Full-width single column only,
regardless of viewport width.

```
┌─────────────────────────────┐
│                             │
│         OSD Viewer          │  ← fills ~60vh
│     (image dominant)        │
│                             │
├─────────────────────────────┤
│  Case N of M                │
│                             │
│  Would you send this case   │
│  for pathologist review?    │
│                             │
│  [ Yes ]        [ No ]      │
│                             │
│  (reasons expand here)      │
│                             │
│  [ Submit ]                 │
└─────────────────────────────┘
```

- Sidebar: hidden entirely in survey mode
- Preview grid: not used in survey mode
- Viewer toolbar: zoom in/out and reset only (no rotation)
- No case title shown to respondent during survey (avoid anchoring bias)

---

## Data model — Apps Script POST payload

One POST per case submission:

```json
{
  "timestamp": "2026-05-08T14:32:00Z",
  "shift": "Night (23:00–07:00)",
  "case_id": "Case_20260418_155022",
  "specimen_type": "Pleural fluid",
  "defer": true,
  "reasons": ["Malignancy suspect", "Cell clusters / groups"],
  "other_reason": ""
}
```

- `defer: false` submissions have `reasons: []` and `other_reason: ""`
- `timestamp` is ISO 8601 UTC (`new Date().toISOString()`)
- Case title is intentionally excluded from the payload (avoid identifying individual
  respondents indirectly if cases are rare)

---

## Apps Script (Google Sheets)

Create a new Google Sheet. Open Extensions → Apps Script. Replace the default function
with:

```javascript
const SHEET_NAME = 'Responses'; // rename tab to this

function doPost(e) {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName(SHEET_NAME);

  const data = JSON.parse(e.postData.contents);

  // Write header row if sheet is empty
  if (sheet.getLastRow() === 0) {
    sheet.appendRow([
      'Timestamp', 'Shift', 'Case ID', 'Specimen Type',
      'Defer', 'Reasons', 'Other Reason'
    ]);
  }

  sheet.appendRow([
    data.timestamp,
    data.shift,
    data.case_id,
    data.specimen_type,
    data.defer ? 'Yes' : 'No',
    (data.reasons || []).join('; '),
    data.other_reason || ''
  ]);

  return ContentService
    .createTextOutput('ok')
    .setMimeType(ContentService.MimeType.TEXT);
}
```

**Deploy:** Click Deploy → New Deployment → Web App.
- Execute as: **Me**
- Who has access: **Anyone**

Copy the deployment URL. It looks like:
`https://script.google.com/macros/s/AKfycb.../exec`

Store this URL in `index.html` as a JS constant near the top of the survey mode block:
```javascript
const SURVEY_ENDPOINT = 'https://script.google.com/macros/s/YOUR_ID/exec';
```

This is safe to commit — it is a write-only endpoint with no access to the sheet data.

**Fetch call (no-cors required — Apps Script redirects on POST):**

```javascript
async function submitSurveyResponse(payload) {
  try {
    await fetch(SURVEY_ENDPOINT, {
      method: 'POST',
      mode: 'no-cors',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (err) {
    // Silent fail — no-cors means we can't inspect the response anyway
    console.warn('Survey submit error:', err);
  }
}
```

`no-cors` means you will not get a meaningful response back. This is expected and fine
for fire-and-forget survey submission.

---

## Module-level state (survey mode)

```javascript
let surveyShift = null;           // loaded from sessionStorage on mode init
let surveyCases = [];             // shuffled survey-eligible cases
let surveyIdx = 0;                // current position in rotation
let surveyDefer = null;           // true/false, set by Yes/No tap
let surveyReasons = new Set();    // checked reasons for current case
let surveyOther = '';             // other free text for current case
```

Reset `surveyDefer`, `surveyReasons`, `surveyOther` on each case advance.

---

## Integration with existing mode guards

Follow the same pattern as quiz/author mutual exclusivity:

```javascript
function isSurveyMode() {
  return new URLSearchParams(window.location.search).get('survey') === 'true';
}
```

- `?survey=true` must strip `?quiz` and `?author` before activating
- Survey mode disables annotation markers, sidebar, and author controls entirely
- `selectCase()` in survey mode should not update the URL with a case fragment
  (avoid respondents bookmarking mid-survey)

---

## Future extensions (do not implement now)

- Respondent name/ID via URL param (`?survey=true&id=R2`) for named link distribution
- Confidence rating (1–5) alongside yes/no
- Time-on-image tracking (ms from case load to submission)
- Results dashboard in author mode pulling from the Sheet via Apps Script `doGet()`
