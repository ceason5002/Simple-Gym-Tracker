"""Research behind the suggestions.

Each study entry was checked against its abstract or PubMed record. Wording stays close to what the
study measured (mostly small trials in untrained people), so the app never overstates a finding.
"""

STUDIES = {
    "volume": {
        "cite": "Schoenfeld, Ogborn & Krieger, 2017 · Journal of Sports Sciences",
        "kind": "Meta-analysis of 15 studies",
        "finding": "More weekly sets per muscle produced more muscle growth in a graded, dose-response way. "
                   "Groups doing roughly 10 or more sets per muscle per week tended to grow the most.",
        "url": "https://core.ac.uk/download/200371264.pdf",
    },
    "frequency": {
        "cite": "Schoenfeld, Ogborn & Krieger, 2016 · Sports Medicine",
        "kind": "Meta-analysis of 10 studies",
        "finding": "Training each muscle at least twice a week produced more growth than once a week "
                   "(effect size 0.49 vs 0.30). Higher-frequency groups often also did more total sets.",
        "url": "https://doi.org/10.1007/s40279-016-0543-8",
    },
    "incline_press": {
        "cite": "J Electromyogr Kinesiol, 2022",
        "kind": "Training study, 13 men, ultrasound",
        "finding": "The 45° incline bench press grew the upper (clavicular) chest more, while the flat bench press "
                   "grew the mid and lower (sternocostal) chest more.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/36334406/",
    },
    "pushup": {
        "cite": "Kikuchi & Nakazato, 2017 · J Exerc Sci Fit",
        "kind": "8-week trial, 18 untrained men",
        "finding": "Push-ups and bench press at a similar load grew chest and triceps thickness similarly.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/29541130/",
    },
    "overhead_triceps": {
        "cite": "Maeo et al., 2023 · Eur J Sport Sci",
        "kind": "12-week trial, 21 adults, MRI",
        "finding": "Triceps extensions with the arm overhead grew the whole triceps about 1.4x more than the same "
                   "exercise with the arm at the side (+19.9% vs +13.9%), mostly from the long head.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/35819335/",
    },
    "seated_leg_curl": {
        "cite": "Maeo et al., 2021 · Med Sci Sports Exerc",
        "kind": "12-week trial, 20 adults, MRI",
        "finding": "Seated leg curls (hips bent) grew the hamstrings more than lying leg curls: about +14% vs +9% "
                   "in whole-hamstring volume.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/33009197/",
    },
    "hip_thrust_squat": {
        "cite": "Plotkin et al., 2023 · Frontiers in Physiology",
        "kind": "9-week trial, 34 untrained adults, MRI",
        "finding": "Hip thrusts and back squats grew the glutes similarly. Squats also grew the quads more.",
        "url": "https://pubmed.ncbi.nlm.nih.gov/37877099/",
    },
    "long_length_quads": {
        "cite": "Pedrosa et al., 2022 · Eur J Sport Sci",
        "kind": "Leg extension trial in untrained women",
        "finding": "Leg extensions focused on the knee-bent (stretched) half of the movement produced favourable quad "
                   "growth, especially near the knee.",
        "url": "https://examine.com/research-feed/study/1Y43rd/",
    },
}

# exercise id -> (study key, how it applies to this exercise)
EXERCISE_EVIDENCE = {
    "incline_bench": ("incline_press", "Best pick here for the upper chest."),
    "incline_db_press": ("incline_press", "Incline pressing targets the upper chest."),
    "bench_press": ("incline_press", "Flat pressing targets the mid and lower chest. Pair with an incline press."),
    "db_bench": ("incline_press", "Flat pressing targets the mid and lower chest. Pair with an incline press."),
    "pushup": ("pushup", "A solid bench press alternative when you have no equipment."),
    "overhead_ext": ("overhead_triceps", "Arm overhead stretches the long head, which grew more."),
    "tricep_pushdown": ("overhead_triceps", "Pushdowns work, but add an overhead extension for more growth."),
    "skull_crusher": ("overhead_triceps", "Letting the bar travel behind your head adds more stretch."),
    "leg_curl": ("seated_leg_curl", "Choose the seated machine over the lying one if your gym has both."),
    "hip_thrust": ("hip_thrust_squat", "Equal to squats for glute growth, with less load on the knees and back."),
    "squat": ("hip_thrust_squat", "Grows glutes as well as hip thrusts do, and your quads too."),
    "leg_extension": ("long_length_quads", "Control the bottom half of each rep, where the quads are stretched."),
}

WEEKLY_SET_TARGET = 10      # from the volume meta-analysis above
WEEKLY_FREQ_TARGET = 2      # from the frequency meta-analysis above


def for_exercise(ex_id):
    pair = EXERCISE_EVIDENCE.get(ex_id)
    if not pair:
        return None
    key, how = pair
    return {**STUDIES[key], "key": key, "how": how}
