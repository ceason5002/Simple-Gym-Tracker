import datetime as dt
import json
import re
from decimal import Decimal, InvalidOperation

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import nutrition
from .models import FoodLogEntry, NutritionProfile, SavedFood, WaterLog

MEALS = [m for m, _ in FoodLogEntry.MEAL_CHOICES]
BARCODE_RE = re.compile(r"^\d{6,14}$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _profile(user):
    return NutritionProfile.objects.get_or_create(user=user)[0]


def _parse_date(value):
    try:
        return dt.date.fromisoformat(value) if value else timezone.localdate()
    except ValueError:
        return timezone.localdate()


def _dec(value, lo=Decimal("0"), hi=Decimal("100000")):
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("not a number")
    if not d.is_finite() or d < lo or d > hi:
        raise ValueError("out of range")
    return d


def _clean_food(data):
    """Validate a food dict from the client into model-ready fields."""
    if not isinstance(data, dict):
        raise ValueError("food missing")
    name = str(data.get("name") or "").strip()[:120]
    if not name:
        raise ValueError("food needs a name")
    source = data.get("source") if data.get("source") in ("usda", "off", "manual", "saved") else "manual"
    return {
        "name": name,
        "brand": str(data.get("brand") or "").strip()[:120],
        "serving_desc": str(data.get("serving_desc") or "1 serving").strip()[:80] or "1 serving",
        "calories": _dec(data.get("calories", 0), hi=Decimal("20000")),
        "protein": _dec(data.get("protein", 0), hi=Decimal("2000")),
        "carbs": _dec(data.get("carbs", 0), hi=Decimal("2000")),
        "fat": _dec(data.get("fat", 0), hi=Decimal("2000")),
        "source": source,
        "_barcode": str(data.get("barcode") or "")[:32],
        "_source_id": str(data.get("source_id") or "")[:64],
    }


def _body(request):
    try:
        return json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return {}


def _bad(msg, status=400):
    return JsonResponse({"error": msg}, status=status)


def _saved_dict(f):
    return {
        "id": f.id, "name": f.name, "brand": f.brand, "barcode": f.barcode, "serving_desc": f.serving_desc,
        "calories": float(f.calories), "protein": float(f.protein), "carbs": float(f.carbs), "fat": float(f.fat),
        "source": "saved", "source_id": str(f.id),
    }


def _day_payload(user, date):
    targets = nutrition.compute_targets(_profile(user))
    entries = list(FoodLogEntry.objects.filter(user=user, date=date))
    totals = {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0}
    rows = []
    for e in entries:
        s = float(e.servings)
        row = {
            "id": e.id, "meal": e.meal, "name": e.name, "brand": e.brand, "serving_desc": e.serving_desc,
            "servings": s,
            "calories": round(float(e.calories) * s, 1), "protein": round(float(e.protein) * s, 1),
            "carbs": round(float(e.carbs) * s, 1), "fat": round(float(e.fat) * s, 1),
        }
        for k in totals:
            totals[k] += row[k]
        rows.append(row)
    water = WaterLog.objects.filter(user=user, date=date).aggregate(t=Sum("amount_oz"))["t"] or 0
    today = timezone.localdate()
    return {
        "date": date.isoformat(),
        "is_today": date == today,
        "label": "Today" if date == today else "Yesterday" if date == today - dt.timedelta(days=1)
                 else date.strftime("%a, %b %-d"),
        "targets": targets.as_dict(),
        "totals": {k: round(v, 1) for k, v in totals.items()},
        "water_oz": float(water),
        "entries": rows,
    }


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@login_required
def nutrition_dashboard(request):
    date = _parse_date(request.GET.get("d"))
    return render(request, "nutrition/dashboard.html", {
        "day": _day_payload(request.user, date),
        "saved": [_saved_dict(f) for f in request.user.saved_foods.all()],
        "meals": FoodLogEntry.MEAL_CHOICES,
    })


class NutritionProfileForm(forms.ModelForm):
    class Meta:
        model = NutritionProfile
        fields = ["goal", "sex", "age", "height_in", "weight_lb", "activity",
                  "calorie_override", "protein_override", "carbs_override", "fat_override", "water_override_oz"]
        widgets = {"goal": forms.RadioSelect, "sex": forms.RadioSelect}
        labels = {
            "calorie_override": "Calories (kcal)", "protein_override": "Protein (g)",
            "carbs_override": "Carbs (g)", "fat_override": "Fat (g)", "water_override_oz": "Water (oz)",
        }

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.fields["sex"].choices = NutritionProfile.SEX_CHOICES
        self.fields["sex"].required = False
        self.fields["age"].widget.attrs.update(min=13, max=100)
        for f in ("calorie_override", "protein_override", "carbs_override", "fat_override", "water_override_oz"):
            self.fields[f].widget.attrs["placeholder"] = "Auto"


@login_required
def nutrition_settings(request):
    profile = _profile(request.user)
    form = NutritionProfileForm(request.POST or None, instance=profile)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Nutrition goals updated.")
        return redirect("nutrition")
    preview = nutrition.compute_targets(form.instance if form.is_bound and form.is_valid() else profile)
    return render(request, "nutrition/settings.html", {"form": form, "targets": preview})


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------

@login_required
@require_GET
def api_day(request):
    return JsonResponse(_day_payload(request.user, _parse_date(request.GET.get("d"))))


@login_required
@require_GET
def api_search(request):
    q = (request.GET.get("q") or "").strip()[:80]
    if len(q) < 2:
        return JsonResponse({"results": [], "saved": []})
    saved = [_saved_dict(f) for f in request.user.saved_foods.filter(name__icontains=q)[:5]]
    try:
        results = nutrition.search_usda(q)
    except nutrition.FoodLookupError as e:
        return JsonResponse({"results": [], "saved": saved, "error": str(e)}, status=502)
    return JsonResponse({"results": results, "saved": saved})


@login_required
@require_GET
def api_barcode(request, code):
    if not BARCODE_RE.match(code):
        return _bad("That doesn't look like a barcode.")
    saved = request.user.saved_foods.filter(barcode=code).first()
    if saved:
        return JsonResponse({"food": _saved_dict(saved)})
    try:
        food = nutrition.lookup_barcode(code)
    except nutrition.FoodLookupError:
        return _bad("The food databases couldn't be reached. Try again in a moment.", 502)
    if not food:
        return _bad("No match for this barcode. Try searching by name or add it manually.", 404)
    return JsonResponse({"food": food})


@login_required
@require_POST
def api_log_add(request):
    data = _body(request)
    try:
        food = _clean_food(data.get("food"))
        servings = _dec(data.get("servings", 1), lo=Decimal("0.01"), hi=Decimal("100"))
    except ValueError as e:
        return _bad(str(e))
    meal = data.get("meal") if data.get("meal") in MEALS else "snack"
    date = _parse_date(data.get("date"))
    FoodLogEntry.objects.create(
        user=request.user, date=date, meal=meal, servings=servings,
        **{k: v for k, v in food.items() if not k.startswith("_")},
    )
    return JsonResponse(_day_payload(request.user, date))


@login_required
@require_POST
def api_log_delete(request, entry_id):
    entry = get_object_or_404(FoodLogEntry, id=entry_id, user=request.user)
    date = entry.date
    entry.delete()
    return JsonResponse(_day_payload(request.user, date))


@login_required
@require_POST
def api_saved_add(request):
    try:
        food = _clean_food(_body(request).get("food"))
    except ValueError as e:
        return _bad(str(e))
    existing = request.user.saved_foods.filter(
        name=food["name"], brand=food["brand"], serving_desc=food["serving_desc"]).first()
    if existing:
        return JsonResponse({"food": _saved_dict(existing), "created": False})
    f = SavedFood.objects.create(
        user=request.user,
        name=food["name"], brand=food["brand"], serving_desc=food["serving_desc"],
        calories=food["calories"], protein=food["protein"], carbs=food["carbs"], fat=food["fat"],
        source=food["source"] if food["source"] in ("usda", "off") else "manual",
        barcode=food["_barcode"], source_id=food["_source_id"],
    )
    return JsonResponse({"food": _saved_dict(f), "created": True})


@login_required
@require_POST
def api_saved_delete(request, food_id):
    get_object_or_404(SavedFood, id=food_id, user=request.user).delete()
    return JsonResponse({"ok": True})


@login_required
@require_POST
def api_water_add(request):
    data = _body(request)
    try:
        oz = _dec(data.get("oz", 8), lo=Decimal("0.5"), hi=Decimal("200"))
    except ValueError as e:
        return _bad(str(e))
    date = _parse_date(data.get("date"))
    WaterLog.objects.create(user=request.user, date=date, amount_oz=oz)
    return JsonResponse(_day_payload(request.user, date))


@login_required
@require_POST
def api_water_undo(request):
    date = _parse_date(_body(request).get("date"))
    last = WaterLog.objects.filter(user=request.user, date=date).order_by("-created_at", "-id").first()
    if last:
        last.delete()
    return JsonResponse(_day_payload(request.user, date))
