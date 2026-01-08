from .theme import THEMES

def theme_vars(request):
    key = "dark_gray"
    if request.user.is_authenticated and hasattr(request.user, "profile"):
        key = request.user.profile.theme or "dark_gray"
    return {"theme_vars": THEMES.get(key, THEMES["dark_gray"]), "theme_key": key}
