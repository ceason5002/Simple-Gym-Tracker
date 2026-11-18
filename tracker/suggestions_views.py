from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST

from . import coach, evidence
from .models import LiftEntry, PlannedExercise, VideoCache, Workout
from .workout_library import EXERCISES, GROUPS, PROGRAMS, get_day


def _histories(user):
    entries = list(LiftEntry.objects.filter(user=user).select_related("exercise"))
    return entries, coach.build_history(entries)


def _with_evidence(rows):
    for r in rows:
        r["evidence"] = evidence.for_exercise(r["library_id"])
    return rows


@login_required
def suggestions(request):
    profile = request.user.profile
    program_id = profile.active_program if profile.active_program in PROGRAMS else "ppl"
    today = timezone.localdate()
    entries, histories = _histories(request.user)

    day, reason = coach.next_day(program_id, histories, today)
    up_next = _with_evidence(coach.plan_for_day(day, histories))

    tips = [t for t in (coach.tip_for(h) for h in histories.values()) if t]
    order = {"stalled": 0, "add": 1, "up": 2, "keep": 3}
    tips.sort(key=lambda t: order[t["kind"]])

    volume = coach.weekly_volume(entries, today)
    for v in volume.values():
        v["pct"] = min(100, round(v["sets"] / evidence.WEEKLY_SET_TARGET * 100))
        v["met"] = v["sets"] >= evidence.WEEKLY_SET_TARGET
        v["freq_met"] = v["days"] >= evidence.WEEKLY_FREQ_TARGET
    trained = [v for v in volume.values() if v["sets"]]

    programs = []
    for pid, p in PROGRAMS.items():
        programs.append({
            "id": pid, **{k: p[k] for k in ("name", "blurb", "level", "days_per_week")},
            "active": pid == program_id,
            "days": [{"id": d["id"], "name": d["name"], "focus": [GROUPS[g] for g in d["focus"]],
                      "exercises": _with_evidence(coach.plan_for_day(d, histories))} for d in p["days"]],
        })

    return render(request, "suggestions.html", {
        "program": PROGRAMS[program_id], "program_id": program_id,
        "up_next": {"day": day, "reason": reason, "rows": up_next, "focus": [GROUPS[g] for g in day["focus"]]},
        "tips": tips[:6],
        "volume": volume, "has_volume": bool(trained),
        "set_target": evidence.WEEKLY_SET_TARGET, "freq_target": evidence.WEEKLY_FREQ_TARGET,
        "volume_study": evidence.STUDIES["volume"], "freq_study": evidence.STUDIES["frequency"],
        "programs": programs,
        "has_history": bool(entries),
    })


@login_required
@require_POST
def follow_program(request):
    pid = request.POST.get("program")
    if pid in PROGRAMS:
        request.user.profile.active_program = pid
        request.user.profile.save(update_fields=["active_program"])
        messages.success(request, f"Now following {PROGRAMS[pid]['name']}.")
    return redirect("suggestions")


@login_required
@require_POST
def start_workout(request):
    prog, day = get_day(request.POST.get("program", ""), request.POST.get("day", ""))
    if not day:
        messages.error(request, "That workout doesn't exist.")
        return redirect("suggestions")
    _, histories = _histories(request.user)
    rows = coach.plan_for_day(day, histories)

    base = f"{day['name']} · {timezone.localdate():%b %-d}"
    name, n = base, 2
    with transaction.atomic():
        while Workout.objects.filter(user=request.user, name=name).exists():
            name, n = f"{base} ({n})", n + 1
        try:
            workout = Workout.objects.create(user=request.user, name=name[:80])
        except IntegrityError:
            messages.error(request, "Couldn't create that workout. Try again.")
            return redirect("suggestions")
        PlannedExercise.objects.bulk_create([PlannedExercise(
            workout=workout, library_id=r["library_id"], name=r["name"], sets=r["sets"], reps=r["reps"],
            suggested_weight=r["suggested_weight"], note=r["note"][:140], order=r["order"],
        ) for r in rows])
    messages.success(request, f"{day['name']} is ready. Tap an exercise to log it.")
    return redirect("workout_detail", workout_id=workout.id)


@login_required
@require_GET
def api_videos(request):
    ex_id = request.GET.get("ex", "")
    name = EXERCISES[ex_id]["name"] if ex_id in EXERCISES else (request.GET.get("name") or "").strip()[:80]
    if not name:
        return JsonResponse({"error": "Which exercise?"}, status=400)
    videos, fallback = coach.fetch_videos(coach.video_query(name), VideoCache)
    return JsonResponse({"exercise": name, "videos": videos, "search_url": fallback})
