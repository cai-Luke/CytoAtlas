# SPEC: Collapsible sidebar for tablet and mobile
**File:** `atlas.html` only.

---

## Behaviour by breakpoint

| Breakpoint | Sidebar default | Mechanism |
|---|---|---|
| Desktop ≥ 1024 px | Open | Inline column; toggle button collapses it with a width transition |
| Tablet 600–1023 px | Closed | Overlay drawer that slides in from the left; backdrop closes it |
| Mobile < 600 px | Closed | Same overlay drawer |

On desktop the sidebar is part of the flex layout (push behaviour — the viewer gains the 220 px when sidebar collapses). On tablet/mobile the sidebar floats above the viewer as a drawer so the viewer never loses viewport space.

---

## Change 1 — Add a toggle button to the header

In the `.header` HTML, insert a hamburger button **before** the logo mark:

```html
<!-- HEADER -->
<div class="header">
  <button class="sb-toggle" id="sb-toggle" onclick="toggleSidebar()" aria-label="Toggle case list">
    <span></span><span></span><span></span>
  </button>
  <div class="logo-mark" onclick="goHome()">Cyto <em>Atlas</em></div>
  ...
```

---

## Change 2 — Add a backdrop div to the body

Inside `.body`, immediately before `.sidebar`:

```html
<div class="body">
  <div class="sb-backdrop" id="sb-backdrop" onclick="closeSidebar()"></div>
  <div class="sidebar" id="sidebar">
  ...
```

---

## Change 3 — CSS additions

Add the following block after the existing `.sb-item.active .sb-item-meta` rule and before `/* ── MAIN AREA ── */`:

```css
/* ── SIDEBAR TOGGLE BUTTON ── */
.sb-toggle {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 4.5px;
  width: 32px;
  height: 32px;
  padding: 6px;
  border: none;
  background: transparent;
  cursor: pointer;
  border-radius: var(--radius);
  flex-shrink: 0;
  transition: background .12s;
}

.sb-toggle:hover {
  background: var(--surface2);
}

.sb-toggle span {
  display: block;
  width: 100%;
  height: 1.5px;
  background: var(--text3);
  border-radius: 2px;
  transition: background .12s;
}

.sb-toggle:hover span {
  background: var(--text);
}

/* ── SIDEBAR BACKDROP (tablet/mobile only) ── */
.sb-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, .55);
  z-index: 49;
  opacity: 0;
  transition: opacity .25s ease;
}

.sb-backdrop.active {
  opacity: 1;
}

/* ── DESKTOP: inline collapse via width transition ── */
@media (min-width: 1024px) {
  .sidebar {
    transition: width .22s ease, border-color .22s ease;
  }

  .sidebar.collapsed {
    width: 0;
    border-right-color: transparent;
  }

  /* Hide all sidebar content instantly when width is collapsing */
  .sidebar.collapsed .sb-section,
  .sidebar.collapsed .sb-list {
    opacity: 0;
    pointer-events: none;
  }
}

/* ── TABLET / MOBILE: overlay drawer ── */
@media (max-width: 1023px) {
  .sidebar {
    position: fixed;
    top: 52px;          /* height of .header */
    left: 0;
    bottom: 0;
    z-index: 50;
    transform: translateX(-100%);
    transition: transform .25s ease;
    /* Keep declared width — just slide it off-screen */
    width: 220px;
    border-right-color: var(--border);
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .sb-backdrop {
    display: block;     /* exists in DOM; only visible when .active */
    top: 52px;          /* start below the header */
  }
}

/* ── HIDE filter pills and stat on very small screens ── */
@media (max-width: 599px) {
  .stat-pill { display: none; }
  .filter-pills { display: none; }
  .logo-sub { display: none; }
  .logo-sep { display: none; }
}
```

---

## Change 4 — CSS: add `id="sidebar"` to sidebar element

The JS below targets `#sidebar`. Confirm the sidebar div has `id="sidebar"` (add it if absent):

```html
<div class="sidebar" id="sidebar">
```

---

## Change 5 — JS: sidebar state management

Add these functions in the `<script>` block. Place them after the `goHome()` function:

```javascript
// ─────────────────────────────────────────────────────────────────────────
// Sidebar collapse / drawer
// ─────────────────────────────────────────────────────────────────────────
function isOverlayMode() {
  return window.innerWidth < 1024;
}

function toggleSidebar() {
  if (isOverlayMode()) {
    const isOpen = document.getElementById('sidebar').classList.contains('open');
    isOpen ? closeSidebar() : openSidebar();
  } else {
    // Desktop: toggle collapsed class
    document.getElementById('sidebar').classList.toggle('collapsed');
  }
}

function openSidebar() {
  const sb = document.getElementById('sidebar');
  const bd = document.getElementById('sb-backdrop');
  sb.classList.add('open');
  bd.classList.add('active');
}

function closeSidebar() {
  const sb = document.getElementById('sidebar');
  const bd = document.getElementById('sb-backdrop');
  sb.classList.remove('open');
  bd.classList.remove('active');
}

// Close drawer automatically after selecting a case on overlay mode
// Hook into the existing selectCase function:
// In the existing selectCase(c) function, add one line at the top:
//   if (isOverlayMode()) closeSidebar();
```

**Also** update the existing `selectCase()` function by adding the auto-close line:

```javascript
// BEFORE
function selectCase(c) {
  activeCase = c;
  buildSidebar();
  showInfoPanel(c);
  loadViewer(c);
}

// AFTER
function selectCase(c) {
  if (isOverlayMode()) closeSidebar();   // ← ADD
  activeCase = c;
  buildSidebar();
  showInfoPanel(c);
  loadViewer(c);
}
```

---

## Change 6 — Initial state on page load

At the end of the `init()` function, after the sidebar and filter pills are built, set the initial state based on viewport:

```javascript
// At the bottom of the try block in init(), before the setTimeout transition:
if (window.innerWidth < 1024) {
  // Start closed on tablet/mobile — no class needed, default state is translateX(-100%)
} else {
  // Desktop: sidebar starts open, nothing to do
}
```

This is a no-op comment block — the default CSS state already handles this. Include it as documentation only.

---

## Verification checklist

- [ ] Desktop ≥ 1024 px: toggle button collapses/expands sidebar inline; viewer gains the freed space smoothly.
- [ ] Tablet/mobile < 1024 px: sidebar is hidden on load; toggle button slides it in as an overlay drawer; backdrop visible; tapping backdrop closes it.
- [ ] Selecting a case on tablet/mobile closes the drawer automatically.
- [ ] Filter pills and logo sub are hidden on < 600 px (header not overcrowded).
- [ ] `goHome()` still works correctly on all breakpoints.
- [ ] Author panel, info panel, and OSD viewer unaffected.
- [ ] No z-index conflicts with the about modal (z-index 600) or toast (z-index 700).
