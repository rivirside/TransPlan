"""Blood-type canonicalization for model lookups (#413 / L-088).

US solid-organ allocation is **ABO-matched**. RhD is a red-cell antigen and is
not part of OPTN matching for kidney, liver, heart, lung, pancreas or
intestine, so there is no allocation mechanism by which an Rh-negative
candidate waits longer for an organ.

The shipped tables nevertheless carry eight entries with a systematic
Rh-negative penalty, and measurement (docs/rh-factor-report.md) found that
penalty to be a flat additive per-organ constant in 22 of 24 cells — the
signature of a hand-set convention, not an estimate. SRTR publishes blood type
as O/A/B/AB without Rh, so the eight-entry tables rest on four categories of
evidence and no calibration gate can adjudicate them even in principle.

Every model lookup therefore goes through `model_key`, which maps a patient's
blood type to its ABO group's representative entry. One change point makes the
wait multipliers, the compatibility score, the BBN CPT axis and the MCMC index
Rh-blind together, instead of editing eight-entry tables in five places. The
tables keep all eight entries: they are the record of what was there, and
reverting is a one-line change if Rh-stratified evidence ever appears.

**Why the `+` entry represents the group.** If the `-` offset is fabricated,
the `+` value is the ABO value. Even taking the opposite view — that the author
calibrated a group average and split it — Rh-positive is ~84% of every group,
so the average sits within 0.16 x 0.05..0.10 = 0.008..0.016 of the `+` entry.
Below the precision the tables are quoted to either way.

The UI keeps all eight options. Patients know their full blood type, and being
told plainly that Rh does not affect organ allocation is more useful than being
asked for it and silently penalized for the answer.
"""

ABO_GROUPS = ("O", "A", "B", "AB")

# Every key the model may be handed, mapped to its ABO group. Built rather
# than string-sliced so that an unexpected value falls through to the caller's
# own fallback instead of being silently truncated to something plausible —
# "AB+"[:-1] is right but "Bombay"[:-1] is not.
_TO_GROUP = {f"{g}{rh}": g for g in ABO_GROUPS for rh in ("+", "-")}


def abo_group(blood_type: str) -> str | None:
    """'O-' -> 'O'. None when the input is not a recognized ABO+Rh string."""
    return _TO_GROUP.get(blood_type)


def model_key(blood_type: str) -> str:
    """The table key a model lookup should use for this patient (#413).

    Returns the ABO group's Rh-positive entry, so O+ and O- resolve to the
    same value. Unrecognized input is returned unchanged, which lets each
    caller keep its own documented fallback (scoring's 85, the multipliers'
    1.0) rather than having this function invent one.
    """
    group = _TO_GROUP.get(blood_type)
    return f"{group}+" if group else blood_type
