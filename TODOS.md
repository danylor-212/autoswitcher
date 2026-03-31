# AutoSwitcher — TODOS

## P2: Windows Installer

**What:** Create a proper Windows installer using NSIS or WiX Toolset.

**Why:** Currently users get a raw `.exe`. An installer adds:
- Auto-start on Windows boot (registry key)
- Start Menu entry
- Proper uninstaller (Add/Remove Programs)
- Optional: associate `.autoswitcher` config files

**Pros:** Required before any public release. Makes the tool feel like a real app.
**Cons:** NSIS/WiX learning curve. Adds a build step.
**Context:** The exe currently lives in `dist/`. Users manually put it in a folder.
**Effort:** ~1 day human / ~20 min CC+gstack
**Priority:** P2 — needed before v1.0 public release
**Depends on:** v0.4 feature-complete

---

## P2: Sentence-Level Correction

**What:** A hotkey (e.g., Ctrl+Shift+Space) that retroactively corrects all words
typed since the last sentence break (`.`, `!`, `?`, or beginning of typing session).

**Why:** Users often type an entire sentence before noticing the layout is wrong.
Word-by-word correction requires re-triggering after every word. Sentence mode
fixes everything at once.

**Pros:** Dramatically better UX for "I typed a whole paragraph in the wrong layout" scenario.
**Cons:** More complex buffer management (need to track sentence boundaries).
         Undo is harder (undoing a sentence-level correction).
**Context:** Currently the buffer is cleared at every word boundary, so historical
words are lost. Would need to either keep a rolling word history or handle sentence
correction differently (e.g., grab clipboard).
**Effort:** ~3 hours human / ~15 min CC+gstack
**Priority:** P2 — v0.5 target
**Depends on:** v0.4 stable (need undo infrastructure)

---

## P3: Statistics Dashboard

**What:** A simple daily/weekly stats view in the Settings window or a separate tab.
Tracks: corrections per day, correction accuracy (user accepted/undid), most-corrected words.

**Why:** Users want to know "is this thing actually helping me?" A counter ("47 corrections
today") provides that feedback. Accuracy tracking helps tune the detection thresholds.

**Pros:** Builds user confidence. Enables future accuracy improvements.
**Cons:** Requires persistent stats storage (extend config.json or separate file).
**Context:** v0.4 adds a daily correction counter. Stats dashboard is the next step.
**Effort:** ~2 hours human / ~10 min CC+gstack
**Priority:** P3 — nice to have
**Depends on:** v0.4 correction counter

---

## P3: Auto-Update Mechanism

**What:** On startup, check a GitHub releases URL for a newer version. If found,
show a tray notification: "v0.4.1 available — click to download."

**Why:** Users don't know when updates are available. Without auto-update, bugs stay
in the field indefinitely.

**Pros:** Standard for desktop utilities. Ensures users run current version.
**Cons:** Requires a release hosting location (GitHub is fine). Network call on startup.
**Context:** Currently users manually replace the .exe from the versions/ folder.
**Effort:** ~1 hour human / ~5 min CC+gstack
**Priority:** P3 — after installer exists
**Depends on:** Windows installer (needs an update mechanism that integrates with it)
