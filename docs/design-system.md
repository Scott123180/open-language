# Open Language — Design System

**Version:** 1.0.0 | **Date:** 2026-03-23

---

## Philosophy

Open Language is a personal language-learning companion — intimate, patient, and focused. The design should feel like a thoughtful tutor's study: warm materials, clean surfaces, calm focus. Nothing competes with the content. The user is here to practice conversation; the UI should be nearly invisible.

**Three guiding principles:**

1. **Warmth over sterility.** Every color, shadow, and surface choice should read as "cozy and trustworthy," not "corporate dashboard." Warm stone neutrals instead of cold grays. Teal instead of corporate blue.
2. **Typography does the work.** Visual hierarchy is built with font weight, size, and color contrast — not decorations, gradients, or illustrations. If you reach for a border or a background to create hierarchy, first ask whether typography can do it instead.
3. **One primary action per screen.** At any moment there is exactly one thing the user should do. Everything else is secondary. Secondary elements step back visually — smaller type, muted color, less shadow.

---

## Design Tokens

All values live in CSS custom properties. Use tokens exclusively in components — never hardcode a hex value or px measurement that has a matching token.

### Color

#### Light Mode

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#faf9f7` | Page background (warm off-white) |
| `--color-bg-alt` | `#f5f3ef` | Hover surfaces, zebra rows |
| `--color-surface` | `#ffffff` | Cards, modals, panels |
| `--color-surface-raised` | `#f5f3ef` | Elevated surfaces within cards |
| `--color-border` | `#e8e4de` | Visible borders (warm gray-beige) |
| `--color-border-subtle` | `#f0ede8` | Dividers, list separators |
| `--color-text` | `#1c1917` | Primary text (warm near-black) |
| `--color-text-muted` | `#78716c` | Secondary text, labels |
| `--color-text-faint` | `#a8a29e` | Placeholder, disabled, timestamps |
| `--color-primary` | `#0d9488` | Primary actions, links, focus rings (teal-600) |
| `--color-primary-hover` | `#0f766e` | Hover state for primary (teal-700) |
| `--color-primary-subtle` | `#ccfbf1` | Selected states, chips, badges |
| `--color-primary-text` | `#134e4a` | Text safe on `--color-primary-subtle` bg |
| `--color-text-on-primary` | `#ffffff` | Text/icons on filled primary buttons |
| `--color-success` | `#16a34a` | Success states |
| `--color-success-subtle` | `#dcfce7` | Success backgrounds |
| `--color-warning` | `#d97706` | Warning states |
| `--color-error` | `#dc2626` | Error states |
| `--color-error-subtle` | `#fef2f2` | Error backgrounds |

#### Dark Mode

The dark palette preserves the warm hue angle of the light palette — backgrounds use `hsl(28, 10%, 9%)` rather than the cold slate `hsl(222, 47%, 11%)`. The result reads as the same room after sunset, not a server room.

| Token | Value | Usage |
|---|---|---|
| `--color-bg` | `#1a1714` | Page background (warm near-black) |
| `--color-bg-alt` | `#211e1a` | Hover surfaces |
| `--color-surface` | `#242019` | Cards, panels |
| `--color-surface-raised` | `#2e2a25` | Elevated surfaces |
| `--color-border` | `#3d3830` | Visible borders |
| `--color-border-subtle` | `#2a2622` | Dividers |
| `--color-text` | `#f5f2ee` | Primary text (warm near-white) |
| `--color-text-muted` | `#a09890` | Secondary text |
| `--color-text-faint` | `#6b6560` | Placeholder, disabled |
| `--color-primary` | `#2dd4bf` | Primary actions, links (teal-300 — brighter for dark bg contrast) |
| `--color-primary-hover` | `#5eead4` | Hover state (teal-200) |
| `--color-primary-subtle` | `#1a3a38` | Selected states |
| `--color-primary-text` | `#99f6e4` | Text on `--color-primary-subtle` bg |
| `--color-text-on-primary` | `#0d1f1e` | Text/icons on filled primary buttons |
| `--color-success` | `#4ade80` | Success states |
| `--color-success-subtle` | `#052e16` | Success backgrounds |
| `--color-warning` | `#fbbf24` | Warning states |
| `--color-error` | `#f87171` | Error states |
| `--color-error-subtle` | `#3b0a0a` | Error backgrounds |

#### Color Rules

- **Never hardcode `#fff` as text on a primary background.** Use `var(--color-text-on-primary)` — in dark mode the primary is light teal and requires dark text.
- **Never use `--color-primary` for large filled surfaces.** It is for interactive elements, links, and highlights only.
- The `--color-success, green` fallback pattern is forbidden. Use `--color-success` only — it is always defined.
- Colored text must meet WCAG AA: 4.5:1 for body text, 3:1 for UI components (buttons, labels).

---

### Typography

#### Typeface

```css
--font-sans: 'Plus Jakarta Sans', 'DM Sans', system-ui, -apple-system, sans-serif;
```

**Plus Jakarta Sans** is a humanist sans-serif with subtly flared terminals and optical warmth. Its open counters and high x-height give excellent legibility at conversation-sized text (14–16px). The slight personality at display sizes (the letterforms show evidence of a calligraphic hand) matches the personal, tutor-like tone of the app.

Load via Google Fonts in `index.html`:
```html
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
```

#### Scale (Major Third ratio, 1.25)

| Token | Value | Usage |
|---|---|---|
| `--text-xs` | `0.75rem / 12px` | Metadata, timestamps, labels |
| `--text-sm` | `0.875rem / 14px` | Secondary UI, nav pills, captions |
| `--text-base` | `1rem / 16px` | Body text, chat messages, inputs |
| `--text-md` | `1.125rem / 18px` | Card titles, subheadings |
| `--text-lg` | `1.375rem / 22px` | Page headings (h2) |
| `--text-xl` | `1.75rem / 28px` | App name, large display (h1) |

#### Weights

| Token | Value | Usage |
|---|---|---|
| `--weight-normal` | `400` | Body text, chat messages |
| `--weight-medium` | `500` | Nav items, labels, secondary hierarchy |
| `--weight-semibold` | `600` | Card titles, button labels, active states |
| `--weight-bold` | `700` | Page headings only |

**Rule:** weights 800–900 are never used. Bold only on headings.

#### Line Heights

| Token | Value | Usage |
|---|---|---|
| `--leading-tight` | `1.2` | Display headings |
| `--leading-snug` | `1.3` | Card titles, UI labels |
| `--leading-normal` | `1.5` | Default, nav, buttons |
| `--leading-relaxed` | `1.6` | Chat messages, body text — critical for reading comfort |

#### Letter Spacing

- Display headings (`--text-lg`, `--text-xl`): `letter-spacing: -0.02em`
- Body text: `letter-spacing: 0` (browser default)
- Small caps / section labels: `letter-spacing: 0.06em`

---

### Spacing

All spacing is multiples of 4px (half-step) or 8px (base grid).

| Token | Value | Usage |
|---|---|---|
| `--space-1` | `4px` | Icon-to-label gaps, micro adjustments |
| `--space-2` | `8px` | Tight internal spacing |
| `--space-3` | `12px` | List item gaps, compact padding |
| `--space-4` | `16px` | Standard component padding |
| `--space-5` | `20px` | Generous component padding |
| `--space-6` | `24px` | Section gaps, card padding |
| `--space-8` | `32px` | Between sections |
| `--space-10` | `40px` | Major section breathing room |
| `--space-12` | `48px` | Page-level vertical rhythm |
| `--space-16` | `64px` | Hero space |

**Rule:** spacing inside a component is always less than spacing between components. A card with 16px internal padding needs 24px+ gap from adjacent elements.

---

### Border Radius

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | `4px` | Tags, badges, inline chips |
| `--radius-md` | `8px` | Buttons, inputs, small cards |
| `--radius-lg` | `12px` | Cards, panels, scenario cards |
| `--radius-xl` | `16px` | Modals, large surfaces |
| `--radius-full` | `9999px` | Pills, nav chips, record button |

The `--radius` alias maps to `--radius-md` for backward compatibility.

---

### Shadows & Elevation

Shadow colors use the warm near-black `rgba(28, 25, 23, ...)` instead of pure black — produces shade-like shadows instead of ink-like ones.

| Token | Value | Usage |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgba(28,25,23,0.06)` | Subtle lift (cards, inputs) |
| `--shadow-md` | `0 2px 8px rgba(28,25,23,0.08), 0 1px 3px rgba(28,25,23,0.06)` | Floating elements |
| `--shadow-lg` | `0 8px 24px rgba(28,25,23,0.10), 0 2px 8px rgba(28,25,23,0.06)` | Popovers, modals |

In dark mode, shadows use higher opacity pure black (the warm dark surface already provides the ambient warmth).

The `--shadow` alias maps to `--shadow-sm` for backward compatibility.

---

### Layout

| Token | Value | Usage |
|---|---|---|
| `--width-narrow` | `360px` | Focused single-item views (flashcard prompts) |
| `--width-content` | `480px` | Primary content column |
| `--width-wide` | `640px` | Tables, analytics, history |
| `--nav-height` | `56px` | App header height |

---

### Transitions

| Token | Value | Usage |
|---|---|---|
| `--transition-fast` | `80ms ease` | Hover states, button press |
| `--transition-base` | `150ms ease` | Expand/collapse, panel opens |
| `--transition-slow` | `250ms ease` | Page-level motion (use sparingly) |

---

## Component Patterns

### Buttons

**Primary button** — filled, one per screen:
```css
background: var(--color-primary);
color: var(--color-text-on-primary);  /* never hardcode #fff */
border: none;
border-radius: var(--radius-md);
padding: 10px 24px;
font-weight: var(--weight-semibold);
font-size: var(--text-base);
```

**Secondary button** — outlined:
```css
background: transparent;
border: 1px solid var(--color-border);
color: var(--color-text);
border-radius: var(--radius-md);
```

**Ghost button** — no border, text only (for "Back", "Collapse", etc.):
```css
background: none;
border: none;
color: var(--color-text-muted);
```

**Disabled state:** `opacity: 0.5; cursor: not-allowed;` — always, on any variant.

### Navigation Pills

Horizontal row of pill-shaped links for top-level navigation. Styled with the `.nav-pill` CSS class.

```css
.nav-pill {
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text);           /* not --color-primary — avoids blue-on-blue-dark */
  border-radius: var(--radius-full);
  padding: 6px 16px;
  font-size: var(--text-sm);
  font-weight: var(--weight-medium);
}
.nav-pill:hover { background: var(--color-border); }
```

### Cards

```css
background: var(--color-surface);
border: 1px solid var(--color-border);
border-radius: var(--radius-lg);       /* 12px, warmer than 8px */
box-shadow: var(--shadow-sm);
padding: var(--space-6);               /* 24px */
```

### Section Labels

Small uppercase labels above content sections:
```css
font-size: var(--text-xs);
font-weight: var(--weight-semibold);
letter-spacing: 0.08em;
text-transform: uppercase;
color: var(--color-text-muted);
margin-bottom: var(--space-2);
```

### Back Links

Use `--color-text-muted` with hover to `--color-text`. Never use `--color-primary` for back navigation. Always use `<IconArrowLeft size={14} />` before the label — never a raw `←` Unicode character.

```css
.back-link {
  color: var(--color-text-muted);
  text-decoration: none;
  font-size: var(--text-sm);
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  transition: color var(--transition-fast);
}
.back-link:hover { color: var(--color-text); }
```

```tsx
// Link-based back navigation
<Link to="/" className="back-link">
  <IconArrowLeft size={14} /> Back to Home
</Link>

// Button-based back navigation (when using navigate())
<button onClick={() => navigate(-1)} className="back-link" style={{ background: 'none', border: 'none', cursor: 'pointer' }}>
  <IconArrowLeft size={14} /> Back
</button>
```

### Chat Bubbles

- **User bubbles:** `background: var(--color-primary)`, `color: var(--color-text-on-primary)`, align right
- **AI bubbles:** `background: var(--color-surface)`, `color: var(--color-text)`, border, align left
- Padding: `10px 14px`, radius: `var(--radius-lg)`, max-width: 75%, line-height: `var(--leading-relaxed)`

### App Header

Sticky, 56px tall (`--nav-height`), `--color-surface` background, bottom border in `--color-border`. Contains: app name (left, `--weight-bold`, `--text-md`) and theme toggle (right, `.theme-toggle` class).

### Modal Dialogs

Use a modal when the user must make a decision that **interrupts the current context** — creating a new item, confirming a destructive action, or entering a focused sub-task. The backdrop signals "you are in a sub-task; everything else is paused."

**Never use an inline-expanding panel for creation flows.** Inline panels keep existing content visible and scrollable, which competes for attention. A modal enforces focus.

**Structure:**

```tsx
{/* Backdrop — sibling to dialog, not parent */}
<div
  aria-hidden="true"
  onClick={onClose}
  style={{
    position: 'fixed',
    inset: 0,
    background: 'rgba(28, 25, 23, 0.5)',  /* warm near-black, matches shadow color */
    backdropFilter: 'blur(4px)',
    zIndex: 40,
  }}
/>

{/* Dialog */}
<div
  role="dialog"
  aria-modal="true"
  aria-label="[descriptive label]"
  style={{
    position: 'fixed',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: 'min(480px, calc(100vw - 48px))',
    maxHeight: 'calc(100vh - 64px)',
    overflowY: 'auto',
    background: 'var(--color-surface)',
    borderRadius: 'var(--radius-xl)',    /* 16px — large surface */
    boxShadow: 'var(--shadow-lg)',
    padding: '32px',
    zIndex: 50,
  }}
>
  {/* Close button — top-right, always visible */}
  <button
    onClick={onClose}
    aria-label="Close"
    style={{ position: 'absolute', top: '16px', right: '16px', ... }}
  >
    ×
  </button>
  {/* Content */}
</div>
```

**Rules:**
- Backdrop and dialog are **siblings**, not parent/child — click events on the dialog do not bubble to the backdrop.
- Use `backdropFilter: blur(4px)` to visually recede the background without hiding it entirely.
- Always wire `Escape` to close: `document.addEventListener('keydown', ...)` in a `useEffect` that cleans up on unmount.
- `role="dialog"` + `aria-modal="true"` + `aria-label` are required for screen reader support.
- The close `×` character is permitted per the icon rules (Unicode text character, not emoji), but must have `aria-label="Close"`.
- Width uses `min(480px, calc(100vw - 48px))` to stay within viewport on mobile.
- `zIndex` convention: backdrop at 40, dialog at 50.

---

### Stepped Wizard

Use a stepped wizard when a creation or configuration flow has **3 or more independent decisions** that would overwhelm a single form. Each step presents exactly one question, enforcing the "one primary action per screen" principle at the micro-flow level.

**When to use a wizard vs a single form:**
- ≥ 3 distinct, independent decisions → wizard
- 1–2 related fields → single form within a modal
- A destructive confirmation → single modal, no steps

**Progress dots:**

```tsx
{Array.from({ length: TOTAL_STEPS }).map((_, i) => (
  <div
    key={i}
    style={{
      height: '8px',
      width: i === step ? '24px' : '8px',   /* active dot expands */
      borderRadius: '9999px',
      background: i === step
        ? 'var(--color-primary)'
        : i < step
        ? 'var(--color-primary-subtle)'      /* completed */
        : 'var(--color-border)',             /* upcoming */
      transition: 'width 150ms ease, background 150ms ease',
    }}
  />
))}
```

**Step heading structure:**

Each step gets a large heading (`1.75rem`, `font-weight: 700`, `letter-spacing: -0.02em`) phrased as a question ("How many cards?"), a small uppercase step counter above it, and a one-line subtitle in muted text below.

```
Step 1 of 3          ← --text-xs, uppercase, muted
How many cards?      ← 1.75rem, bold, -0.02em tracking
Choose a session size. You can always create more decks later.  ← --text-sm, muted
```

**Navigation pattern:**
- Step 1: **Cancel** (ghost, left) + **Next →** (primary, right)
- Middle steps: **Back** (outlined, left) + **Next →** (primary, right)
- Final step: **Back** (outlined, left) + **Generate / Submit** (primary, right)
- "Generate" only appears on the final step — never prematurely.
- The Back button preserves all previously entered state.

---

### Selection Tile Cards

Use selection tiles — not `<select>` dropdowns — when the user needs to **choose one option from a small set (2–6)** and the options benefit from visible descriptions.

**Why not dropdowns:**
- Dropdowns hide all options until clicked — the user cannot survey their choices at a glance.
- Option descriptions cannot be shown in `<option>` elements without hacks.
- Dropdowns are visually subordinate; tiles make the decision feel intentional.

**Tile anatomy:**

```tsx
<button
  onClick={() => setValue(option.value)}
  style={{
    padding: '16px 20px',
    border: `2px solid ${selected ? 'var(--color-primary)' : 'var(--color-border)'}`,
    borderRadius: 'var(--radius-lg)',
    background: selected ? 'var(--color-primary-subtle)' : 'var(--color-surface)',
    cursor: 'pointer',
    textAlign: 'left',
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    transition: 'border-color 80ms ease, background 80ms ease',
    width: '100%',
  }}
>
  <span style={{ fontSize: '1.125rem', fontWeight: 600, color: selected ? 'var(--color-primary-text)' : 'var(--color-text)' }}>
    {option.label}
  </span>
  <span style={{ fontSize: '0.875rem', color: selected ? 'var(--color-primary-text)' : 'var(--color-text-muted)' }}>
    {option.description}
  </span>
</button>
```

**Selected state:** `--color-primary-subtle` background + `--color-primary` border + `--color-primary-text` for all text within the tile. Never use `#fff` on teal backgrounds.

**Numeric tiles** (e.g., card count presets): use `1.75rem` bold for the number, a short sublabel in muted text on the right, row layout (`flex-direction: row`, `justify-content: space-between`).

**Custom entry tile:** treat "Custom" as a fourth tile that, when selected, expands to reveal a large `<input type="number">` inside itself. Do not render the input as a separate sibling element in the row — this avoids the width-constrained, label-truncation problem of inline inputs.

```tsx
{/* Custom tile — self-contained */}
<button onClick={() => setUseCustom(true)} style={tileStyle(useCustom)}>
  <span>Custom</span>
  {useCustom && (
    <input
      type="number"
      autoFocus
      onClick={(e) => e.stopPropagation()}  /* prevent tile toggle on input click */
      style={{ fontSize: '1.75rem', fontWeight: 700, textAlign: 'center', width: '100%', ... }}
    />
  )}
</button>
```

**Layout:** stack tiles vertically with `gap: 10px`. Do not use a grid — vertical stacking makes scanning and tapping easier on narrow viewports.

---

### Forms & Inputs

```css
padding: 10px 12px;
border: 1px solid var(--color-border);
border-radius: var(--radius-md);
background: var(--color-surface);
color: var(--color-text);
font-size: var(--text-base);
```
Focus: `outline: 2px solid var(--color-primary); outline-offset: 2px;`

---

## Brand Mark & Favicon

### Concept

A filled speech bubble — the universal symbol for conversation. Single shape, single read. No interior detail at small sizes; no gradients; no strokes.

### File

`frontend/public/favicon.svg` — served from Vite's `public/` directory at `/favicon.svg`. Linked from `index.html` as:

```html
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
```

### Construction (16×16 viewBox)

| Element | Value |
|---|---|
| Tile background | `<rect width="16" height="16" rx="3">` — rounded square, `rx="3"` reads clearly rounded but not circular at 16px |
| Bubble body + tail | Single `<path>` — body + tail combined to avoid sub-pixel gaps between the two shapes |
| Bubble body | Occupies x=2–14, y=2–11; Q-bezier corners equivalent to ~2px radius |
| Tail | Triangle from base (x=4–7, y=11) to tip (x=4, y=14) — bottom-left placement, iMessage/chat convention |

### Adaptive Colors (via CSS `@media` inside the SVG)

| Mode | Tile | Symbol |
|---|---|---|
| Light | `#0d9488` (teal-600, `--color-primary`) | `#faf9f7` (warm off-white, `--color-bg`) |
| Dark | `#2dd4bf` (teal-300, dark-mode `--color-primary`) | `#0f172a` (near-black) |

The SVG contains an inline `<style>` block with a `@media (prefers-color-scheme: dark)` rule. This means the browser tab icon adapts to the OS theme automatically — no JavaScript, no extra files.

### Why not PNG/ICO?

SVG favicons are supported by all modern browsers (Chrome 80+, Firefox 41+, Edge 80+, Safari 12+). They are resolution-independent and theme-adaptive. A `favicon.ico` fallback would be needed for IE11 — not a target browser for this app.

If iOS home screen support is added later, create `frontend/public/apple-touch-icon.png` at 180×180px with the same teal tile + white bubble at larger scale, and add `<link rel="apple-touch-icon" href="/apple-touch-icon.png">` to `index.html`.

## Icons

### Rule: SVG only, never emoji

Emoji are **never used** in the UI chrome. Reasons:

- **Platform rendering divergence** — the same codepoint renders as a completely different shape, color, and silhouette on Apple, Google, Windows, and Samsung emoji fonts. Visual QA is impossible cross-platform.
- **Dark mode blindness** — emoji are baked-in RGBA images. They cannot inherit `color: currentColor`, do not invert for dark mode, and actively clash against dark backgrounds.
- **Visual weight mismatch** — emoji are heavy pictograms designed for text runs. They have no relationship to the stroke weight, corner radius, or optical spacing of the typeface.
- **Accessibility** — screen readers announce emoji by their Unicode name ("turtle") not the UI intent ("slower playback").

### Icon system: Lucide-style inline SVGs

All icons follow the Lucide visual language:

```
viewBox="0 0 24 24"
fill="none"
stroke="currentColor"
strokeWidth="2"
strokeLinecap="round"
strokeLinejoin="round"
```

`stroke="currentColor"` means every icon automatically adapts to its parent element's text color — muted, active, inverted, or disabled — for free.

**Sizing by context:**

| Context | Render size |
|---|---|
| Tool bar buttons (Replay, Translate…) | 10–11px |
| Standard buttons and labels | 14–16px |
| Primary action buttons (record, send) | 18–20px |
| Page-level actions | 20–22px |

### Shared icon components

Reusable icons live in [frontend/src/components/shared/icons.tsx](../frontend/src/components/shared/icons.tsx). Import from there — never inline a raw SVG path in a component file.

Available icons: `IconMic`, `IconStop`, `IconPlay`, `IconClock`, `IconCheck`, `IconGlobe`, `IconArrowLeft`, `IconArrowLeftRight`, `IconLightbulb`, `IconMessageCircle`, `IconSearch`, `IconTrash`, `IconVolume`.

### Unicode text characters (allowed exceptions)

Directional text characters are permitted in label contexts only (not as icon substitutes):

| Character | Allowed usage |
|---|---|
| `→` | Directional labels (e.g., "Ask →", "English → Spanish") |
| `↑` | Send button label |
| `×` or `✕` | Close button (when icon-only with `aria-label`) |

**`←` is not permitted.** Use `<IconArrowLeft size={14} />` instead. The Unicode arrow lacks hover/transition support and visual consistency with the SVG icon system.

These are typographic characters, not emoji — they inherit color, scale with font size, and are visually consistent with the typeface.

### Do's and don'ts

| Do | Don't |
|---|---|
| Use `<IconMic size={18} />` from `icons.tsx` | Use `🎤` as a button's only content |
| Give the parent button an `aria-label` | Rely on the icon for accessibility |
| Use `currentColor` (inherited) for icon color | Set an explicit hex color on the SVG |
| Use `strokeWidth="2"` (Lucide default) | Override to `1` or `1.5` — it breaks visual consistency |
| Match icon size to surrounding text weight | Mix icon sizes within a single toolbar |

## Dark Mode Guidelines

1. **Hue angle preservation:** The dark background `#1a1714` is `hsl(28, 10%, 9%)` — same warm hue family as the light `#faf9f7` (`hsl(30, 14%, 98%)`). This is why dark mode feels warm, not cold.
2. **No pure black.** `#000000` reads as void; `#1a1714` reads as a candlelit room.
3. **Warm near-white for text.** `#f5f2ee` instead of `#ffffff` maintains thermal consistency.
4. **Surfaces layer by luminance, not borders.** In dark mode, `--color-bg` → `--color-surface` → `--color-surface-raised` step by ~4–5% luminance. Reduce or omit border lines on cards in dark mode when the luminance step is visible enough.
5. **Primary shifts lighter.** Light mode: teal-600 (`#0d9488`). Dark mode: teal-300 (`#2dd4bf`). This keeps the accent visually prominent against the dark background while filling the same role. Text on teal-300 backgrounds uses dark near-black `--color-text-on-primary: #0d1f1e`.

---

## Accessibility

- **Minimum contrast ratios:** 4.5:1 for body text, 3:1 for large UI text and components (WCAG AA)
- **Touch targets:** minimum 44×44px for all interactive elements
- **Focus rings:** `*:focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }`
- **`aria-label`** on all icon-only buttons
- **`aria-live`** on streaming/loading states
- **Never** suppress focus outline for non-mouse interactions

---

## Data Cards & List Items

When a screen shows a list of user-created items (decks, sessions, conversations), each item carries multiple types of information. Without deliberate structure, all fields render at the same visual weight and the list becomes unreadable at scale.

### The three-layer model

Every data card must be designed around three distinct layers. Each layer has a different visual weight and a different job:

| Layer | Job | Visual treatment |
|---|---|---|
| **Identity** | What *type* of thing is this? | Prominent icons, bold label, top of the card |
| **Status** | How is it *doing*? When was it last used? | Color-coded values, progress bars, relative time |
| **Action** | What can I *do* with it? | Primary button (one), secondary button (one max) |

If you can't immediately answer "what is this thing?" from the identity layer alone, the card is under-designed.

### Identity marks

Use the feature's own icon vocabulary as a visual fingerprint on each card. Two cards with different configurations should look visually distinct before the user reads a single word.

- Group the icons in a raised container (`--color-surface-raised` background, `--radius-md`) on the left edge of the card
- Size: 20px — large enough to read at a glance, not so large they dominate
- Color: `--color-primary` — the teal tint signals "this is the type identifier"
- Stack vertically when showing two related icons (e.g., mode icon above algorithm icon)

```tsx
<div style={{
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  gap: '6px',
  padding: '10px 8px',
  background: 'var(--color-surface-raised)',
  borderRadius: 'var(--radius-md)',
  color: 'var(--color-primary)',
  flexShrink: 0,
}}>
  {modeIcon}
  {algorithmIcon}
</div>
```

### Card title: derived from configuration, not from timestamp

**Never use a timestamp as the primary title of a data card.** Auto-generated names like "Deck — Mar 22, 2026" are low-information — the date is already expressed by the status layer. The title slot is the most prominent text on the card; it should answer "what IS this?"

Derive the title from the item's configuration:
```tsx
// Good — tells the user what kind of deck this is
{MODE_LABELS[deck.practice_mode]} · {ALGO_LABELS[deck.algorithm]}

// Bad — tells the user when it was made, which belongs in the status layer
{deck.name}  // "Deck — Mar 22, 2026"
```

### Status badges

Use a pill badge to surface a discrete state that changes the meaning of the card. The most common case is "New" for items that have never been interacted with.

```tsx
{isNew && (
  <span style={{
    fontSize: '0.7rem',
    fontWeight: 600,
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    background: 'var(--color-primary-subtle)',
    color: 'var(--color-primary-text)',
    borderRadius: '9999px',
    padding: '2px 8px',
  }}>
    New
  </span>
)}
```

Rules:
- Badges sit inline with the card title, not below it
- One badge maximum per card — if you need two, reconsider the information architecture
- Use `--color-primary-subtle` / `--color-primary-text` for neutral state badges ("New", "Active")
- Use `--color-warning-subtle` / `--color-warning` for time-sensitive badges ("Due", "Expiring")
- Use `--color-error-subtle` / `--color-error` for problem badges ("Failed", "Blocked")

### Progress bars

A thin horizontal bar communicates a 0–100% value faster than a number. Use for accuracy, completion, and progress metrics.

```tsx
<div style={{
  flex: 1,
  height: '4px',
  background: 'var(--color-border)',
  borderRadius: '9999px',
  overflow: 'hidden',
}}>
  <div style={{
    height: '100%',
    width: `${value * 100}%`,
    background: fillColor,
    borderRadius: '9999px',
    transition: 'width 300ms ease',
  }} />
</div>
```

Always pair the bar with a numeric label on the same row — the bar gives instant gestalt, the number gives precision:

```tsx
<div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
  <div style={{ flex: 1 }}>  {/* bar */} </div>
  <span style={{ fontSize: '0.75rem', fontWeight: 600, flexShrink: 0 }}>72%</span>
</div>
```

Bar height: 4px is the standard. 6px for more prominent progress (e.g., a full-width section bar). Never exceed 8px — taller bars read as filled buttons, not progress indicators.

### Color-coded status values

Accuracy, scores, and health metrics should use a three-tier color system. Apply the color to both the progress bar fill and the accompanying numeric label so they read as a unit:

| Threshold | Color token | Meaning |
|---|---|---|
| ≥ 80% | `--color-success` | Doing well |
| 60–79% | `--color-warning` | Needs attention |
| < 60% | `--color-error` | Struggling |

```ts
function accuracyColor(accuracy: number): string {
  if (accuracy >= 0.8) return 'var(--color-success)'
  if (accuracy >= 0.6) return 'var(--color-warning)'
  return 'var(--color-error)'
}
```

Never use raw green/yellow/red hex values. Always use the semantic tokens — they adapt to dark mode automatically.

### Timestamps

Use a short formatted date ("Mar 22") for recency fields on data cards. Omit the year when it matches the current year. Use `toLocaleDateString` with `{ month: 'short', day: 'numeric' }` — never hardcode a format string.

### Full card structure example

```tsx
<li style={{
  background: 'var(--color-surface)',
  border: '1px solid var(--color-border)',
  borderRadius: 'var(--radius-lg)',   /* always --radius-lg for list cards */
  padding: '16px 20px',
  display: 'flex',
  gap: '16px',
  alignItems: 'flex-start',
  boxShadow: 'var(--shadow-sm)',
}}>
  {/* Layer 1: Identity */}
  <div style={{ ...identityBlockStyle }}>
    {typeIconA}
    {typeIconB}
  </div>

  {/* Layer 2: Status */}
  <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: '6px' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
      <span style={{ fontWeight: 600, fontSize: '1rem' }}>{derivedTitle}</span>
      {isNew && <NewBadge />}
    </div>
    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
      {subtitle} · {relativeTime(item.last_active_at)}
    </div>
    {accuracy != null && <AccuracyBar value={accuracy} />}
  </div>

  {/* Layer 3: Actions — stacked vertically, right-aligned */}
  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', flexShrink: 0 }}>
    <PrimaryButton />
    <SecondaryButton />
  </div>
</li>
```

Key rules:
- Cards in lists always use `--radius-lg` (12px), never `--radius` / `--radius-md`
- Always include `box-shadow: var(--shadow-sm)` — lifts the card off the background subtly
- Action buttons stack **vertically** on the right when there are two — horizontal stacking pushes content too wide on narrow viewports
- `flex: 1; min-width: 0` on the status column prevents text overflow bleeding outside the card

---

## Do's and Don'ts

| Do | Don't |
|---|---|
| Use `var(--color-text-on-primary)` for text on primary backgrounds | Hardcode `#fff` or `#000` on colored backgrounds |
| Use `--color-text-muted` for secondary nav, back links | Use `--color-primary` for navigation text (blue-on-blue-dark problem) |
| Add `--color-error-subtle` for error message backgrounds | Hardcode `#fef2f2` |
| Use `--radius-lg` (12px) for cards and list items | Use `--radius` / 8px for cards (too sharp) |
| Use `--shadow-sm` (warm-tinted) | Use `box-shadow: 0 1px 3px rgba(0,0,0,0.1)` (cold shadow) |
| Build hierarchy with font size and weight | Add decorative borders, backgrounds, or gradients for hierarchy |
| Keep the content column at `--width-content` (480px) | Widen content for "breathing room" — whitespace comes from page padding |
| Use `var(--color-success)` directly | Use `var(--color-success, green)` — the fallback means the token is undefined |
| Use short formatted dates ("Mar 22") for recency fields on cards | Hardcode date format strings — use `toLocaleDateString` with options |
| Derive card titles from item configuration (mode, type, category) | Use auto-generated timestamp names ("Deck — Mar 22, 2026") as the primary title |
| Color-code accuracy/score values with success/warning/error tokens | Show raw percentages in muted text with no visual encoding |
| Use `--color-surface-raised` for icon identity blocks within cards | Leave icon identity areas with no background distinction |
| Use a modal with blurred backdrop for creation/configuration flows | Expand inline panels that leave existing content visible and competing for attention |
| Use stepped wizards for flows with ≥ 3 independent decisions | Put all options in one dense form when choices benefit from focused attention |
| Use selection tile cards for small option sets (2–6) with descriptions | Use `<select>` dropdowns that hide options until clicked |
