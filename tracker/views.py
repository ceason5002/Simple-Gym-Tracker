from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Workout, Exercise, LiftEntry
from .forms import WorkoutForm, LiftEntryForm

@login_required
def dashboard(request):
    workouts = Workout.objects.filter(user=request.user).order_by("name")
    recent = LiftEntry.objects.filter(user=request.user)[:10]
    return render(request, "dashboard.html", {"workouts": workouts, "recent": recent})

@login_required
def create_workout(request):
    if request.method == "POST":
        form = WorkoutForm(request.POST)
        if form.is_valid():
            w = form.save(commit=False)
            w.user = request.user
            try:
                w.save()
                return redirect("dashboard")
            except:
                messages.error(request, "Workout name already exists.")
    else:
        form = WorkoutForm()
    return render(request, "create_workout.html", {"form": form})

@login_required
def workout_detail(request, workout_id):
    workout = get_object_or_404(Workout, id=workout_id, user=request.user)
    entries = LiftEntry.objects.filter(user=request.user, workout=workout)[:50]
    form = LiftEntryForm(initial={"workout_id": workout.id})
    return render(request, "workout_detail.html", {"workout": workout, "entries": entries, "form": form})

@login_required
def add_entry(request):
    if request.method != "POST":
        return redirect("dashboard")

    form = LiftEntryForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Invalid entry.")
        return redirect("dashboard")

    workout = get_object_or_404(Workout, id=form.cleaned_data["workout_id"], user=request.user)

    ex_name = form.cleaned_data["exercise_name"].strip()
    exercise, _ = Exercise.objects.get_or_create(user=request.user, name=ex_name)

    LiftEntry.objects.create(
        user=request.user,
        workout=workout,
        exercise=exercise,
        weight=form.cleaned_data["weight"],
        reps=form.cleaned_data["reps"],
        sets=form.cleaned_data["sets"],
    )

    return redirect("workout_detail", workout_id=workout.id)
