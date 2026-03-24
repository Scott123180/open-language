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

## Do's and Don'ts

| Do | Don't |
|---|---|
| Use `var(--color-text-on-primary)` for text on primary backgrounds | Hardcode `#fff` or `#000` on colored backgrounds |
| Use `--color-text-muted` for secondary nav, back links | Use `--color-primary` for navigation text (blue-on-blue-dark problem) |
| Add `--color-error-subtle` for error message backgrounds | Hardcode `#fef2f2` |
| Use `--radius-lg` (12px) for cards | Use `--radius` / 8px for cards (too sharp) |
| Use `--shadow-sm` (warm-tinted) | Use `box-shadow: 0 1px 3px rgba(0,0,0,0.1)` (cold shadow) |
| Build hierarchy with font size and weight | Add decorative borders, backgrounds, or gradients for hierarchy |
| Keep the content column at `--width-content` (480px) | Widen content for "breathing room" — whitespace comes from page padding |
| Use `var(--color-success)` directly | Use `var(--color-success, green)` — the fallback means the token is undefined |
