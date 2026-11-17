from django.db import models
from django.contrib.auth.models import User

class Workout(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="workouts")
    name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.user.username} - {self.name}"

class Exercise(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="exercises")
    name = models.CharField(max_length=80)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.user.username} - {self.name}"

class LiftEntry(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lift_entries")
    workout = models.ForeignKey(Workout, on_delete=models.CASCADE, related_name="entries")
    exercise = models.ForeignKey(Exercise, on_delete=models.CASCADE, related_name="entries")
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    reps = models.PositiveIntegerField()
    sets = models.PositiveIntegerField(default=3)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-logged_at"]

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    theme = models.CharField(max_length=30, default="dark_gray")

    def __str__(self):
        return self.user.username

# ---------------------------------------------------------------------------
# NutrientAI
# ---------------------------------------------------------------------------

class NutritionProfile(models.Model):
    SEX_CHOICES = [("male", "Male"), ("female", "Female")]
    ACTIVITY_CHOICES = [
        ("sedentary", "Sedentary (little exercise)"),
        ("light", "Light (1-3 days/week)"),
        ("moderate", "Moderate (3-5 days/week)"),
        ("active", "Active (6-7 days/week)"),
        ("very_active", "Very active (hard training or physical job)"),
    ]
    GOAL_CHOICES = [("lose", "Lose weight"), ("maintain", "Maintain weight"), ("gain", "Gain weight")]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="nutrition")
    sex = models.CharField(max_length=6, choices=SEX_CHOICES, blank=True)
    age = models.PositiveSmallIntegerField(null=True, blank=True)
    height_in = models.DecimalField("Height (inches)", max_digits=5, decimal_places=1, null=True, blank=True)
    weight_lb = models.DecimalField("Weight (lb)", max_digits=5, decimal_places=1, null=True, blank=True)
    activity = models.CharField(max_length=12, choices=ACTIVITY_CHOICES, default="moderate")
    goal = models.CharField(max_length=8, choices=GOAL_CHOICES, default="maintain")

    # Optional manual overrides; blank means "use the calculated value"
    calorie_override = models.PositiveIntegerField(null=True, blank=True)
    protein_override = models.PositiveIntegerField(null=True, blank=True)
    carbs_override = models.PositiveIntegerField(null=True, blank=True)
    fat_override = models.PositiveIntegerField(null=True, blank=True)
    water_override_oz = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} nutrition"


class SavedFood(models.Model):
    SOURCE_CHOICES = [("usda", "USDA"), ("off", "Open Food Facts"), ("manual", "Manual")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="saved_foods")
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=120, blank=True)
    barcode = models.CharField(max_length=32, blank=True)
    serving_desc = models.CharField(max_length=80, default="1 serving")
    calories = models.DecimalField(max_digits=7, decimal_places=1)
    protein = models.DecimalField(max_digits=6, decimal_places=1)
    carbs = models.DecimalField(max_digits=6, decimal_places=1)
    fat = models.DecimalField(max_digits=6, decimal_places=1)
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES, default="manual")
    source_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.user.username} - {self.name}"


class FoodLogEntry(models.Model):
    """A logged food. Macros are copied in (per serving) so later edits to a saved food don't rewrite history."""
    MEAL_CHOICES = [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner"), ("snack", "Snacks")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="food_log")
    date = models.DateField(db_index=True)
    meal = models.CharField(max_length=10, choices=MEAL_CHOICES, default="snack")
    name = models.CharField(max_length=120)
    brand = models.CharField(max_length=120, blank=True)
    serving_desc = models.CharField(max_length=80, default="1 serving")
    servings = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    calories = models.DecimalField(max_digits=7, decimal_places=1)
    protein = models.DecimalField(max_digits=6, decimal_places=1)
    carbs = models.DecimalField(max_digits=6, decimal_places=1)
    fat = models.DecimalField(max_digits=6, decimal_places=1)
    source = models.CharField(max_length=8, default="manual")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class WaterLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="water_log")
    date = models.DateField(db_index=True)
    amount_oz = models.DecimalField(max_digits=5, decimal_places=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
