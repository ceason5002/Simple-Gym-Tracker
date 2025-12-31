from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib import messages
from .forms import SignUpForm, LiftForm
from .models import Lift

from openai import OpenAI

#view created using openai api

def home(request):
    return render(request, "home.html")

def signup_view(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
    else:
        form = SignUpForm()
    return render(request, "signup.html", {"form": form})

def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "")
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("dashboard")
        messages.error(request, "Invalid username or password.")
    return render(request, "login.html")

def logout_view(request):
    logout(request)
    return redirect("home")

def _ai_progression_tip(lifts):
    if not settings.GROQ_API_KEY:
        return "Tip: Aim to add +5 lb next week if form stays solid, or add +1 rep per set."

    summary = []
    for l in lifts:
        summary.append(f"{l.name}: {l.weight} lb x {l.reps} reps x {l.sets} sets")

    prompt = (
        "You are a strength coach. Give ONE short progressive overload suggestion for next session.\n"
        "Rules: be safe, prioritize good form, suggest either +5 lb OR +1 rep OR +1 set.\n"
        "User's current lifts:\n"
        + "\n".join(summary)
        + "\nReturn 1-2 sentences max."
    )

    client = OpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )

    resp = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
        max_tokens=80,
    )
    return resp.choices[0].message.content.strip()

@login_required
def dashboard(request):
    lifts = Lift.objects.filter(user=request.user).order_by("name")
    tip = _ai_progression_tip(lifts)
    return render(request, "dashboard.html", {"lifts": lifts, "tip": tip})

@login_required
def add_lift(request):
    if request.method == "POST":
        form = LiftForm(request.POST)
        if form.is_valid():
            lift = form.save(commit=False)
            lift.user = request.user
            try:
                lift.save()
                return redirect("dashboard")
            except Exception:
                messages.error(request, "You already have a lift with that name. Try a different name.")
    else:
        form = LiftForm()
    return render(request, "add_lift.html", {"form": form})

@login_required
def delete_lift(request, lift_id):
    lift = get_object_or_404(Lift, id=lift_id, user=request.user)
    if request.method == "POST":
        lift.delete()
        return redirect("dashboard")
    return render(request, "delete_lift.html", {"lift": lift})
