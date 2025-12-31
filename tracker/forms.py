from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from .models import Workout, Exercise, LiftEntry

# -------------------------
# SIGN UP FORM (KEEP THIS)
# -------------------------
class SignUpForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ["username", "email"]

    def clean_password1(self):
        pw = self.cleaned_data.get("password1")
        validate_password(pw)
        return pw

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords do not match.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


# -------------------------
# NEW WORKOUT FORM
# -------------------------
class WorkoutForm(forms.ModelForm):
    class Meta:
        model = Workout
        fields = ["name"]


# -------------------------
# NEW LIFT ENTRY FORM
# -------------------------
class LiftEntryForm(forms.Form):
    workout_id = forms.IntegerField(widget=forms.HiddenInput)
    exercise_name = forms.CharField(max_length=80)
    weight = forms.DecimalField(max_digits=6, decimal_places=2)
    reps = forms.IntegerField(min_value=1)
    sets = forms.IntegerField(min_value=1, initial=3)
