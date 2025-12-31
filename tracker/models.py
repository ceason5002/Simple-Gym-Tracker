from django.db import models
from django.contrib.auth.models import User

#lift model created 
class Lift(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="lifts")
    name = models.CharField(max_length=80)
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    reps = models.PositiveIntegerField()
    sets = models.PositiveIntegerField(default=3)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "name")

    def __str__(self):
        return f"{self.user.username} - {self.name}"
