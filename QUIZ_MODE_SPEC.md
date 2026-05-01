# CytoAtlas — Quiz Mode Implementation Spec

**Target file:** `index.html` (single-file app, ~3991 lines)  
**Implementation style:** Targeted `str_replace` patches only. Never re-emit the full file.  
**Constraint:** Read `CLAUDE.md` before making any changes. Honor all "Do Not Modify" blocks.

---

## Overview

Add a `?quiz=true` URL mode that transforms the viewer into a teaching survey tool.
When active, the info panel hides interpretation and annotation labels, replacing them
with a per-region response form. Instructors can step through annotation markers, type
observations, and optionally reveal the annotated label + description for each region.

Pattern mirrors the existing `?author=true` mode exactly: URL param → module-level boolean
→ conditional branches in existing render functions → hidden toggle in the About modal.

---

## 1. Module-level state (patch into existing State block, ~line 2522)

Add immediately after the `IS_AUTHOR` line:

```js
const IS_QUIZ = new URLSearchParams(location.search).has('quiz');

// Quiz session state — reset on each selectCase()
let quizCurrentIdx = 0;       // 0-based index of the annotation being quizzed
let quizResponses  = [];       // string[] — one entry per annotation (persists within session)
let quizRevealed   = [];       // boolean[] — whether "Reveal" was clicked for each annotation
```

---

## 2. Header badge (patch `index.html` HTML, ~line 2360)

The existing markup is:
```html
<div class="author-badge" id="author-badge">Author Mode</div>
<button class="about-btn" onclick="openAbout()">ⓘ About</button>
```

Add a quiz badge directly after `author-badge`:
```html
<div class="quiz-badge" id="quiz-badge">Quiz Mode</div>
```

---

## 3. CSS — add to the `<style>` block

Append near the existing `.author-badge` styles. Find that rule and add after it:

```css
/* ── QUIZ BADGE (header) ── */
.quiz-badge {
  display: none;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  letter-spacing: .8px;
  text-transform: uppercase;
  color: var(--amber);
  border: 1px solid var(--amber-dim);
  background: rgba(251,191,36,.08);
  border-radius: 4px;
  padding: 3px 8px;
}
.quiz-badge.visible { display: block; }

/* ── QUIZ PANEL (inside info-panel, mirrors .author-panel) ── */
.quiz-panel {
  display: none;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  border-top: 1px solid var(--border);
  background: var(--surface2);
  flex-shrink: 0;
}
.quiz-panel.visible { display: flex; }

.qp-label {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: .8px;
  color: var(--amber);
}

.qp-progress {
  display: flex;
  align-items: center;
  gap: 8px;
}

.qp-progress-bar-wrap {
  flex: 1;
  height: 3px;
  background: var(--border2);
  border-radius: 2px;
  overflow: hidden;
}

.qp-progress-bar {
  height: 100%;
  background: var(--amber);
  border-radius: 2px;
  transition: width .3s ease;
}

.qp-progress-label {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--text4);
  white-space: nowrap;
}

.qp-region-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text2);
}

.qp-textarea {
  width: 100%;
  min-height: 72px;
  max-height: 140px;
  resize: vertical;
  padding: 8px 10px;
  background: var(--surface);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  color: var(--text);
  line-height: 1.5;
  outline: none;
  transition: border-color .15s;
}
.qp-textarea:focus { border-color: var(--accent); }
.qp-textarea::placeholder { color: var(--text4); }

.qp-btn-row {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.qp-btn {
  padding: 5px 10px;
  font-size: 12px;
  font-family: 'DM Sans', sans-serif;
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  background: transparent;
  color: var(--text3);
  cursor: pointer;
  transition: all .15s;
}
.qp-btn:hover { color: var(--text); border-color: var(--accent); }
.qp-btn.primary {
  border-color: var(--accent);
  color: var(--accent);
}
.qp-btn.primary:hover {
  background: var(--accent);
  color: #0f1117;
}
.qp-btn.reveal-active {
  border-color: var(--amber);
  color: var(--amber);
  background: rgba(251,191,36,.08);
}

/* Revealed answer block */
.qp-reveal-block {
  display: none;
  flex-direction: column;
  gap: 4px;
  padding: 10px 12px;
  background: var(--surface3);
  border: 1px solid var(--border2);
  border-radius: var(--radius);
  margin-top: 2px;
}
.qp-reveal-block.visible { display: flex; }

.qp-reveal-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--amber);
}
.qp-reveal-desc {
  font-size: 12px;
  color: var(--text2);
  line-height: 1.6;
}

/* Quiz mode — suppress annotation labels in the panel list */
.quiz-ann-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
  transition: background .15s;
  border: 1px solid transparent;
}
.quiz-ann-item:hover { background: var(--surface2); }
.quiz-ann-item.active { border-color: var(--accent); background: var(--accent-dim); }
.quiz-ann-item.current-q { border-color: var(--amber); }

.quiz-ann-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  font-weight: 500;
  background: var(--surface3);
  border: 1.5px solid var(--border2);
  color: var(--text3);
  flex-shrink: 0;
}
.quiz-ann-status {
  font-family: 'DM Mono', monospace;
  font-size: 10px;
  color: var(--text4);
}
.quiz-ann-status.answered { color: var(--green); }
```

---

## 4. HTML — quiz panel inside info-panel

The existing `#info-panel` ends with `.author-panel`. Add `#quiz-panel` immediately
after `#author-panel` (before the closing `</div>` of `#info-panel`).

Find this closing sequence in `index.html`:
```html
            <div class="ap-status" id="ap-status"></div>
          </div>
        </div>
      </div>
    </div>
```

Insert `#quiz-panel` between `</div><!-- /author-panel -->` and `</div><!-- /info-panel -->`:

```html
          <!-- QUIZ PANEL -->
          <div class="quiz-panel" id="quiz-panel">
            <div class="qp-label">✦ Quiz Mode</div>
            <div class="qp-progress">
              <div class="qp-progress-bar-wrap">
                <div class="qp-progress-bar" id="qp-progress-bar"></div>
              </div>
              <span class="qp-progress-label" id="qp-progress-label">0 / 0</span>
            </div>
            <div class="qp-region-label" id="qp-region-label">Region 1</div>
            <textarea class="qp-textarea" id="qp-textarea"
                      placeholder="Describe what you see in this region…"></textarea>
            <div class="qp-btn-row">
              <button class="qp-btn" id="qp-prev" onclick="quizStep(-1)">← Prev</button>
              <button class="qp-btn" id="qp-next" onclick="quizStep(1)">Next →</button>
              <button class="qp-btn primary" onclick="quizFocus()">Focus</button>
              <button class="qp-btn" id="qp-reveal" onclick="quizToggleReveal()">Reveal</button>
            </div>
            <div class="qp-reveal-block" id="qp-reveal-block">
              <div class="qp-reveal-label" id="qp-reveal-label"></div>
              <div class="qp-reveal-desc" id="qp-reveal-desc"></div>
            </div>
          </div>
```

---

## 5. About modal — Toggle Quiz Mode button

Find the existing "Toggle Author Mode" button line in the about modal:
```html
          <button onclick="toggleAuthorModeURL()" ...>Toggle Author Mode</button>
```

Add a "Toggle Quiz Mode" button immediately after it (on a new line, same styling):
```html
          <button onclick="toggleQuizModeURL()" style="background:transparent; border:1px solid var(--border2); color:var(--text4); border-radius:4px; padding:3px 8px; cursor:pointer; font-family:inherit; font-size:10px; transition:all 0.15s;" onmouseover="this.style.color='var(--text)'; this.style.borderColor='var(--amber)';" onmouseout="this.style.color='var(--text4)'; this.style.borderColor='var(--border2)';">Toggle Quiz Mode</button>
```

---

## 6. JavaScript — new functions and patches

### 6a. `toggleQuizModeURL()` — add near `toggleAuthorModeURL()`

```js
function toggleQuizModeURL() {
  const url = new URL(window.location.href);
  if (url.searchParams.has('quiz')) {
    url.searchParams.delete('quiz');
  } else {
    url.searchParams.set('quiz', 'true');
    url.searchParams.delete('author'); // quiz and author are mutually exclusive
  }
  window.location.href = url.toString();
}
```

### 6b. `init()` — activate quiz badge

Find the existing block in `init()`:
```js
if (IS_AUTHOR) {
  document.getElementById('author-badge').classList.add('visible');
  ...
}
```

Add after that block:
```js
if (IS_QUIZ) {
  document.getElementById('quiz-badge').classList.add('visible');
}
```

### 6c. `selectCase()` — reset quiz state

Find `selectCase(c)`. After `activeCase = c;` add:
```js
if (IS_QUIZ) {
  const n = (c.annotations || []).length;
  quizCurrentIdx = 0;
  quizResponses  = Array(n).fill('');
  quizRevealed   = Array(n).fill(false);
}
```

### 6d. `showInfoPanel(c)` — hide interpretation and show quiz panel

In `showInfoPanel(c)`, the interpretation block is:
```js
const interpEl = document.getElementById('ip-interp'), aiBadge = document.getElementById('ip-ai-badge-wrap');
if (IS_AUTHOR) {
  ...
} else {
  if (c.interpretation && c.interpretation.trim()) {
    ...
  } else {
    ...
  }
}
```

Wrap the entire else branch (the non-author branch) so that if `IS_QUIZ` is true,
the interpretation section is hidden instead:

```js
const interpEl = document.getElementById('ip-interp'), aiBadge = document.getElementById('ip-ai-badge-wrap');
if (IS_AUTHOR) {
  interpEl.innerHTML = `<textarea ...>${c.interpretation || ''}</textarea>`;
  interpEl.classList.remove('ai-draft'); aiBadge.style.display = 'none';
} else if (IS_QUIZ) {
  // Hide interpretation entirely in quiz mode
  interpEl.closest('div').style.display = 'none';
  aiBadge.style.display = 'none';
} else {
  if (c.interpretation && c.interpretation.trim()) {
    interpEl.innerHTML = c.interpretation;
    interpEl.classList.toggle('ai-draft', !!c.ai_generated);
    aiBadge.style.display = c.ai_generated ? '' : 'none';
  } else {
    interpEl.innerHTML = '<span class="ip-empty">No interpretation yet.</span>';
    interpEl.classList.remove('ai-draft'); aiBadge.style.display = 'none';
  }
}
```

Also at the end of `showInfoPanel(c)`, after the author-panel block, show/hide quiz panel:
```js
const qp = document.getElementById('quiz-panel');
if (IS_QUIZ) {
  qp.classList.add('visible');
  renderQuizPanel(c);
} else {
  qp.classList.remove('visible');
}
```

### 6e. `renderAnnotationList(c)` — quiz mode branch

In `renderAnnotationList(c)`, the existing logic has an `if (IS_AUTHOR)` branch and an
else branch that renders full label + description. Add a quiz mode branch:

```js
function renderAnnotationList(c) {
  const list = document.getElementById('ip-ann-list');
  if (!c.annotations || c.annotations.length === 0) {
    list.innerHTML = '<div class="ip-empty">No annotations yet.</div>';
    // author-only add button omitted here for brevity — keep existing logic
    return;
  }
  list.innerHTML = '';

  if (IS_QUIZ) {
    // Quiz mode: show numbered items only; no labels or descriptions revealed here.
    // The quiz panel below handles focus / reveal.
    c.annotations.forEach((ann, i) => {
      const item = document.createElement('div');
      item.className = 'quiz-ann-item';
      if (i === quizCurrentIdx) item.classList.add('current-q');
      item.onclick = () => { quizGoTo(i); };

      const hasResponse = quizResponses[i] && quizResponses[i].trim().length > 0;
      const statusText = hasResponse ? '✓ response' : 'no response';
      item.innerHTML = `
        <span class="quiz-ann-num">${i + 1}</span>
        <span class="quiz-ann-status ${hasResponse ? 'answered' : ''}">${statusText}</span>`;
      list.appendChild(item);
    });
    return;
  }

  // IS_AUTHOR and default branches — keep existing code exactly as-is
  ...
}
```

**Important:** Keep the existing `IS_AUTHOR` and default `else` branches verbatim inside
the same function. Only prepend the `if (IS_QUIZ)` early-return branch.

### 6f. `addAnnotationOverlays(c)` — suppress tooltip label in quiz mode

In `addAnnotationOverlays(c)`, the `mouseenter` handler sets tooltip text to `ann.label`:
```js
tt.textContent = ann.label;
```

Patch it to:
```js
tt.textContent = IS_QUIZ ? `Region ${i + 1}` : ann.label;
```

### 6g. Quiz panel render and interaction functions — add as a new section

Add a new JS section after the `// Author mode — Gemini` section:

```js
// ─────────────────────────────────────────────────────────────────────────
// Quiz mode
// ─────────────────────────────────────────────────────────────────────────

function renderQuizPanel(c) {
  const anns = c.annotations || [];
  const n = anns.length;
  if (n === 0) {
    document.getElementById('quiz-panel').classList.remove('visible');
    return;
  }

  const idx = quizCurrentIdx;

  // Progress
  const answered = quizResponses.filter(r => r && r.trim().length > 0).length;
  document.getElementById('qp-progress-bar').style.width = `${n > 0 ? (answered / n) * 100 : 0}%`;
  document.getElementById('qp-progress-label').textContent = `${answered} / ${n}`;
  document.getElementById('qp-region-label').textContent = `Region ${idx + 1} of ${n}`;

  // Textarea — save on input, restore existing response
  const ta = document.getElementById('qp-textarea');
  ta.value = quizResponses[idx] || '';
  ta.oninput = () => {
    quizResponses[idx] = ta.value;
    // Update answered status in the annotation list
    renderAnnotationList(activeCase);
  };

  // Prev / Next buttons
  document.getElementById('qp-prev').disabled = idx === 0;
  document.getElementById('qp-next').disabled = idx === n - 1;

  // Reveal state
  const revealBlock = document.getElementById('qp-reveal-block');
  const revealBtn   = document.getElementById('qp-reveal');
  if (quizRevealed[idx]) {
    revealBlock.classList.add('visible');
    revealBtn.classList.add('reveal-active');
    revealBtn.textContent = 'Hide';
    document.getElementById('qp-reveal-label').textContent = anns[idx].label || '';
    document.getElementById('qp-reveal-desc').textContent  = anns[idx].description || '';
  } else {
    revealBlock.classList.remove('visible');
    revealBtn.classList.remove('reveal-active');
    revealBtn.textContent = 'Reveal';
    document.getElementById('qp-reveal-label').textContent = '';
    document.getElementById('qp-reveal-desc').textContent  = '';
  }

  // Highlight the active annotation on the slide
  highlightAnnotation(idx);
}

function quizGoTo(idx) {
  if (!activeCase || !activeCase.annotations) return;
  const n = activeCase.annotations.length;
  quizCurrentIdx = Math.max(0, Math.min(n - 1, idx));
  renderQuizPanel(activeCase);
  renderAnnotationList(activeCase);
  panToAnnotation(quizCurrentIdx);
}

function quizStep(dir) {
  quizGoTo(quizCurrentIdx + dir);
}

function quizFocus() {
  panToAnnotation(quizCurrentIdx);
}

function quizToggleReveal() {
  quizRevealed[quizCurrentIdx] = !quizRevealed[quizCurrentIdx];
  renderQuizPanel(activeCase);
}
```

---

## 7. Restore interpretation div visibility on case change

Because quiz mode hides the interpretation div with `style.display = 'none'` on the parent,
the non-quiz path needs to restore it. In `showInfoPanel(c)`, before the interpretation
block, add:

```js
// Restore interpretation section visibility (may have been hidden by quiz mode)
const interpSection = document.getElementById('ip-interp')?.closest('div');
if (interpSection) interpSection.style.display = '';
```

---

## 8. Behaviour summary

| Condition | Interpretation | Ann list | Tooltip on hover | Info panel bottom |
|-----------|---------------|----------|------------------|-------------------|
| Default   | Shown         | Label + description | `ann.label` | hidden |
| Author    | Textarea      | Editable fields | `ann.label` | author-panel |
| Quiz      | Hidden        | Number + ✓/— status | `Region N` | quiz-panel |

---

## 9. Edge cases

- **No annotations:** `renderQuizPanel` early-returns and hides the quiz panel. The
  annotation list shows the existing "No annotations yet." message.
- **Case navigation while in quiz mode:** `selectCase()` resets quiz state before
  `showInfoPanel()` fires, so `renderQuizPanel` always starts at index 0 with a clean slate.
- **Quiz + Author simultaneously:** `toggleQuizModeURL()` deletes `?author` before
  navigating. The URL can only carry one mode param at a time.
- **`IS_QUIZ` in author panel:** The author panel branch checks `IS_AUTHOR` separately;
  since the two modes are mutually exclusive by URL, no special guard is needed.

---

## 10. CLAUDE.md constraints — do not touch

- `callGemini()` and the model string `gemini-3.1-pro-preview`
- OpenSeadragon CDN version
- CSS variables in `:root`
- Font imports
- Annotation coordinate system
- `cases.json` schema (quiz mode reads from it; it does not write)

Quiz mode is read-only with respect to case data. It never modifies `activeCase`.
