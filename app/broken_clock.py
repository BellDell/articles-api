"""Pure calculation and formatting helpers for the Broken Clock Calculator.

This module has no Flask, sqlite3, or environment variable dependencies.
All functions are pure: same inputs always produce the same outputs.
"""


def parse_hhmm(s):
    """Parse a "HH:MM" string into (hours, minutes) tuple or None if invalid."""
    try:
        parts = s.split(":")
        h, m = int(parts[0]), int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
        return h, m
    except (ValueError, IndexError, AttributeError):
        return None


def to_minutes(h, m):
    """Convert hours and minutes to total minutes since midnight."""
    return h * 60 + m


def compute_offset(real_minutes, wrong_minutes):
    """Compute the signed offset (wrong - real), normalised to the shortest path.

    Returns an integer in the range -719..+719 (minutes).
    """
    raw_diff = wrong_minutes - real_minutes
    if raw_diff > 720:
        return raw_diff - 1440
    elif raw_diff < -720:
        return raw_diff + 1440
    else:
        return raw_diff


def format_offset_human(offset_minutes):
    """Format offset_minutes as a human-readable string, e.g. "+60 minutes"."""
    if offset_minutes >= 0:
        return f"+{offset_minutes} minutes"
    else:
        return f"{offset_minutes} minutes"


def compute_clock_status(offset_minutes):
    """Return "fast", "slow", or "accurate" based on the offset."""
    if offset_minutes > 0:
        return "fast"
    elif offset_minutes < 0:
        return "slow"
    else:
        return "accurate"


def compute_reference_points(target_wrong_times, offset_minutes):
    """Build a list of reference point dicts for the given target times.

    Each dict has keys: wrong_time, real_time, day_shift.
    """
    reference_points = []
    for target in target_wrong_times:
        tp = parse_hhmm(target)
        if tp is None:
            raise ValueError(f"Invalid target time: {target}")
        target_minutes = to_minutes(*tp)
        real_at_target = target_minutes - offset_minutes
        day_shift = 0
        if real_at_target < 0:
            real_at_target += 1440
            day_shift = -1
        elif real_at_target >= 1440:
            real_at_target -= 1440
            day_shift = 1
        real_time = f"{real_at_target // 60:02d}:{real_at_target % 60:02d}"
        reference_points.append({
            "wrong_time": target,
            "real_time": real_time,
            "day_shift": day_shift,
        })
    return reference_points


def format_explanation(offset_human, clock_status):
    """Return the explanation sentence for the calculation result."""
    return (
        f"The wrong clock is {offset_human} relative to the real clock "
        f"(status: {clock_status})."
    )


def format_compact_ref_point(rp):
    """Format a single reference-point dict into a compact string.

    Example outputs:
        "07:00 → 06:00"
        "23:00 → 22:00 (next day)"
        "00:00 → 01:00 (previous day)"
    """
    label = f"{rp['wrong_time']} \u2192 {rp['real_time']}"
    if rp["day_shift"] == 1:
        label += " (next day)"
    elif rp["day_shift"] == -1:
        label += " (previous day)"
    return label
