from .theme import THEMES, build_custom


def theme_vars(request):
    key = "dark_gray"
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    if profile:
        key = profile.theme or "dark_gray"
    if key == "custom" and profile:
        return {"theme_vars": build_custom(profile.custom_theme), "theme_key": key}
    return {"theme_vars": THEMES.get(key, THEMES["dark_gray"]), "theme_key": key}
