# AutoSwitcher App — Development Plan

**Date:** 2026-03-30
**Current Version:** v0.3.4
**Status:** Beta — core EN↔UA switching stable, T9 autocorrect working, Windows build distributable

---

## Executive Summary

AutoSwitcher occupies an uncontested position in the market: **open-source, offline-first, privacy-respecting, free auto-layout-switching**. The nearest competitor (Punto Switcher) has serious privacy baggage (Yandex ownership, keylogging capability, Russian data jurisdiction). Caramba Switcher — built by Punto's original creator — is paid and closed-source.

This plan takes AutoSwitcher from a working beta to a publicly released, multi-platform, multi-language tool with distribution through GitHub, winget, and a dedicated landing page.

---

## Phase 1: Ship-Ready Polish (v0.4.0)

**Goal:** Make the current EN↔UA Windows build ready for public release.

### 1.1 Detection Quality Hardening
- [ ] Audit false-positive rates with expanded test corpus (common programming terms, abbreviations, mixed-language sentences)
- [ ] Add a "undo last correction" hotkey (e.g., Ctrl+Z passthrough or dedicated shortcut) so users can quickly revert incorrect swaps
- [ ] Improve punctuation-adjacent word handling (URLs, file paths, code snippets should not be corrected)
- [ ] Add programming mode / code editor detection — disable correction when focus is in known IDEs (VS Code, PyCharm, etc.)

### 1.2 UX Improvements
- [ ] Add a subtle toast notification on correction (optional, off by default) so users know when a swap happened
- [ ] Add correction statistics to settings window (words corrected today, total corrections)
- [ ] Improve whitelist UX — allow adding the current word to whitelist via hotkey
- [ ] Add "Start with Windows" toggle in settings (registry-based autostart)
- [ ] First-run onboarding — brief tooltip or settings window on first launch explaining the tray icon

### 1.3 Build & Distribution
- [ ] Set up GitHub repository (README with screenshots, GIFs, feature list)
- [ ] Create GitHub Actions CI pipeline for automated builds
- [ ] Sign the Windows executable (or document how to bypass SmartScreen warning)
- [ ] Generate SHA256 checksums for each release
- [ ] Submit to winget package manager
- [ ] Submit to Chocolatey
- [ ] Submit to AlternativeTo (as Punto Switcher alternative)
- [ ] List on Product Hunt

### 1.4 Testing & Quality
- [ ] Expand QA tool coverage to 25+ test suites
- [ ] Add regression test for each bug fix
- [ ] Performance benchmark: measure CPU/memory with 1hr sustained typing session
- [ ] Compatibility testing: Windows 10, Windows 11 (latest builds)

---

## Phase 2: Cross-Platform (v0.5.0)

**Goal:** macOS support — unlock a new platform and prove cross-platform architecture.

### 2.1 macOS Port
- [ ] Abstract OS-specific keyboard hooks (pynput should work, but test thoroughly on macOS)
- [ ] Handle macOS Accessibility permissions (app needs Input Monitoring permission)
- [ ] Replace pystray with macOS-native menu bar implementation (rumps library or similar)
- [ ] Replace Tkinter settings with a lightweight alternative that looks native on macOS
- [ ] Test with macOS keyboard layouts (Ukrainian QWERTY may differ from Windows)
- [ ] Build .app bundle with py2app or PyInstaller for macOS
- [ ] Code signing and notarization for macOS distribution

### 2.2 Shared Core Refactor
- [ ] Extract platform-specific code into `platform/` modules (win.py, mac.py)
- [ ] Ensure config.json paths follow OS conventions (AppData on Windows, ~/Library on macOS)
- [ ] Unified logging location per OS

---

## Phase 3: Language Expansion (v0.6.0 — v0.8.0)

**Goal:** Add 4 new language pairs, each opening a new geographic market.

### 3.1 Language Pack Architecture
- [ ] Design a pluggable language pack format (dictionary files + character mapping + validation rules)
- [ ] Allow users to select active language pair(s) in settings
- [ ] Support multiple simultaneous language pairs (detect which pair is relevant per word)

### 3.2 Priority Languages (ordered by market opportunity)
Each language pair requires: character mapping table, frequency dictionary, validation dictionary, and QA test suite.

1. **English ↔ Russian** — Largest market. Direct Punto Switcher competitor. ~150M Russian-speaking computer users.
2. **English ↔ Hebrew** — Strong demand in Israel (~9.5M). Few good tools exist.
3. **English ↔ Spanish** — Huge population but Latin↔Latin switching is different (accented characters, ñ). May need different detection heuristics.
4. **English ↔ Arabic** — Large market. RTL adds complexity but high value.
5. **English ↔ French/German/Portuguese** — Lower priority (Latin scripts, smaller layout confusion) but easy wins since the infrastructure will exist.

### 3.3 Community Contributions
- [ ] Document how to create a language pack (CONTRIBUTING.md)
- [ ] Create a template language pack with tests
- [ ] Accept community-submitted language packs via PR

---

## Phase 4: Growth & Community (Ongoing)

### 4.1 SEO & Content
- [ ] Landing page live (see separate landing page plan)
- [ ] Blog post: "Why we built AutoSwitcher" (founding story, Ukrainian perspective)
- [ ] Blog post: "AutoSwitcher vs Punto Switcher" (SEO keyword targeting)
- [ ] Blog post: "How AutoSwitcher detects your keyboard layout" (technical deep dive, builds trust)

### 4.2 Community Outreach
- [ ] Ukrainian tech communities: DOU.ua, Ukrainian Telegram dev channels
- [ ] Reddit: r/ukraine, r/Ukrainian, r/opensource, r/bilingual
- [ ] Hacker News: Show HN launch
- [ ] GitHub: Encourage stars, issue templates, contributor guide

### 4.3 Distribution Expansion
- [ ] Microsoft Store submission (adds legitimacy for non-technical users)
- [ ] Homebrew cask for macOS
- [ ] Scoop bucket for Windows
- [ ] AUR package for future Linux support

### 4.4 Future Features (Post-v1.0 Backlog)
- [ ] Linux support (X11 + Wayland)
- [ ] Per-application whitelist profiles
- [ ] Clipboard correction mode (correct text already on clipboard)
- [ ] Browser extension companion (for web-only users)
- [ ] Auto-update mechanism

---

## Risk Mitigation

| Risk | Strategy |
|------|----------|
| macOS accessibility permissions friction | Clear first-run guide + documentation |
| Windows SmartScreen blocking unsigned exe | Code signing certificate or thorough "how to allow" documentation |
| Detection algorithm false positives | Conservative defaults + easy undo + whitelist + user control |
| Low discoverability | SEO-optimized landing page + community outreach + AlternativeTo listing |
| Maintenance burden | Keep codebase simple, attract contributors, modular language packs |

---

## Success Metrics

| Metric | Phase 1 Target | Phase 2 Target | Phase 4 Target |
|--------|----------------|----------------|----------------|
| GitHub Stars | 100 | 500 | 2,000 |
| Active Users (estimated via downloads) | 500 | 2,000 | 10,000 |
| Language Pairs | 1 (EN↔UA) | 1 (EN↔UA) | 5+ |
| Platforms | Windows | Windows + macOS | Win + Mac + Linux |
| False Positive Rate | <5% | <3% | <2% |

---

## Competitive Positioning Summary

**"The privacy-first, open-source keyboard layout switcher. Made in Ukraine."**

- vs **Punto Switcher**: We're open source with zero telemetry. They're owned by Yandex.
- vs **Caramba Switcher**: We're free forever. They charge $1/mo.
- vs **Mahou**: We have modern UX that works out of the box. They have 96 settings tabs.
- vs **OS autocorrect**: We actually solve the wrong-layout problem. Windows/macOS don't.
