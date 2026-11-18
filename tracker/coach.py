"""Workout suggestions from a user's own lift history, plus YouTube "watch how" videos.

Everything here works on plain data so it can be unit-tested without the web layer.
"""
import datetime as dt
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote_plus

import httpx
from django.conf import settings
from django.utils import timezone

from .workout_library import EXERCISES, GROUPS, PROGRAMS, alternatives, match_exercise

log = logging.getLogger(__name__)

TOP_OF_RANGE_REPS = 8        # hitting this at the same weight twice = time to add load
STALL_SESSIONS = 3           # this many sessions with no progress = stalled
DELOAD = Decimal("0.9")


# ---------------------------------------------------------------------------
# Sessions: one top set per exercise per day
# ---------------------------------------------------------------------------

@dataclass
class Session:
    date: dt.date
    weight: Decimal
    reps: int
    sets: int


@dataclass
class ExerciseHistory:
    name: str                       # as the user typed it (most recent spelling)
    library_id: str | None
    sessions: list = field(default_factory=list)   # newest first

    @property
    def last(self):
        return self.sessions[0] if self.sessions else None


def build_history(entries):
    """entries: iterable of objects with .exercise.name, .weight, .reps, .sets, .logged_at (any order)."""
    by_ex = {}
    tops = defaultdict(dict)   # key -> {date: Session}
    for e in entries:
        name = e.exercise.name.strip()
        key = match_exercise(name) or "custom:" + name.lower()
        by_ex.setdefault(key, ExerciseHistory(name=name, library_id=None if key.startswith("custom:") else key))
        day = timezone.localtime(e.logged_at).date() if timezone.is_aware(e.logged_at) else e.logged_at.date()
        cur = tops[key].get(day)
        cand = Session(day, Decimal(e.weight), int(e.reps), int(e.sets))
        if cur is None or (cand.weight, cand.reps) > (cur.weight, cur.reps):
            tops[key][day] = cand
    for key, hist in by_ex.items():
        hist.sessions = sorted(tops[key].values(), key=lambda s: s.date, reverse=True)
    return by_ex


# ---------------------------------------------------------------------------
# Progression tips
# ---------------------------------------------------------------------------

def increment_for(library_id):
    lower = bool(library_id and EXERCISES.get(library_id, {}).get("lower"))
    return Decimal("10") if lower else Decimal("5")


def _round_plate(w: Decimal) -> Decimal:
    """Round to the nearest 2.5 lb (what you can actually load)."""
    return (w / Decimal("2.5")).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * Decimal("2.5")


def tip_for(hist: ExerciseHistory):
    """Return {kind, title, detail, next_weight} or None. kinds: add, stalled, up, keep."""
    s = hist.sessions
    if not s:
        return None
    last = s[0]
    inc = increment_for(hist.library_id)

    # Stalled: the newest session is no better than the oldest of the last few (same weight, no extra reps)
    if len(s) >= STALL_SESSIONS:
        oldest = s[STALL_SESSIONS - 1]
        if (last.weight, last.reps) <= (oldest.weight, oldest.reps):
            deload = _round_plate(last.weight * DELOAD)
            alts = alternatives(hist.library_id) if hist.library_id else []
            swap = f", or swap in {EXERCISES[alts[0]]['name']} for a few weeks" if alts else ""
            return {"kind": "stalled", "title": f"{hist.name} has stalled",
                    "detail": f"No progress in your last {STALL_SESSIONS} sessions. Try a lighter week at "
                              f"{deload:g} lb{swap}.",
                    "next_weight": deload}

    if len(s) >= 2:
        prev = s[1]
        if last.weight == prev.weight and last.reps >= TOP_OF_RANGE_REPS and prev.reps >= TOP_OF_RANGE_REPS:
            nxt = last.weight + inc
            return {"kind": "add", "title": f"Add {inc:g} lb to {hist.name}",
                    "detail": f"You hit {last.reps} reps at {last.weight:g} lb twice in a row. Go for {nxt:g} lb next time.",
                    "next_weight": nxt}
        if last.weight > prev.weight:
            return {"kind": "up", "title": f"{hist.name} is moving",
                    "detail": f"Up {last.weight - prev.weight:g} lb since your previous session. Stay at {last.weight:g} lb "
                              f"until you can do {TOP_OF_RANGE_REPS} reps.",
                    "next_weight": last.weight}
    return {"kind": "keep", "title": f"Keep building {hist.name}",
            "detail": f"Last time: {last.weight:g} lb x {last.reps}. Try for one more rep at the same weight.",
            "next_weight": last.weight}


def suggested_weight(hist: ExerciseHistory | None):
    if not hist or not hist.last:
        return None
    t = tip_for(hist)
    return t["next_weight"] if t else hist.last.weight


# ---------------------------------------------------------------------------
# What to train next
# ---------------------------------------------------------------------------

def muscle_recency(histories, today):
    """Days since each muscle group was last trained (None = not in your log yet)."""
    last = {}
    for h in histories.values():
        if not h.library_id or not h.last:
            continue
        ex = EXERCISES[h.library_id]
        for g in [ex["primary"], *ex["secondary"]]:
            if g not in last or h.last.date > last[g]:
                last[g] = h.last.date
    return {g: ((today - last[g]).days if g in last else None) for g in GROUPS}


def next_day(program_id, histories, today):
    """Pick the program day whose focus muscles are the most rested. Returns (day, reason)."""
    prog = PROGRAMS.get(program_id) or PROGRAMS["ppl"]
    rec = muscle_recency(histories, today)

    def score(day):
        # Rank by the day's main muscle (first in focus); never-trained counts as most rested.
        # Ties are broken by the average rest of the other focus muscles.
        main = rec[day["focus"][0]]
        others = [rec[g] for g in day["focus"][1:] if rec[g] is not None]
        return (1000 if main is None else main, sum(others) / len(others) if others else 0)

    ranked = sorted(prog["days"], key=score, reverse=True)
    day = ranked[0]
    main_g = day["focus"][0]
    main_name = GROUPS[main_g].lower()
    if not any(v is not None for v in rec.values()):
        reason = "Start here. Once you log a few sessions, suggestions follow what you've trained."
    elif rec[main_g] is None:
        reason = f"You haven't logged any {main_name} work yet."
    else:
        n = rec[main_g]
        when = "today" if n == 0 else "yesterday" if n == 1 else f"{n} days ago"
        reason = f"You last trained {main_name} {when}, longer ago than any other day in this program."
    return day, reason


def weekly_volume(entries, today):
    """Hard sets and training days per muscle group over the last 7 days.

    A set counts fully for the exercise's primary muscle and half for each secondary muscle,
    a common convention in the volume research."""
    since = today - dt.timedelta(days=6)
    sets = {g: 0.0 for g in GROUPS}
    days = {g: set() for g in GROUPS}
    for e in entries:
        day = timezone.localtime(e.logged_at).date() if timezone.is_aware(e.logged_at) else e.logged_at.date()
        if day < since:
            continue
        ex_id = match_exercise(e.exercise.name)
        if not ex_id:
            continue
        ex = EXERCISES[ex_id]
        sets[ex["primary"]] += e.sets
        days[ex["primary"]].add(day)
        for g in ex["secondary"]:
            sets[g] += e.sets * 0.5
            days[g].add(day)
    return {g: {"label": GROUPS[g], "sets": round(sets[g], 1), "days": len(days[g])} for g in GROUPS}


def plan_for_day(day, histories):
    """Exercises for a program day with suggested weights from history."""
    rows = []
    for i, (ex_id, sets, reps) in enumerate(day["exercises"]):
        hist = histories.get(ex_id)
        w = suggested_weight(hist)
        t = tip_for(hist) if hist else None
        rows.append({
            "order": i, "library_id": ex_id, "name": EXERCISES[ex_id]["name"], "sets": sets, "reps": reps,
            "equipment": EXERCISES[ex_id]["equipment"], "primary": GROUPS[EXERCISES[ex_id]["primary"]],
            "suggested_weight": w,
            "note": (t["title"] if t and t["kind"] in ("add", "stalled") else
                     f"Last: {hist.last.weight:g} lb x {hist.last.reps}" if hist and hist.last else "New for you"),
        })
    return rows


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------

YT_SEARCH = "https://www.googleapis.com/youtube/v3/search"
CACHE_DAYS = 30


def youtube_search_url(query):
    return "https://www.youtube.com/results?search_query=" + quote_plus(query)


def video_query(exercise_name):
    return f"{exercise_name} proper form tutorial"


def fetch_videos(query, cache_model):
    """Return (videos, fallback_url). Uses the cache; calls the API only with a key and a stale/missing cache."""
    fallback = youtube_search_url(query)
    key = getattr(settings, "YOUTUBE_API_KEY", "")
    cached = cache_model.objects.filter(query=query).first()
    fresh = cached and cached.fetched_at > timezone.now() - dt.timedelta(days=CACHE_DAYS)
    if fresh or not key:
        return (cached.results if cached else []), fallback
    try:
        with httpx.Client(timeout=httpx.Timeout(8.0, connect=4.0)) as c:
            r = c.get(YT_SEARCH, params={
                "part": "snippet", "q": query, "type": "video", "maxResults": 4,
                "videoEmbeddable": "true", "safeSearch": "strict", "relevanceLanguage": "en", "key": key,
            })
        r.raise_for_status()
        videos = [{
            "id": it["id"]["videoId"],
            "title": it["snippet"]["title"],
            "channel": it["snippet"]["channelTitle"],
            "thumb": (it["snippet"]["thumbnails"].get("medium") or it["snippet"]["thumbnails"]["default"])["url"],
        } for it in r.json().get("items", []) if it.get("id", {}).get("videoId")]
    except (httpx.HTTPError, KeyError, ValueError) as e:
        log.warning("YouTube search failed: %s", e)
        return (cached.results if cached else []), fallback
    cache_model.objects.update_or_create(query=query, defaults={"results": videos})
    return videos, fallback
