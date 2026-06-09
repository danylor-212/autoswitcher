# engine.py — the pure word-decision engine. No I/O, no Win32, no threads:
# given the physical key sequence (as EN chars), the foreground layout, and
# the config flags, return what (if anything) to replace on screen.
#
# One symmetric rule replaces v1's asymmetric branch ladder:
#
#   correct  ⇔  other_valid AND (NOT shown_valid
#                                OR logP(other) − logP(shown) ≥ dominance)
#
# 'shown' is the rendering the foreground layout actually produced; 'other'
# is the same keys rendered through the opposite layout. Punctuation needs no
# special-case heuristics: we score BOTH the full-token reading (punct keys
# may be letters in the other layout: ',fub'→«баги», ',elt'→«буде») and the
# edge-stripped reading with punctuation re-attached, and keep the better one.

from dataclasses import dataclass

from dictionaries import STRIP_PUNCT

# Dominance thresholds (log10 units): the other reading must be at least this
# many orders of magnitude more probable to overrule a VALID shown word.
DOMINANCE_KNOWN   = 2.0   # foreground layout positively identified
DOMINANCE_UNKNOWN = 3.5   # layout unknown — be much more reluctant


@dataclass
class Decision:
    action: str             # 'none' | 'switch' | 't9'
    app_text: str = ''      # exactly what the screen shows (to backspace)
    replacement: str = ''   # text to type instead
    reason: str = ''        # for logging/tests


def _strip_edges(token: str):
    """(core, leading_punct, trailing_punct) using the shared punct set."""
    core = token.strip(STRIP_PUNCT)
    if not core:
        return '', token, ''
    start = token.index(core[0])
    return core, token[:start], token[start + len(core):]


def _best_candidate(shown_token, translate, valid, logp):
    """Best reading of these keys in the other layout.

    Tries the full token first (punct chars often map to letters), then the
    edge-stripped core with the shown-side punctuation re-attached.
    Returns (replacement, logp) or (None, None).
    """
    best = (None, None)
    full = translate(shown_token)
    if valid(full):
        best = (full, logp(full))
    core, lead, trail = _strip_edges(shown_token)
    if core and (lead or trail):
        cand = translate(core)
        if valid(cand):
            score = logp(cand)
            if best[0] is None or score > best[1]:
                best = (lead + cand + trail, score)
    return best


def decide(en_token: str, layout: str, *, lex, keymap,
           en_to_uk=True, uk_to_en=True, t9_en=False, t9_uk=False,
           t9=None) -> Decision:
    """Decide the correction for one finished word.

    en_token — the physical keys typed, rendered as EN-layout chars.
    layout   — 'EN' | 'UK' | 'unknown' (foreground window at typing time).
    t9       — optional GrammarEngine for typo correction.
    """
    if not en_token or not en_token.strip(STRIP_PUNCT):
        return Decision('none', reason='empty/punct-only')

    dominance = DOMINANCE_KNOWN if layout in ('EN', 'UK') else DOMINANCE_UNKNOWN

    if layout == 'UK':
        shown_token = keymap.to_ukrainian(en_token)
        shown_valid, shown_logp = lex.uk_valid, lex.logp_uk
        other_valid, other_logp = lex.en_valid, lex.logp_en
        translate = keymap.to_english
        direction_on = uk_to_en
        t9_on, t9_fn = t9_uk, (t9.correct_ukrainian if t9 else None)
    else:
        # Layout EN or unknown: the screen shows the EN rendering.
        shown_token = en_token
        shown_valid, shown_logp = lex.en_valid, lex.logp_en
        other_valid, other_logp = lex.uk_valid, lex.logp_uk
        translate = keymap.to_ukrainian
        direction_on = en_to_uk
        t9_on, t9_fn = t9_en, (t9.correct_english if t9 else None)

    core, lead, trail = _strip_edges(shown_token)
    is_shown_valid = shown_valid(core)

    # ── Layout switch ─────────────────────────────────────────────────────
    if direction_on:
        replacement, cand_logp = _best_candidate(
            shown_token, translate, other_valid, other_logp)
        if replacement is not None and replacement != shown_token:
            if not is_shown_valid:
                return Decision('switch', shown_token, replacement,
                                reason='shown-invalid')
            if cand_logp - shown_logp(core) >= dominance:
                return Decision('switch', shown_token, replacement,
                                reason='dominance')

    # ── T9 typo correction (only when the shown word is invalid) ─────────
    if t9_on and t9_fn and not is_shown_valid and core:
        suggestion = t9_fn(core)
        if suggestion and suggestion != core:
            return Decision('t9', shown_token, lead + suggestion + trail,
                            reason='t9')

    return Decision('none', reason='valid' if is_shown_valid else 'no-candidate')
