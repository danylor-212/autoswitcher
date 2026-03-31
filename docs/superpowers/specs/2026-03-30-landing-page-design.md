# AutoSwitcher Landing Page — Design Spec

**Date:** 2026-03-30
**Status:** Approved
**Stack:** Next.js 16 + Tailwind CSS 4 + Framer Motion, static export

---

## 1. Product Context

AutoSwitcher is a desktop application (Windows + macOS) that auto-detects when a bilingual user is typing in the wrong keyboard layout and corrects it locally. Currently supports English ↔ Ukrainian, with Spanish, French, German, and Portuguese planned.

**USPs:**
- Solves the universal bilingual frustration of typing gibberish in the wrong layout
- 100% local — no internet connection, no data leaves the machine
- Fully open source — auditable, forkable, no telemetry

**Target audience:** Bilingual people broadly. Positioned as a platform for many language pairs, not just EN/UA. Developer/hacker aesthetic appeals to the open-source community.

---

## 2. Design System

### Color Tokens

| Token | Value | Usage |
|---|---|---|
| `--bg-primary` | `#0A1628` | Page background |
| `--bg-elevated` | `#0F1D32` | Elevated surfaces |
| `--bg-card` | `#122240` | Card backgrounds |
| `--bg-card-hover` | `#162A4E` | Card hover state |
| `--bg-terminal` | `#0D1117` | Terminal/code blocks |
| `--bg-footer` | `#060E1A` | Footer background |
| `--violet` | `#A78BFA` | Primary accent |
| `--violet-light` | `#C4B5FD` | Hover/light accent |
| `--violet-dark` | `#7C3AED` | Active/pressed |
| `--violet-subtle` | `rgba(167,139,250,0.08)` | Tinted backgrounds |
| `--violet-border` | `rgba(167,139,250,0.2)` | Subtle borders |
| `--text-primary` | `#FFFFFF` | Headings |
| `--text-secondary` | `rgba(255,255,255,0.55)` | Body text |
| `--text-muted` | `rgba(255,255,255,0.3)` | Labels, hints |
| `--positive` | `#34D399` | Success/correct states |
| `--negative` | `#F87171` | Error/wrong states |
| `--warning` | `#F59E0B` | Planned/pending states |
| `--border-subtle` | `rgba(255,255,255,0.06)` | Dividers |
| `--border-hover` | `rgba(255,255,255,0.12)` | Hover borders |

### Typography

- **Headings:** JetBrains Mono (monospace) — reinforces developer aesthetic
- **Body text:** Inter (sans-serif) — clean readability
- **Code snippets / labels:** JetBrains Mono
- Both loaded via `next/font/google` with `display: "swap"`

### Shared Components (ported from United Network patterns)

- **RevealOnScroll** — Framer Motion `useInView`, fade-up animation (opacity 0 + translateY 24px → visible), cubic-bezier `[0.16, 1, 0.3, 1]`, fires once
- **SectionHeader** — Monospace uppercase label + title with gradient highlight on key phrase + optional description. Center-aligned.
- **cn()** — `clsx` + `tailwind-merge` utility for safe class merging

### Global Patterns

- **Section spacing:** `py-16 sm:py-20` vertical, `max-w-[1080px] mx-auto px-5 sm:px-6`
- **Card hover:** border-subtle → violet-border, bg-card → bg-card-hover, translateY(-2px) lift
- **Mouse-follow glow:** CSS variables `--mouse-x`/`--mouse-y` with radial gradient on hover
- **Responsive:** Mobile-first, breakpoints at sm(640), md(768), lg(1024)
- **Animations:** Staggered RevealOnScroll with incremental delay per element

---

## 3. Logo

**Concept: "The Correction"** — Shows gibberish text transforming into correct text via an arrow. Communicates the product story at a glance.

**Elements:**
- Two overlapping rounded rectangles representing text fields
- Top field: garbled text (e.g., "ghbdsn") in white/muted
- Bottom field: correct text (e.g., "привіт") in violet
- Connecting arrow showing the transformation
- Subtle sparkle accents

**Deliverables:**
- Full SVG logo (icon + wordmark)
- Icon-only variant (for favicon, system tray)
- Both in navy + violet palette

---

## 4. Navbar

- **Fixed sticky header** with frosted glass effect on scroll (backdrop-blur)
- **Left:** Logo icon + "AutoSwitcher" wordmark (monospace)
- **Center/Right links:** Features, How It Works, Languages (scroll-to-section anchors)
- **CTA button:** "Download" with violet gradient background
- **Mobile:** Hamburger menu with full-screen overlay, staggered link animations
- **Scroll behavior:** Transitions from transparent to glass-pill style at ~60px scroll

---

## 5. Sections

### 5.1 Hero

**Layout:** Centered, single-column

**Content:**
- **Pill badge:** "Open Source · 100% Local" — violet-subtle background, violet-border
- **Headline:** "Stop typing **gibberish.**" — "gibberish" in violet gradient text, JetBrains Mono
- **Subline:** "AutoSwitcher detects when you're typing in the wrong keyboard layout and instantly corrects it. No internet. No data leaves your machine."
- **CTA buttons:**
  - Primary: "Download for Windows" (violet bg, navy text) + Windows icon
  - Primary: "Download for macOS" (violet bg, navy text) + Apple icon
  - Secondary: "View Source →" (border style, violet text)
- **Terminal demo card** (centerpiece)

**Terminal Demo Animation:**
- macOS-style window chrome (red/yellow/green dots + "terminal" label)
- Monospace font throughout
- Animation sequence (looping):
  1. `0.0s` — Page loads, headline fades up with staggered children
  2. `0.8s` — Terminal card fades up
  3. `1.5s` — Characters typed one by one: "ghbdsn cdsn" in red (`--negative`)
  4. `3.0s` — Pause with blinking cursor
  5. `3.5s` — Red text gets strikethrough, green text types in: "привіт світ" (`--positive`)
  6. `5.0s` — "✓ UA detected" badge fades in (green subtle background)
  7. `7.0s` — Loop restarts with a different phrase pair
- Multiple phrase pairs to cycle through. Each "wrong" string must be the actual keys you'd press on an EN keyboard when your layout is set to UA (i.e., real keyboard position mapping, not random characters). Examples:
  - "ghbdsn cdsn" → "привіт світ" (hello world)
  - "dsgj" → "вхід" (login)
  - "djlrhjlysq rjl" → "відкритий код" (open source)
- Implemented with Framer Motion `animate` sequences and `useEffect` interval

### 5.2 How It Works

**Layout:** Section header + 3-column grid

**Section header:**
- Label: "HOW IT WORKS"
- Title: "Three steps. **Zero effort.**"

**3 step cards** (terminal-style, `--bg-terminal` background):
- Each has: numbered pill badge (01/02/03), icon, title, description, code snippet
- **Step 1 — "You type":** Keyboard icon. "Start typing without checking your layout." Code: `$ ghbdsn cdsn_` (red)
- **Step 2 — "We detect":** Magnifying glass icon. "AutoSwitcher runs locally, analyzing keystrokes against language dictionaries in real time." Code: `analyzing... → UA match 97%` (amber → violet)
- **Step 3 — "Auto-corrected":** Sparkle icon. "Text is instantly replaced with what you actually meant to type." Code: `$ привіт світ ✓` (green)

**Animation:** Cards reveal on scroll with staggered delay (0, 0.1s, 0.2s)

**Responsive:** Stacks to single column on mobile

### 5.3 Features

**Layout:** Section header + 2x2 card grid

**Section header:**
- Label: "FEATURES"
- Title: "Built for people who **think in two languages.**"

**4 feature cards** (with mouse-follow glow effect):

Each card has: custom SVG icon in violet, `CONSTANT_CASE` monospace label, title, description.

1. **100% Offline** (`LOCAL_ONLY`) — "No internet connection. No cloud. No API calls. Everything runs on your machine using local dictionaries. Your keystrokes never leave your device." Icon: terminal window with traffic light dots.
2. **Fully Open Source** (`OPEN_SOURCE`) — "Every line of code is public. Audit it, fork it, contribute to it. No hidden telemetry, no tracking, no surprises. Trust through transparency." Icon: code brackets `</>`.
3. **Instant & Lightweight** (`LIGHTWEIGHT`) — "Sits quietly in your system tray. Detects and corrects in real time with minimal CPU and memory. You won't even notice it's running." Icon: clock/speed.
4. **Both Directions** (`BIDIRECTIONAL`) — "Works both ways — English to Ukrainian and Ukrainian to English. Whichever layout you forgot to switch, AutoSwitcher has you covered." Icon: bidirectional arrows.

**Animation:** Cards reveal on scroll with stagger. Mouse-follow glow on hover (radial gradient at cursor position).

**Responsive:** 2x2 on desktop, single column on mobile

### 5.4 Privacy

**Layout:** Section header + two-column (guarantees left, terminal audit right)

**Section header:**
- Label: "PRIVACY"
- Title: "Your keystrokes are **yours.**"
- Description: "We don't want your data. We can't see your data. The app has no way to phone home — even if it wanted to."

**Left column — 4 guarantee cards:**
Each has green checkmark icon, monospace title, description.
1. **Zero network connections** — "No HTTP requests, no WebSocket, no DNS lookups. Verify with Wireshark yourself."
2. **No data collection** — "No analytics, no telemetry, no crash reports. We don't know you exist."
3. **Password safe** — "AutoSwitcher processes text patterns, not individual keystrokes. It can't capture passwords or sensitive input."
4. **Auditable source code** — "Don't trust us — read the code. Every line is public on GitHub."

**Right column — Terminal "network audit":**
- macOS window chrome
- Animated line-by-line on scroll:
  ```
  $ netstat -b | grep AutoSwitcher
    (no results)
  $ wireshark --filter "autoswitcher"
    0 packets captured
  $ dns-log --app AutoSwitcher
    0 DNS queries
  ─────────────────
  ✓ Zero outbound connections
  ✓ Zero packets transmitted
  ✓ Zero DNS lookups
  ```

**Responsive:** Stacks vertically on mobile (guarantees on top, terminal below)

### 5.5 Languages

**Layout:** Section header + centered terminal + flag cards row

**Section header:**
- Label: "LANGUAGES"
- Title: "One pair today. **Many more coming.**"

**Terminal "package list"** (`autoswitch list --languages`):
- INSTALLED section: "English ↔ Ukrainian" — v0.3.3, green `stable` badge
- COMING SOON section:
  - "English ↔ Spanish" — amber `planned` badge
  - "English ↔ French" — amber `planned` badge
  - "English ↔ German" — amber `planned` badge
  - "English ↔ Portuguese" — amber `planned` badge
- Bottom line: "Want your language? Open an issue →" (violet link)

**Flag cards row** below terminal:
- 🇺🇦 Ukrainian — green border, "available now"
- 🇪🇸 Spanish — amber border, dimmed, "coming soon"
- 🇫🇷 French — amber border, dimmed, "coming soon"
- 🇩🇪 German — amber border, dimmed, "coming soon"
- 🇧🇷 Portuguese — amber border, dimmed, "coming soon"

**Animation:** Terminal lines animate in sequentially. Flag cards reveal with stagger.

**Responsive:** Flag cards wrap on smaller screens

### 5.6 Download / CTA

**Layout:** Centered glowing card

**Card styling:** Violet-subtle gradient background, violet-border, subtle radial glow behind

**Content:**
- **Version badge:** "v0.3.3 · FREE & OPEN SOURCE"
- **Headline:** "Ready to stop **retyping?**"
- **Subline:** "Download AutoSwitcher and never worry about wrong keyboard layouts again."
- **Two primary download buttons** (side by side):
  - "Download for Windows" — violet bg, navy text, download icon, Windows icon, glow shadow
  - "Download for macOS" — violet bg, navy text, download icon, Apple icon, glow shadow
- **Platform info row:** "Windows 10+" and "macOS 12+" as equal first-class platforms
- **Git clone section** below divider:
  - "Or if you prefer building from source:"
  - Terminal snippet: `$ git clone github.com/user/autoswitcher` with copy-to-clipboard button

**Animation:** Card fades up on scroll. Buttons have hover glow pulse.

### 5.7 Footer

**Layout:** Two-row — content row + copyright bar

**Content row:**
- **Left:** Logo + "AutoSwitcher" + tagline: "Open-source keyboard layout auto-correction. Built with care for bilingual people."
- **Right:** Two link columns:
  - **Product:** Download, Features, Languages (internal scroll anchors)
  - **Community:** GitHub →, Report Bug →, Request Language → (external links)

**Copyright bar** (separated by subtle border):
- Left: "© 2026 AutoSwitcher. MIT License."
- Right: "Made with ❤ for bilingual devs"

**Styling:** Darkest background (`--bg-footer: #060E1A`), monospace throughout

---

## 6. Project Structure

```
autoswitch-landing/
├── src/
│   ├── app/
│   │   ├── layout.tsx          # Root layout: fonts, metadata, Navbar + Footer
│   │   ├── page.tsx            # Composes all 7 sections
│   │   └── globals.css         # CSS variables, keyframes, utility classes
│   ├── components/
│   │   ├── sections/
│   │   │   ├── Hero.tsx        # Hero + typing simulation
│   │   │   ├── HowItWorks.tsx  # 3-step process
│   │   │   ├── Features.tsx    # 4-card feature grid
│   │   │   ├── Privacy.tsx     # Guarantees + terminal audit
│   │   │   ├── Languages.tsx   # Package list + flag cards
│   │   │   └── Download.tsx    # CTA card
│   │   ├── layout/
│   │   │   ├── Navbar.tsx      # Sticky nav with glass effect
│   │   │   └── Footer.tsx      # Footer with links
│   │   └── shared/
│   │       ├── RevealOnScroll.tsx
│   │       └── SectionHeader.tsx
│   └── lib/
│       └── utils.ts            # cn() helper
├── public/
│   └── images/
│       ├── logo.svg            # Full logo (icon + wordmark)
│       └── logo-icon.svg       # Icon only (favicon)
├── next.config.ts              # Static export config
├── tailwind.config.ts
├── tsconfig.json
└── package.json
```

---

## 7. SEO & Metadata

- **Title:** "AutoSwitcher — Stop Typing Gibberish"
- **Description:** "Open-source desktop app that auto-detects wrong keyboard layouts and corrects your text locally. Supports English ↔ Ukrainian, more languages coming soon. 100% offline, no data collection."
- **Keywords:** keyboard layout switcher, bilingual typing, auto-correct keyboard, Ukrainian English, open source, local, offline, privacy
- **Open Graph:** Title, description, featured image (hero screenshot)
- **Theme color:** `#A78BFA`
- **Favicon:** Logo icon SVG

---

## 8. Performance

- **Static export** (`output: 'export'`) — no server runtime
- **next/font** with `display: "swap"` for both fonts
- **Next.js Image** component for any raster images
- **Framer Motion** lazy-loaded only for animated sections
- **RevealOnScroll** with `once: true` to avoid re-triggering

---

## 9. Responsive Behavior

All sections follow mobile-first design:
- **Mobile (<640px):** Single column layouts, stacked cards, hamburger nav
- **Tablet (640-1024px):** Some 2-column grids start applying
- **Desktop (1024px+):** Full layouts as wireframed — 3-column How It Works, 2x2 Features, 2-column Privacy

---

## 10. Out of Scope

- No backend or API
- No user accounts or authentication
- No blog or documentation pages
- No i18n (page is English-only)
- No cookie banner or analytics
- Download links will be placeholder URLs until GitHub releases are set up
