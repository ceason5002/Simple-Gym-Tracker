"""NutrientAI services: daily targets, and food lookups from USDA FoodData Central and Open Food Facts.

Every lookup returns foods in one normalized shape (macros are per serving):
    {"name", "brand", "barcode", "serving_desc", "calories", "protein", "carbs", "fat", "source", "source_id"}
"""
import logging
from dataclasses import dataclass

import httpx
from django.conf import settings

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Daily targets
# ---------------------------------------------------------------------------

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
GOAL_CALORIE_DELTA = {"lose": -500, "maintain": 0, "gain": 300}   # ~1 lb/week loss; lean gain
PROTEIN_G_PER_LB = {"lose": 1.0, "maintain": 0.8, "gain": 0.9}    # higher when cutting to keep muscle
FAT_SHARE = 0.25
WATER_OZ_PER_LB = 0.5
MIN_CALORIES = 1200

DEFAULT_TARGETS = {"calories": 2000, "protein": 150, "carbs": 200, "fat": 67, "water_oz": 64}


@dataclass
class Targets:
    calories: int
    protein: int
    carbs: int
    fat: int
    water_oz: int
    maintenance: int | None   # estimated maintenance calories, None when the profile is incomplete
    complete: bool            # whether the profile had enough data to calculate

    def as_dict(self):
        return self.__dict__.copy()


def profile_is_complete(p) -> bool:
    return bool(p.sex and p.age and p.height_in and p.weight_lb)


def maintenance_calories(p) -> int:
    """Mifflin-St Jeor BMR times an activity factor."""
    kg = float(p.weight_lb) * 0.45359237
    cm = float(p.height_in) * 2.54
    bmr = 10 * kg + 6.25 * cm - 5 * p.age + (5 if p.sex == "male" else -161)
    return round(bmr * ACTIVITY_FACTORS.get(p.activity, 1.55))


def compute_targets(p) -> Targets:
    if profile_is_complete(p):
        maintenance = maintenance_calories(p)
        calories = max(MIN_CALORIES, maintenance + GOAL_CALORIE_DELTA.get(p.goal, 0))
        protein = round(float(p.weight_lb) * PROTEIN_G_PER_LB.get(p.goal, 0.8))
        fat = round(calories * FAT_SHARE / 9)
        water = round(float(p.weight_lb) * WATER_OZ_PER_LB)
        complete = True
    else:
        d = DEFAULT_TARGETS
        maintenance, calories, protein, fat, water = None, d["calories"], d["protein"], d["fat"], d["water_oz"]
        complete = False

    # Manual overrides win; carbs fill whatever calories are left
    calories = p.calorie_override or calories
    protein = p.protein_override or protein
    fat = p.fat_override or fat
    carbs = p.carbs_override or max(0, round((calories - protein * 4 - fat * 9) / 4))
    water = p.water_override_oz or water
    return Targets(calories, protein, carbs, fat, water, maintenance, complete)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

USER_AGENT = "SimpleGymTracker/1.0 (nutrition lookup)"
TIMEOUT = httpx.Timeout(8.0, connect=4.0)


class FoodLookupError(Exception):
    """A food service could not be reached or returned something unusable."""


def _client():
    # trust_env=True (the default) lets PythonAnywhere's outbound proxy apply
    return httpx.Client(timeout=TIMEOUT, headers={"User-Agent": USER_AGENT})


def _num(v):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    return f if f >= 0 else None


def _food(name, brand, barcode, serving_desc, kcal, protein, carbs, fat, source, source_id):
    return {
        "name": (name or "Unnamed food").strip()[:120],
        "brand": (brand or "").strip()[:120],
        "barcode": barcode or "",
        "serving_desc": (serving_desc or "1 serving").strip()[:80],
        "calories": round(kcal or 0, 1),
        "protein": round(protein or 0, 1),
        "carbs": round(carbs or 0, 1),
        "fat": round(fat or 0, 1),
        "source": source,
        "source_id": str(source_id or ""),
    }


# ---- Open Food Facts (barcodes) -------------------------------------------

OFF_URL = "https://world.openfoodfacts.org/api/v2/product/{code}.json"
OFF_FIELDS = "code,product_name,brands,serving_size,nutriments"


def normalize_off(product: dict) -> dict | None:
    n = product.get("nutriments") or {}

    def pick(key, suffix):
        val = _num(n.get(f"{key}_{suffix}"))
        if val is None and key == "energy-kcal":     # some products only list kJ
            kj = _num(n.get(f"energy-kj_{suffix}")) or _num(n.get(f"energy_{suffix}"))
            val = kj / 4.184 if kj is not None else None
        return val

    for suffix, desc in (("serving", product.get("serving_size") or "1 serving"), ("100g", "100 g")):
        kcal = pick("energy-kcal", suffix)
        if kcal is not None:
            return _food(
                product.get("product_name"), (product.get("brands") or "").split(",")[0], product.get("code"),
                desc, kcal, pick("proteins", suffix), pick("carbohydrates", suffix), pick("fat", suffix),
                "off", product.get("code"),
            )
    return None   # product exists but has no usable nutrition data


def lookup_off(code: str) -> dict | None:
    try:
        with _client() as c:
            r = c.get(OFF_URL.format(code=code), params={"fields": OFF_FIELDS})
    except httpx.HTTPError as e:
        raise FoodLookupError(f"Open Food Facts unreachable: {e}") from e
    if r.status_code == 404:
        return None
    if r.status_code != 200:
        raise FoodLookupError(f"Open Food Facts returned {r.status_code}")
    data = r.json()
    if data.get("status") != 1 or not data.get("product"):
        return None
    return normalize_off(data["product"])


# ---- USDA FoodData Central (search + barcode fallback) ---------------------

USDA_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"
USDA_DATA_TYPES = ["Foundation", "SR Legacy", "Survey (FNDDS)", "Branded"]
NUTRIENT_IDS = {
    "calories": (1008, 2047, 2048),   # Energy (kcal); Foundation foods use the Atwater variants
    "protein": (1003,),
    "fat": (1004,),
    "carbs": (1005,),
}
PER_GRAM_UNITS = {"g", "grm", "ml", "mlt"}


def normalize_usda(item: dict) -> dict | None:
    values = {}
    for n in item.get("foodNutrients") or []:
        nid, unit = n.get("nutrientId"), (n.get("unitName") or "").lower()
        for key, ids in NUTRIENT_IDS.items():
            if nid in ids and key not in values and (key != "calories" or unit == "kcal"):
                values[key] = _num(n.get("value"))
    if values.get("calories") is None:
        return None

    # Search results report nutrients per 100 g. Branded foods also give a serving size to scale to.
    scale, desc = 1.0, "100 g"
    size, unit = _num(item.get("servingSize")), (item.get("servingSizeUnit") or "").lower()
    if size and unit in PER_GRAM_UNITS:
        scale = size / 100
        unit_label = "ml" if unit in ("ml", "mlt") else "g"
        household = (item.get("householdServingFullText") or "").strip()
        desc = f"{household} ({size:g} {unit_label})" if household else f"{size:g} {unit_label}"

    def s(key):
        v = values.get(key)
        return v * scale if v is not None else 0

    brand = item.get("brandName") or item.get("brandOwner") or ""
    name = (item.get("description") or "").strip()
    if name.isupper():
        name = name.title()
    return _food(name, brand, item.get("gtinUpc"), desc, s("calories"), s("protein"), s("carbs"), s("fat"),
                 "usda", item.get("fdcId"))


def _usda_search(query: str, data_types, page_size: int) -> list[dict]:
    key = getattr(settings, "USDA_API_KEY", "") or "DEMO_KEY"
    try:
        with _client() as c:
            r = c.post(USDA_SEARCH_URL, params={"api_key": key},
                       json={"query": query, "pageSize": page_size, "dataType": data_types})
    except httpx.HTTPError as e:
        raise FoodLookupError(f"USDA unreachable: {e}") from e
    if r.status_code == 429:
        raise FoodLookupError("USDA rate limit reached; add a USDA_API_KEY or try again later")
    if r.status_code != 200:
        raise FoodLookupError(f"USDA returned {r.status_code}")
    return r.json().get("foods") or []


def _rank(item: dict, query: str) -> tuple:
    """Plain foods before branded ones; names that start with (or contain every word of) the query first."""
    name = (item.get("description") or "").lower()
    q = query.lower().strip()
    words = q.split()
    branded = item.get("dataType") == "Branded"
    return (
        0 if name.startswith(q) else 1 if all(w in name for w in words) else 2,
        1 if branded else 0,
        len(name),
    )


def search_usda(query: str, limit: int = 20) -> list[dict]:
    items = _usda_search(query, USDA_DATA_TYPES, 50)
    results, seen = [], set()
    for item in sorted(items, key=lambda i: _rank(i, query)):
        food = normalize_usda(item)
        if not food:
            continue
        dedupe = (food["name"].lower(), food["brand"].lower(), food["serving_desc"])
        if dedupe not in seen:
            seen.add(dedupe)
            results.append(food)
        if len(results) >= limit:
            break
    return results


def lookup_usda_barcode(code: str) -> dict | None:
    want = code.lstrip("0")
    for item in _usda_search(code, ["Branded"], 10):
        if (item.get("gtinUpc") or "").lstrip("0") == want:
            return normalize_usda(item)
    return None


def lookup_barcode(code: str) -> dict | None:
    """Open Food Facts first (wider coverage), then USDA branded foods."""
    errors = []
    for fn in (lookup_off, lookup_usda_barcode):
        try:
            food = fn(code)
        except FoodLookupError as e:
            errors.append(str(e))
            log.warning("barcode lookup failed: %s", e)
            continue
        if food:
            return food
    if len(errors) == 2:
        raise FoodLookupError("; ".join(errors))
    return None
