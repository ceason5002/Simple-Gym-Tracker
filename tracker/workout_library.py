"""Curated exercise library and well-known training programs.

Exercises: id -> {name, primary, secondary, equipment, aliases, lower}
  primary/secondary are muscle groups from GROUPS; `lower` marks lower-body lifts (bigger weight jumps).
Programs: id -> {name, blurb, level, days_per_week, days: [{id, name, focus, exercises: [(exercise_id, sets, reps)]}]}
"""

GROUPS = {
    "chest": "Chest", "back": "Back", "shoulders": "Shoulders", "biceps": "Biceps", "triceps": "Triceps",
    "quads": "Quads", "hamstrings": "Hamstrings", "glutes": "Glutes", "calves": "Calves", "core": "Core",
}


def _ex(name, primary, secondary=(), equipment="barbell", aliases=(), lower=False):
    return {"name": name, "primary": primary, "secondary": list(secondary), "equipment": equipment,
            "aliases": list(aliases), "lower": lower}


EXERCISES = {
    # Chest
    "bench_press": _ex("Barbell Bench Press", "chest", ("triceps", "shoulders"), aliases=("bench", "bench press", "flat bench", "bb bench")),
    "incline_bench": _ex("Incline Barbell Bench Press", "chest", ("shoulders", "triceps"), aliases=("incline bench", "incline press")),
    "db_bench": _ex("Dumbbell Bench Press", "chest", ("triceps", "shoulders"), "dumbbell", ("db bench", "dumbbell press")),
    "incline_db_press": _ex("Incline Dumbbell Press", "chest", ("shoulders", "triceps"), "dumbbell", ("incline db press", "incline dumbbell bench")),
    "cable_fly": _ex("Cable Fly", "chest", (), "cable", ("chest fly", "pec fly", "cable crossover", "flyes", "fly")),
    "pushup": _ex("Push-Up", "chest", ("triceps", "shoulders", "core"), "bodyweight", ("pushup", "push ups", "press up")),
    "dips": _ex("Dips", "chest", ("triceps", "shoulders"), "bodyweight", ("chest dips", "parallel bar dips")),
    # Back
    "deadlift": _ex("Deadlift", "back", ("hamstrings", "glutes", "core"), aliases=("conventional deadlift", "dl"), lower=True),
    "pullup": _ex("Pull-Up", "back", ("biceps",), "bodyweight", ("pull up", "pullups", "weighted pull up")),
    "chinup": _ex("Chin-Up", "back", ("biceps",), "bodyweight", ("chin up", "chinups")),
    "lat_pulldown": _ex("Lat Pulldown", "back", ("biceps",), "cable", ("pulldown", "lat pull down", "pull down")),
    "barbell_row": _ex("Barbell Row", "back", ("biceps",), aliases=("bent over row", "bb row", "pendlay row", "row")),
    "db_row": _ex("One-Arm Dumbbell Row", "back", ("biceps",), "dumbbell", ("dumbbell row", "db row", "single arm row")),
    "seated_row": _ex("Seated Cable Row", "back", ("biceps",), "cable", ("cable row", "seated row")),
    "face_pull": _ex("Face Pull", "shoulders", ("back",), "cable", ("face pulls",)),
    # Shoulders
    "ohp": _ex("Overhead Press", "shoulders", ("triceps",), aliases=("ohp", "military press", "shoulder press", "standing press")),
    "db_shoulder_press": _ex("Seated Dumbbell Shoulder Press", "shoulders", ("triceps",), "dumbbell", ("db shoulder press", "dumbbell shoulder press", "arnold press")),
    "lateral_raise": _ex("Lateral Raise", "shoulders", (), "dumbbell", ("side raise", "lateral raises", "side lateral raise")),
    "rear_delt_fly": _ex("Rear Delt Fly", "shoulders", ("back",), "dumbbell", ("reverse fly", "rear delt raise")),
    # Arms
    "barbell_curl": _ex("Barbell Curl", "biceps", (), aliases=("bb curl", "curl", "ez bar curl")),
    "db_curl": _ex("Dumbbell Curl", "biceps", (), "dumbbell", ("db curl", "bicep curl", "biceps curl")),
    "hammer_curl": _ex("Hammer Curl", "biceps", (), "dumbbell", ("hammer curls",)),
    "tricep_pushdown": _ex("Triceps Pushdown", "triceps", (), "cable", ("tricep pushdown", "rope pushdown", "pushdown", "cable pushdown")),
    "skull_crusher": _ex("Skull Crusher", "triceps", (), aliases=("skullcrusher", "lying triceps extension", "ez bar skull crusher")),
    "overhead_ext": _ex("Overhead Triceps Extension", "triceps", (), "dumbbell", ("overhead tricep extension", "overhead extension")),
    "close_grip_bench": _ex("Close-Grip Bench Press", "triceps", ("chest",), aliases=("close grip bench", "cgbp")),
    # Legs
    "squat": _ex("Back Squat", "quads", ("glutes", "hamstrings", "core"), aliases=("squat", "squats", "barbell squat", "high bar squat", "low bar squat"), lower=True),
    "front_squat": _ex("Front Squat", "quads", ("glutes", "core"), aliases=("front squats",), lower=True),
    "leg_press": _ex("Leg Press", "quads", ("glutes",), "machine", ("leg press machine",), lower=True),
    "split_squat": _ex("Bulgarian Split Squat", "quads", ("glutes",), "dumbbell", ("split squat", "bss", "rear foot elevated split squat"), lower=True),
    "lunge": _ex("Walking Lunge", "quads", ("glutes",), "dumbbell", ("lunge", "lunges", "walking lunges"), lower=True),
    "leg_extension": _ex("Leg Extension", "quads", (), "machine", ("leg extensions", "quad extension")),
    "rdl": _ex("Romanian Deadlift", "hamstrings", ("glutes", "back"), aliases=("rdl", "romanian dl", "stiff leg deadlift"), lower=True),
    "leg_curl": _ex("Leg Curl", "hamstrings", (), "machine", ("hamstring curl", "lying leg curl", "seated leg curl")),
    "hip_thrust": _ex("Hip Thrust", "glutes", ("hamstrings",), aliases=("barbell hip thrust", "glute bridge"), lower=True),
    "calf_raise": _ex("Standing Calf Raise", "calves", (), "machine", ("calf raise", "calf raises", "calves")),
    # Core
    "plank": _ex("Plank", "core", (), "bodyweight", ("planks",)),
    "hanging_leg_raise": _ex("Hanging Leg Raise", "core", (), "bodyweight", ("leg raise", "hanging knee raise")),
    "cable_crunch": _ex("Cable Crunch", "core", (), "cable", ("crunch", "kneeling cable crunch")),
}

PROGRAMS = {
    "ppl": {
        "name": "Push / Pull / Legs",
        "blurb": "Train each movement pattern on its own day. Run it 3 days a week, or twice through for 6.",
        "level": "Intermediate", "days_per_week": "3-6",
        "days": [
            {"id": "push", "name": "Push", "focus": ["chest", "shoulders", "triceps"], "exercises": [
                ("bench_press", 4, "6-8"), ("ohp", 3, "8-10"), ("incline_db_press", 3, "8-12"),
                ("lateral_raise", 3, "12-15"), ("tricep_pushdown", 3, "10-12"), ("overhead_ext", 2, "12-15")]},
            {"id": "pull", "name": "Pull", "focus": ["back", "biceps"], "exercises": [
                ("deadlift", 3, "5"), ("pullup", 4, "6-10"), ("barbell_row", 3, "8-10"),
                ("face_pull", 3, "15"), ("barbell_curl", 3, "8-12"), ("hammer_curl", 2, "10-12")]},
            {"id": "legs", "name": "Legs", "focus": ["quads", "hamstrings", "glutes", "calves"], "exercises": [
                ("squat", 4, "5-8"), ("rdl", 3, "8-10"), ("leg_press", 3, "10-12"),
                ("leg_curl", 3, "10-12"), ("calf_raise", 4, "12-15"), ("hanging_leg_raise", 3, "10-15")]},
        ],
    },
    "upper_lower": {
        "name": "Upper / Lower",
        "blurb": "Four days a week: two upper-body days and two lower-body days, each muscle twice a week.",
        "level": "Beginner to intermediate", "days_per_week": "4",
        "days": [
            {"id": "upper_a", "name": "Upper A", "focus": ["chest", "back", "shoulders", "biceps", "triceps"], "exercises": [
                ("bench_press", 4, "5-8"), ("barbell_row", 4, "6-10"), ("db_shoulder_press", 3, "8-12"),
                ("lat_pulldown", 3, "10-12"), ("barbell_curl", 2, "10-12"), ("tricep_pushdown", 2, "10-12")]},
            {"id": "lower_a", "name": "Lower A", "focus": ["quads", "hamstrings", "glutes", "calves", "core"], "exercises": [
                ("squat", 4, "5-8"), ("rdl", 3, "8-10"), ("split_squat", 3, "10"), ("calf_raise", 4, "12-15"), ("plank", 3, "45s")]},
            {"id": "upper_b", "name": "Upper B", "focus": ["chest", "back", "shoulders", "biceps", "triceps"], "exercises": [
                ("ohp", 4, "5-8"), ("pullup", 4, "6-10"), ("incline_db_press", 3, "8-12"),
                ("seated_row", 3, "10-12"), ("lateral_raise", 3, "12-15"), ("hammer_curl", 2, "10-12")]},
            {"id": "lower_b", "name": "Lower B", "focus": ["hamstrings", "glutes", "quads", "calves", "core"], "exercises": [
                ("deadlift", 3, "5"), ("front_squat", 3, "6-8"), ("hip_thrust", 3, "8-12"),
                ("leg_curl", 3, "10-12"), ("hanging_leg_raise", 3, "10-15")]},
        ],
    },
    "full_body": {
        "name": "Full Body 3x",
        "blurb": "Three whole-body sessions a week, alternating A and B. Great when you can't train often.",
        "level": "Beginner", "days_per_week": "3",
        "days": [
            {"id": "full_a", "name": "Full Body A", "focus": ["quads", "chest", "back", "core"], "exercises": [
                ("squat", 3, "5-8"), ("bench_press", 3, "6-8"), ("barbell_row", 3, "8-10"),
                ("lateral_raise", 2, "12-15"), ("plank", 3, "45s")]},
            {"id": "full_b", "name": "Full Body B", "focus": ["hamstrings", "shoulders", "back", "glutes"], "exercises": [
                ("deadlift", 3, "5"), ("ohp", 3, "6-8"), ("lat_pulldown", 3, "10-12"),
                ("split_squat", 2, "10"), ("db_curl", 2, "10-12")]},
        ],
    },
    "five_by_five": {
        "name": "5x5 Strength",
        "blurb": "Classic linear strength: a few big lifts, five sets of five, add weight every session.",
        "level": "Beginner", "days_per_week": "3",
        "days": [
            {"id": "sf_a", "name": "5x5 Day A", "focus": ["quads", "chest", "back"], "exercises": [
                ("squat", 5, "5"), ("bench_press", 5, "5"), ("barbell_row", 5, "5")]},
            {"id": "sf_b", "name": "5x5 Day B", "focus": ["quads", "shoulders", "back", "hamstrings"], "exercises": [
                ("squat", 5, "5"), ("ohp", 5, "5"), ("deadlift", 1, "5")]},
        ],
    },
}


# ---------------------------------------------------------------------------

def norm(name: str) -> str:
    return "".join(ch for ch in (name or "").lower() if ch.isalnum())


_ALIAS_INDEX = {}
for _id, _e in EXERCISES.items():
    for _a in [_e["name"], *_e["aliases"]]:
        _ALIAS_INDEX.setdefault(norm(_a), _id)


def match_exercise(name: str):
    """Map a free-text exercise name a user logged to a library id (or None)."""
    n = norm(name)
    if not n:
        return None
    if n in _ALIAS_INDEX:
        return _ALIAS_INDEX[n]
    # longest alias contained in the logged name, e.g. "paused bench press" -> bench_press
    best = None
    for alias, ex_id in _ALIAS_INDEX.items():
        if len(alias) >= 4 and alias in n and (best is None or len(alias) > len(best[0])):
            best = (alias, ex_id)
    return best[1] if best else None


def alternatives(ex_id: str, limit: int = 2):
    """Other exercises with the same primary muscle, for swapping out a stalled lift."""
    primary = EXERCISES[ex_id]["primary"]
    return [k for k, e in EXERCISES.items() if k != ex_id and e["primary"] == primary][:limit]


def get_day(program_id: str, day_id: str):
    prog = PROGRAMS.get(program_id)
    if not prog:
        return None, None
    for d in prog["days"]:
        if d["id"] == day_id:
            return prog, d
    return prog, None
