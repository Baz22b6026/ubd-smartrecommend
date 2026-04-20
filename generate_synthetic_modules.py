import csv
import random
from pathlib import Path

random.seed(42)

OUTPUT_FILE = Path("synthetic_modules_1000.csv")

LEVELS = [1000, 2000, 3000, 4000]
MODULES_PER_LEVEL = 250

FACULTIES = [
    "School of Digital Science",
    "Faculty of Arts and Social Sciences",
    "Faculty of Science",
    "School of Business and Economics",
]

CATEGORY_OPTIONS = ["Academic", "Career", "Campus Service", "Student Activity"]

FACULTY_THEMES = {
    "School of Digital Science": {
        "prefixes": ["Cloud", "Data", "AI", "Programming", "Cybersecurity", "Systems", "Software", "Analytics"],
        "subjects": ["Computing", "Development", "Engineering", "Mining", "Infrastructure", "Architecture", "Design", "Applications"],
        "topics": [
            "cloud", "azure", "data science", "machine learning", "python",
            "programming", "software engineering", "analytics", "sql", "devops",
            "cybersecurity", "web development", "distributed systems"
        ]
    },
    "Faculty of Arts and Social Sciences": {
        "prefixes": ["Academic", "Critical", "Research", "Social", "Cultural", "Media", "Communication", "Writing"],
        "subjects": ["Studies", "Methods", "Writing", "Analysis", "Inquiry", "Perspectives", "Practice", "Projects"],
        "topics": [
            "writing", "research", "critical thinking", "literature",
            "communication", "media", "sociology", "history",
            "academic writing", "innovation", "policy", "culture"
        ]
    },
    "Faculty of Science": {
        "prefixes": ["Biology", "Chemistry", "Physics", "Environmental", "Laboratory", "Scientific", "Applied", "Quantitative"],
        "subjects": ["Methods", "Analysis", "Investigations", "Systems", "Research", "Applications", "Foundations", "Techniques"],
        "topics": [
            "biology", "chemistry", "physics", "lab work",
            "research", "statistics", "scientific methods",
            "environment", "experimentation", "data analysis"
        ]
    },
    "School of Business and Economics": {
        "prefixes": ["Business", "Finance", "Marketing", "Management", "Innovation", "Entrepreneurship", "Economic", "Strategic"],
        "subjects": ["Analysis", "Practice", "Decision Making", "Planning", "Development", "Systems", "Applications", "Leadership"],
        "topics": [
            "business", "finance", "marketing", "economics",
            "leadership", "management", "entrepreneurship",
            "innovation", "strategy", "analytics"
        ]
    }
}

LEVEL_LABELS = {
    1000: "Undergraduate",
    2000: "Undergraduate",
    3000: "Senior Students",
    4000: "Final Year Students",
}

LEVEL_TOPIC_BIAS = {
    1000: ["foundations", "introductory", "fundamentals", "basics"],
    2000: ["intermediate", "applications", "practice", "methods"],
    3000: ["advanced", "project", "professional", "industry"],
    4000: ["capstone", "research", "specialised", "final year"],
}

CAREER_TITLES = [
    "Internship Preparation Workshop",
    "Career Development Seminar",
    "Graduate Employability Clinic",
    "Professional Skills Lab",
    "Interview Readiness Session",
    "CV and Portfolio Review",
]

CAMPUS_SERVICE_TITLES = [
    "Library Research Support",
    "Student Wellbeing Support",
    "Academic Advisory Session",
    "Learning Support Workshop",
    "Campus Guidance Briefing",
]

STUDENT_ACTIVITY_TITLES = [
    "Innovation Challenge",
    "Student Leadership Forum",
    "Technology Showcase",
    "Research Poster Session",
    "Entrepreneurship Seminar",
]

def choose_category(level: int) -> str:
    if level == 4000:
        weights = [0.55, 0.25, 0.08, 0.12]
    elif level == 3000:
        weights = [0.50, 0.22, 0.10, 0.18]
    elif level == 2000:
        weights = [0.58, 0.12, 0.10, 0.20]
    else:
        weights = [0.62, 0.08, 0.10, 0.20]
    return random.choices(CATEGORY_OPTIONS, weights=weights, k=1)[0]

def make_module_title(faculty: str, level: int, category: str) -> str:
    if category == "Career":
        return random.choice(CAREER_TITLES)
    if category == "Campus Service":
        return random.choice(CAMPUS_SERVICE_TITLES)
    if category == "Student Activity":
        return random.choice(STUDENT_ACTIVITY_TITLES)

    theme = FACULTY_THEMES[faculty]
    prefix = random.choice(theme["prefixes"])
    subject = random.choice(theme["subjects"])

    if level == 4000:
        return f"Level 4000 {prefix} {subject}"
    if level == 3000:
        return f"Level 3000 Advanced {prefix} {subject}"
    if level == 2000:
        return f"Level 2000 Intermediate {prefix} {subject}"
    return f"Level 1000 Introduction to {prefix} {subject}"

def make_topics(faculty: str, level: int, category: str) -> str:
    base_topics = FACULTY_THEMES[faculty]["topics"][:]
    random.shuffle(base_topics)
    chosen = base_topics[:3]

    level_terms = random.sample(LEVEL_TOPIC_BIAS[level], 1)

    if category == "Career":
        chosen += ["career", "employability", "professional skills"]
    elif category == "Campus Service":
        chosen += ["student support", "academic support"]
    elif category == "Student Activity":
        chosen += ["leadership", "innovation"]

    chosen += level_terms
    return ",".join(dict.fromkeys(chosen))  # remove duplicates while preserving order

def make_target_group(level: int, category: str) -> str:
    if category in ["Campus Service", "Student Activity"]:
        return "All Students"
    return LEVEL_LABELS[level]

def make_description(title: str, faculty: str, level: int, category: str, topics: str) -> str:
    topic_list = topics.split(",")[:3]
    if category == "Academic":
        return (
            f"{title} is designed for {LEVEL_LABELS[level].lower()} and focuses on "
            f"{', '.join(topic_list)} within {faculty}."
        )
    if category == "Career":
        return (
            f"{title} supports {LEVEL_LABELS[level].lower()} in preparing for internships, "
            f"employment, and professional development."
        )
    if category == "Campus Service":
        return (
            f"{title} provides university support services related to "
            f"{', '.join(topic_list)} for the UBD community."
        )
    return (
        f"{title} is an engagement opportunity for students interested in "
        f"{', '.join(topic_list)} and broader campus participation."
    )

def make_code(faculty: str, level: int, index_within_level: int) -> str:
    faculty_codes = {
        "School of Digital Science": "SDS",
        "Faculty of Arts and Social Sciences": "FASS",
        "Faculty of Science": "SCI",
        "School of Business and Economics": "SBE",
    }
    return f"{faculty_codes[faculty]}{level + index_within_level % 100:04d}"

def generate_rows():
    rows = []
    item_id = 1

    for level in LEVELS:
        for i in range(MODULES_PER_LEVEL):
            faculty = random.choices(
                FACULTIES,
                weights=[0.35, 0.25, 0.20, 0.20],
                k=1
            )[0]

            category = choose_category(level)
            title = make_module_title(faculty, level, category)
            topics = make_topics(faculty, level, category)
            target_group = make_target_group(level, category)
            description = make_description(title, faculty, level, category, topics)
            module_code = make_code(faculty, level, i)

            rows.append({
                "id": item_id,
                "module_code": module_code,
                "title": title,
                "category": category,
                "topic_tags": topics,
                "target_group": target_group,
                "description": description,
                "faculty_tag": faculty,
                "level_tag": f"Level {level}",
                "study_level_match": LEVEL_LABELS[level],
                "module_level_number": level,
                "credits": random.choice([3, 4]),
                "semester": random.choice(["Semester 1", "Semester 2"]),
            })
            item_id += 1

    return rows

def main():
    rows = generate_rows()
    fieldnames = [
        "id",
        "module_code",
        "title",
        "category",
        "topic_tags",
        "target_group",
        "description",
        "faculty_tag",
        "level_tag",
        "study_level_match",
        "module_level_number",
        "credits",
        "semester",
    ]

    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Created {len(rows)} synthetic modules at: {OUTPUT_FILE.resolve()}")

if __name__ == "__main__":
    main()