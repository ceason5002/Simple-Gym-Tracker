THEMES = {
    "dark_gray": {
        "bg": "#0b0b0b",
        "card": "#111111",
        "text": "#f2f2f2",
        "muted": "#b8b8b8",
        "accent": "#686B6D",
        "border": "#202020",
    },
    "pink_white_red": {
        "bg": "#ffffff",
        "card": "#fff5fb",
        "text": "#111111",
        "muted": "#555555",
        "accent": "#ff4da6",
        "border": "#ffb3d9",
    },
}


# ---------------------------------------------------------------------------
# Custom themes
# ---------------------------------------------------------------------------
import re

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
CUSTOM_FIELDS = ("bg", "card", "text", "accent")   # the user picks these; muted + border are derived
CUSTOM_DEFAULT = {"bg": "#0f1115", "card": "#171a21", "text": "#f1f3f7", "accent": "#5b8cff"}
STARTERS = {
    "Midnight": {"bg": "#0f1115", "card": "#171a21", "text": "#f1f3f7", "accent": "#5b8cff"},
    "Forest":   {"bg": "#0e1411", "card": "#151d18", "text": "#e9f2ec", "accent": "#3fbf7f"},
    "Sunset":   {"bg": "#1a1012", "card": "#24171a", "text": "#fbecea", "accent": "#ff7a45"},
    "Paper":    {"bg": "#f6f4ef", "card": "#ffffff", "text": "#1d1b18", "accent": "#c2410c"},
    "Ocean":    {"bg": "#eef6fb", "card": "#ffffff", "text": "#0d2433", "accent": "#0b84c6"},
}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02x}" for c in rgb)


def mix(a, b, t):
    """Blend colour a toward b by t (0..1)."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex(tuple(x + (y - x) * t for x, y in zip(ra, rb)))


def _lum(h):
    def ch(c):
        c /= 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (ch(c) for c in _rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def clean_custom(data):
    """Return a validated {bg, card, text, accent} dict, or raise ValueError.

    These values are written into a <style> tag, so only strict #rrggbb hex is accepted.
    """
    out = {}
    for f in CUSTOM_FIELDS:
        v = str((data or {}).get(f, "")).strip()
        if not HEX_RE.match(v):
            raise ValueError(f"{f} must be a colour like #1a2b3c")
        out[f] = v.lower()
    if contrast(out["text"], out["bg"]) < 3:
        raise ValueError("Text and background are too similar to read. Pick colours with more contrast.")
    return out


def build_custom(colors):
    """Expand the four picked colours into the full token set the templates use."""
    try:
        c = clean_custom(colors)
    except ValueError:
        c = CUSTOM_DEFAULT
    return {
        "bg": c["bg"], "card": c["card"], "text": c["text"], "accent": c["accent"],
        "muted": mix(c["text"], c["bg"], 0.38),
        "border": mix(c["bg"], c["text"], 0.14),
    }
