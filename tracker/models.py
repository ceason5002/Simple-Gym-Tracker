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