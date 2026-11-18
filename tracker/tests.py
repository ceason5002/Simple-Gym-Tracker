import json
from decimal import Decimal
from unittest import mock

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from . import nutrition
from .models import FoodLogEntry, NutritionProfile, SavedFood, WaterLog


class TargetsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("t", password="x")
        self.p = NutritionProfile.objects.create(user=self.user)

    def fill(self, **kw):
        base = dict(sex="male", age=30, height_in=Decimal("70"), weight_lb=Decimal("180"), activity="moderate")
        for k, v in {**base, **kw}.items():
            setattr(self.p, k, v)

    def test_defaults_when_profile_incomplete(self):
        t = nutrition.compute_targets(self.p)
        self.assertFalse(t.complete)
        self.assertEqual(t.calories, 2000)
        self.assertIsNone(t.maintenance)

    def test_mifflin_maintenance(self):
        self.fill()
        # BMR = 10*81.65 + 6.25*177.8 - 5*30 + 5 = 1782.7; x1.55 = 2763
        self.assertEqual(nutrition.maintenance_calories(self.p), 2763)

    def test_goal_changes_calories_and_protein(self):
        self.fill(goal="maintain")
        m = nutrition.compute_targets(self.p)
        self.fill(goal="lose")
        lose = nutrition.compute_targets(self.p)
        self.fill(goal="gain")
        gain = nutrition.compute_targets(self.p)
        self.assertEqual(lose.calories, m.calories - 500)
        self.assertEqual(gain.calories, m.calories + 300)
        self.assertEqual(m.protein, 144)      # 0.8 g/lb
        self.assertEqual(lose.protein, 180)   # 1.0 g/lb when cutting
        self.assertEqual(m.water_oz, 90)

    def test_macros_add_up_to_calories(self):
        self.fill()
        t = nutrition.compute_targets(self.p)
        self.assertAlmostEqual(t.protein * 4 + t.carbs * 4 + t.fat * 9, t.calories, delta=12)

    def test_calorie_floor(self):
        self.fill(sex="female", age=70, height_in=Decimal("58"), weight_lb=Decimal("95"), activity="sedentary", goal="lose")
        self.assertEqual(nutrition.compute_targets(self.p).calories, nutrition.MIN_CALORIES)

    def test_overrides_win_and_carbs_fill_the_rest(self):
        self.fill()
        self.p.calorie_override, self.p.protein_override, self.p.fat_override = 2500, 200, 70
        t = nutrition.compute_targets(self.p)
        self.assertEqual((t.calories, t.protein, t.fat), (2500, 200, 70))
        self.assertEqual(t.carbs, round((2500 - 800 - 630) / 4))


class NormalizeTests(TestCase):
    def test_off_prefers_per_serving(self):
        f = nutrition.normalize_off({
            "code": "123", "product_name": "Bar", "brands": "Acme, Other", "serving_size": "40 g",
            "nutriments": {"energy-kcal_serving": 180, "proteins_serving": 10, "carbohydrates_serving": 20,
                           "fat_serving": 6, "energy-kcal_100g": 450},
        })
        self.assertEqual((f["serving_desc"], f["calories"], f["brand"]), ("40 g", 180, "Acme"))

    def test_off_falls_back_to_100g_and_kj(self):
        f = nutrition.normalize_off({"code": "1", "product_name": "X", "nutriments": {"energy-kj_100g": 418.4}})
        self.assertEqual((f["serving_desc"], f["calories"]), ("100 g", 100.0))

    def test_off_without_nutrition_is_none(self):
        self.assertIsNone(nutrition.normalize_off({"code": "1", "product_name": "X", "nutriments": {}}))

    def test_usda_branded_scales_to_serving(self):
        f = nutrition.normalize_usda({
            "fdcId": 9, "description": "GREEK YOGURT", "dataType": "Branded", "brandName": "Fage", "gtinUpc": "0001",
            "servingSize": 170, "servingSizeUnit": "g", "householdServingFullText": "1 container",
            "foodNutrients": [
                {"nutrientId": 1008, "unitName": "KCAL", "value": 59},
                {"nutrientId": 1003, "unitName": "G", "value": 10},
                {"nutrientId": 1005, "unitName": "G", "value": 3.6},
                {"nutrientId": 1004, "unitName": "G", "value": 0.4},
            ],
        })
        self.assertEqual(f["name"], "Greek Yogurt")
        self.assertEqual(f["serving_desc"], "1 container (170 g)")
        self.assertEqual((f["calories"], f["protein"]), (100.3, 17.0))

    def test_usda_ignores_kj_energy(self):
        f = nutrition.normalize_usda({"fdcId": 1, "description": "x", "foodNutrients": [
            {"nutrientId": 1008, "unitName": "kJ", "value": 400},
            {"nutrientId": 2047, "unitName": "KCAL", "value": 96},
        ]})
        self.assertEqual((f["calories"], f["serving_desc"]), (96, "100 g"))


@override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class ApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("api", password="pw-123456")
        self.client.force_login(self.user)
        self.food = {"name": "Oats", "brand": "", "serving_desc": "40 g", "calories": 150,
                     "protein": 5, "carbs": 27, "fat": 3, "source": "usda", "source_id": "1"}

    def post(self, name, body, *args):
        return self.client.post(reverse(name, args=args), json.dumps(body), content_type="application/json")

    def test_pages_need_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("nutrition")).status_code, 302)
        self.assertEqual(self.client.get(reverse("nutrition_api_day")).status_code, 302)

    def test_dashboard_renders(self):
        r = self.client.get(reverse("nutrition"))
        self.assertContains(r, 'id="day-data"')
        self.assertContains(r, "NutrientAI")

    def test_log_food_and_totals(self):
        r = self.post("nutrition_api_log_add", {"meal": "breakfast", "servings": 2, "food": self.food})
        d = r.json()
        self.assertEqual(r.status_code, 200)
        self.assertEqual(d["totals"]["calories"], 300)
        self.assertEqual(d["totals"]["protein"], 10)
        self.assertEqual(d["entries"][0]["meal"], "breakfast")

    def test_log_rejects_bad_input(self):
        self.assertEqual(self.post("nutrition_api_log_add", {"servings": 1, "food": {**self.food, "name": ""}}).status_code, 400)
        self.assertEqual(self.post("nutrition_api_log_add", {"servings": -1, "food": self.food}).status_code, 400)
        self.assertEqual(self.post("nutrition_api_log_add", {"servings": 1, "food": {**self.food, "calories": "abc"}}).status_code, 400)

    def test_delete_only_own_entries(self):
        other = User.objects.create_user("other", password="x")
        e = FoodLogEntry.objects.create(user=other, date=timezone.localdate(), name="X", calories=1, protein=0, carbs=0, fat=0)
        self.assertEqual(self.post("nutrition_api_log_delete", {}, e.id).status_code, 404)
        self.assertTrue(FoodLogEntry.objects.filter(id=e.id).exists())

    def test_water_add_and_undo(self):
        self.post("nutrition_api_water_add", {"oz": 8})
        d = self.post("nutrition_api_water_add", {"oz": 16}).json()
        self.assertEqual(d["water_oz"], 24)
        d = self.post("nutrition_api_water_undo", {}).json()
        self.assertEqual(d["water_oz"], 8)
        self.assertEqual(self.post("nutrition_api_water_add", {"oz": 0}).status_code, 400)

    def test_save_food_is_idempotent(self):
        a = self.post("nutrition_api_saved_add", {"food": self.food}).json()
        b = self.post("nutrition_api_saved_add", {"food": self.food}).json()
        self.assertTrue(a["created"])
        self.assertFalse(b["created"])
        self.assertEqual(SavedFood.objects.filter(user=self.user).count(), 1)

    def test_barcode_validation_and_saved_match(self):
        self.assertEqual(self.client.get(reverse("nutrition_api_barcode", args=["abc"])).status_code, 400)
        SavedFood.objects.create(user=self.user, name="Mine", barcode="0123456789012", calories=1, protein=0, carbs=0, fat=0)
        with mock.patch.object(nutrition, "lookup_barcode") as lb:
            r = self.client.get(reverse("nutrition_api_barcode", args=["0123456789012"]))
            lb.assert_not_called()
        self.assertEqual(r.json()["food"]["name"], "Mine")

    def test_barcode_not_found_and_service_down(self):
        with mock.patch.object(nutrition, "lookup_barcode", return_value=None):
            self.assertEqual(self.client.get(reverse("nutrition_api_barcode", args=["12345678"])).status_code, 404)
        with mock.patch.object(nutrition, "lookup_barcode", side_effect=nutrition.FoodLookupError("down")):
            self.assertEqual(self.client.get(reverse("nutrition_api_barcode", args=["12345678"])).status_code, 502)

    def test_search_merges_saved_foods(self):
        SavedFood.objects.create(user=self.user, name="Overnight oats", calories=300, protein=10, carbs=50, fat=8)
        with mock.patch.object(nutrition, "search_usda", return_value=[self.food]):
            d = self.client.get(reverse("nutrition_api_search"), {"q": "oats"}).json()
        self.assertEqual(len(d["saved"]), 1)
        self.assertEqual(d["results"][0]["name"], "Oats")

    def test_settings_saves_goal(self):
        r = self.client.post(reverse("nutrition_settings"), {
            "goal": "lose", "sex": "female", "age": 28, "height_in": "65", "weight_lb": "150", "activity": "light",
        })
        self.assertRedirects(r, reverse("nutrition"))
        p = NutritionProfile.objects.get(user=self.user)
        self.assertEqual(p.goal, "lose")
        self.assertTrue(self.client.get(reverse("nutrition_api_day")).json()["targets"]["complete"])


from . import theme as theme_mod


class CustomThemeTests(TestCase):
    good = {"bg": "#101010", "card": "#1a1a1a", "text": "#f0f0f0", "accent": "#3366ff"}

    def test_clean_accepts_hex_and_lowercases(self):
        self.assertEqual(theme_mod.clean_custom({**self.good, "accent": "#3366FF"})["accent"], "#3366ff")

    def test_clean_rejects_css_injection_and_bad_values(self):
        for bad in ("red", "#12345", "#1234567", "#101010;}body{display:none", "</style><script>", ""):
            with self.assertRaises(ValueError, msg=bad):
                theme_mod.clean_custom({**self.good, "bg": bad})

    def test_clean_rejects_unreadable_contrast(self):
        with self.assertRaises(ValueError):
            theme_mod.clean_custom({**self.good, "text": "#141414"})

    def test_build_derives_muted_and_border(self):
        t = theme_mod.build_custom(self.good)
        self.assertEqual(set(t), {"bg", "card", "text", "accent", "muted", "border"})
        self.assertTrue(all(theme_mod.HEX_RE.match(v) for v in t.values()))

    def test_build_falls_back_on_corrupt_data(self):
        self.assertEqual(theme_mod.build_custom({"bg": "nope"})["bg"], theme_mod.CUSTOM_DEFAULT["bg"])


@override_settings(STORAGES={"staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class CustomThemeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("th", password="x")
        self.client.force_login(self.user)

    def test_save_custom_theme_applies_to_pages(self):
        r = self.client.post(reverse("theme_settings"), {"theme": "custom", **CustomThemeTests.good})
        self.assertRedirects(r, reverse("theme_settings"))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, "custom")
        page = self.client.get(reverse("dashboard")).content.decode()
        self.assertIn("--accent: #3366ff", page)

    def test_rejected_custom_theme_is_not_saved(self):
        r = self.client.post(reverse("theme_settings"), {"theme": "custom", **CustomThemeTests.good,
                                                         "bg": "#000;}body{display:none"})
        self.assertEqual(r.status_code, 400)
        self.user.profile.refresh_from_db()
        self.assertNotEqual(self.user.profile.theme, "custom")
        self.assertNotIn("display:none", r.content.decode().split("</style>")[0])

    def test_preset_still_works(self):
        self.client.post(reverse("theme_settings"), {"theme": "pink_white_red"})
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.theme, "pink_white_red")
        self.assertContains(self.client.get(reverse("theme_settings")), 'data-panel="custom"')
