from flask import Flask, request, redirect, url_for, session, render_template, flash
import sqlite3
import csv
from pathlib import Path
from math import sqrt

app = Flask(__name__)
app.secret_key = "change-this-secret-key"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "smartrecommend.db"
CSV_PATH = BASE_DIR / "synthetic_modules_1000.csv"


# -----------------------------
# Database helpers
# -----------------------------
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# Schema and seed data
# -----------------------------
def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'student'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id INTEGER PRIMARY KEY,
            faculty TEXT,
            study_level TEXT,
            preferred_categories TEXT,
            preferred_topics TEXT,
            career_interest TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_code TEXT NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            topic_tags TEXT NOT NULL,
            target_group TEXT NOT NULL,
            description TEXT NOT NULL,
            faculty_tag TEXT NOT NULL DEFAULT 'All Faculties',
            level_tag TEXT NOT NULL DEFAULT 'All Levels',
            study_level_match TEXT NOT NULL DEFAULT 'All Levels',
            module_level_number INTEGER NOT NULL DEFAULT 1000,
            credits INTEGER NOT NULL DEFAULT 3,
            semester TEXT NOT NULL DEFAULT 'Semester 1'
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
            UNIQUE(user_id, item_id),
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(item_id) REFERENCES items(id)
        )
    """)

    conn.commit()
    conn.close()


def ensure_item_columns():
    conn = get_connection()
    cur = conn.cursor()
    columns = [row[1] for row in cur.execute("PRAGMA table_info(items)").fetchall()]

    additions = {
        "module_code": "TEXT NOT NULL DEFAULT ''",
        "topic_tags": "TEXT NOT NULL DEFAULT ''",
        "target_group": "TEXT NOT NULL DEFAULT 'All Users'",
        "faculty_tag": "TEXT NOT NULL DEFAULT 'All Faculties'",
        "level_tag": "TEXT NOT NULL DEFAULT 'All Levels'",
        "study_level_match": "TEXT NOT NULL DEFAULT 'All Levels'",
        "module_level_number": "INTEGER NOT NULL DEFAULT 1000",
        "credits": "INTEGER NOT NULL DEFAULT 3",
        "semester": "TEXT NOT NULL DEFAULT 'Semester 1'",
    }

    for col_name, col_type in additions.items():
        if col_name not in columns:
            cur.execute(f"ALTER TABLE items ADD COLUMN {col_name} {col_type}")

    conn.commit()
    conn.close()


def seed_users_and_profiles():
    conn = get_connection()
    cur = conn.cursor()

    users = [
        ("alice", "1234", "Alice Rahman", "student"),
        ("brian", "1234", "Brian Lim", "student"),
        ("charlie", "1234", "Charlie Yusuf", "student"),
        ("staff1", "1234", "Career Centre Staff", "staff"),
    ]

    for user in users:
        cur.execute(
            "INSERT OR IGNORE INTO users (username, password, full_name, role) VALUES (?, ?, ?, ?)",
            user,
        )

    profiles = [
        (1, "School of Digital Science", "Final Year Students", "Academic,Career", "cloud,data mining,analytics,research", "Data and Technology"),
        (2, "School of Digital Science", "Undergraduate", "Academic,Student Activity", "python,ai,programming,technology", "Internship and Career"),
        (3, "Faculty of Arts and Social Sciences", "Undergraduate", "Academic,Campus Service,Student Activity", "research,writing,innovation", "Research and Development"),
        (4, "Career Centre", "Staff", "Career,Campus Service", "career,employability,student support", "Student Services"),
    ]

    for profile in profiles:
        cur.execute(
            """
            INSERT OR IGNORE INTO user_profiles
            (user_id, faculty, study_level, preferred_categories, preferred_topics, career_interest)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            profile,
        )

    conn.commit()
    conn.close()


def seed_items_from_csv():
    if not CSV_PATH.exists():
        raise FileNotFoundError(
            f"CSV file not found: {CSV_PATH}. Place synthetic_modules_1000.csv in the same folder as app.py"
        )

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM items")
    current_count = cur.fetchone()["count"]
    if current_count > 0:
        conn.close()
        return

    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cur.execute(
                """
                INSERT INTO items (
                    module_code, title, category, topic_tags, target_group, description,
                    faculty_tag, level_tag, study_level_match, module_level_number, credits, semester
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row.get("module_code", ""),
                    row.get("title", "Untitled Module"),
                    row.get("category", "Academic"),
                    row.get("topic_tags", ""),
                    row.get("target_group", "All Students"),
                    row.get("description", "No description available."),
                    row.get("faculty_tag", "All Faculties"),
                    row.get("level_tag", "All Levels"),
                    row.get("study_level_match", "All Levels"),
                    int(row.get("module_level_number", 1000) or 1000),
                    int(row.get("credits", 3) or 3),
                    row.get("semester", "Semester 1"),
                ),
            )

    conn.commit()
    conn.close()


def seed_ratings():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) AS count FROM ratings")
    count = cur.fetchone()["count"]
    if count > 0:
        conn.close()
        return

    module_map = {
        row["module_code"]: row["id"]
        for row in cur.execute("SELECT id, module_code FROM items").fetchall()
    }

    seed_pairs = [
        ("alice", ["SDS1001", "SDS1002", "SDS1003", "SDS1004"], [5, 5, 4, 4]),
        ("brian", ["SDS1005", "SDS1006", "SDS1007", "SDS1008"], [5, 4, 5, 4]),
        ("charlie", ["FASS1009", "FASS1010", "FASS1011", "FASS1012"], [5, 4, 5, 4]),
        ("staff1", ["SCI1004", "SBE1005", "FASS1007", "SDS1024"], [4, 5, 4, 5]),
    ]

    user_map = {
        row["username"]: row["id"]
        for row in cur.execute("SELECT id, username FROM users").fetchall()
    }

    for username, module_codes, ratings in seed_pairs:
        user_id = user_map.get(username)
        if not user_id:
            continue
        for module_code, rating in zip(module_codes, ratings):
            item_id = module_map.get(module_code)
            if item_id:
                cur.execute(
                    "INSERT OR IGNORE INTO ratings (user_id, item_id, rating) VALUES (?, ?, ?)",
                    (user_id, item_id, rating),
                )

    conn.commit()
    conn.close()


# -----------------------------
# Utility helpers
# -----------------------------
def tokenize_csv(text):
    return {token.strip().lower() for token in (text or "").split(",") if token.strip()}


def words(text):
    return {part.strip().lower() for part in (text or "").replace(",", " ").split() if part.strip()}


def get_user_ratings(user_id):
    conn = get_connection()
    rows = conn.execute(
        "SELECT item_id, rating FROM ratings WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    conn.close()
    return {row["item_id"]: row["rating"] for row in rows}


def get_all_users():
    conn = get_connection()
    rows = conn.execute("SELECT id, username, full_name, role FROM users").fetchall()
    conn.close()
    return rows


def get_profile(user_id):
    conn = get_connection()
    profile = conn.execute(
        "SELECT * FROM user_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return profile


def profile_completed(user_id):
    profile = get_profile(user_id)
    if not profile:
        return False
    return bool((profile["preferred_categories"] or "").strip() and (profile["preferred_topics"] or "").strip())


def cosine_similarity(ratings_a, ratings_b):
    common_items = set(ratings_a.keys()) & set(ratings_b.keys())
    if not common_items:
        return 0.0

    dot_product = sum(ratings_a[i] * ratings_b[i] for i in common_items)
    norm_a = sqrt(sum(value * value for value in ratings_a.values()))
    norm_b = sqrt(sum(value * value for value in ratings_b.values()))

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return dot_product / (norm_a * norm_b)


def score_item_from_profile(profile, item):
    if not profile:
        return 0, []

    score = 0
    reasons = []
    preferred_categories = tokenize_csv(profile["preferred_categories"])
    preferred_topics = tokenize_csv(profile["preferred_topics"])
    item_topics = tokenize_csv(item["topic_tags"])
    item_words = words(item["title"] + " " + item["description"] + " " + item["topic_tags"])

    faculty = (profile["faculty"] or "").strip().lower()
    study_level = (profile["study_level"] or "").strip().lower()
    career_interest_words = words(profile["career_interest"])
    faculty_tag = (item["faculty_tag"] or "").strip().lower()
    study_level_match = (item["study_level_match"] or "").strip().lower()
    target_group = (item["target_group"] or "").strip().lower()
    module_level_number = int(item["module_level_number"] or 1000)

    if item["category"].lower() in preferred_categories:
        score += 6
        reasons.append(f"Matches your preferred category: {item['category']}")

    topic_overlap = sorted(preferred_topics & item_topics)
    if topic_overlap:
        score += len(topic_overlap) * 5
        reasons.append("Matches your selected topics: " + ", ".join(topic_overlap[:3]))

    if study_level and study_level in {study_level_match, target_group}:
        score += 12
        reasons.append(f"Directly suited to your study level: {profile['study_level']}")

    if study_level == "final year students" and module_level_number >= 4000:
        score += 15
        reasons.append("Prioritised because you selected Final Year Students")
    elif study_level == "senior students" and module_level_number >= 3000:
        score += 10
        reasons.append("Prioritised because you selected Senior Students")
    elif study_level == "undergraduate" and module_level_number in {1000, 2000}:
        score += 8
        reasons.append("Suitable for undergraduate study level")
    elif study_level == "postgraduate" and "postgraduate" in item_words:
        score += 12
        reasons.append("Aligned with postgraduate pathway")

    if faculty and faculty_tag == faculty:
        score += 10
        reasons.append(f"Relevant to your faculty: {profile['faculty']}")
    elif faculty_tag == "all faculties":
        score += 1

    matched_interest_words = sorted(career_interest_words & item_words)
    if matched_interest_words:
        score += min(len(matched_interest_words), 2) * 3
        reasons.append("Aligned with your career interest")

    return score, reasons


def get_popular_items(limit=4):
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT i.*, COALESCE(AVG(r.rating), 0) AS avg_rating, COUNT(r.id) AS rating_count
        FROM items i
        LEFT JOIN ratings r ON i.id = r.item_id
        GROUP BY i.id
        ORDER BY avg_rating DESC, rating_count DESC, i.title ASC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return rows


def recommend_items_for_user(user_id, limit=6):
    target_ratings = get_user_ratings(user_id)
    users = get_all_users()
    profile = get_profile(user_id)

    similarities = []
    for user in users:
        other_id = user["id"]
        if other_id == user_id:
            continue
        other_ratings = get_user_ratings(other_id)
        sim = cosine_similarity(target_ratings, other_ratings)
        if sim > 0:
            similarities.append((other_id, sim))

    similarities.sort(key=lambda x: x[1], reverse=True)

    conn = get_connection()
    all_items = conn.execute("SELECT * FROM items").fetchall()
    conn.close()

    target_seen = set(target_ratings.keys())
    scored_items = {}
    reasons_map = {}

    for item in all_items:
        if item["id"] in target_seen:
            continue
        profile_score, profile_reasons = score_item_from_profile(profile, item)
        scored_items[item["id"]] = float(profile_score)
        reasons_map[item["id"]] = list(profile_reasons)

    for other_id, sim in similarities:
        other_ratings = get_user_ratings(other_id)
        for item_id, rating in other_ratings.items():
            if item_id in target_seen:
                continue
            scored_items.setdefault(item_id, 0.0)
            scored_items[item_id] += sim * rating
            if item_id not in reasons_map:
                reasons_map[item_id] = []
            if not any("similar users" in reason.lower() for reason in reasons_map[item_id]):
                reasons_map[item_id].append("Supported by ratings from similar users")

    ranked = sorted(scored_items.items(), key=lambda x: x[1], reverse=True)
    item_lookup = {item["id"]: item for item in all_items}

    recommendations = []
    seen_titles = set()
    for item_id, score in ranked:
        if score <= 0 or item_id not in item_lookup:
            continue
        item = item_lookup[item_id]
        title_key = item["title"].strip().lower() + str(item["module_code"]).strip().lower()
        if title_key in seen_titles:
            continue
        seen_titles.add(title_key)
        recommendations.append(
            {
                "id": item["id"],
                "module_code": item["module_code"],
                "title": item["title"],
                "category": item["category"],
                "topic_tags": item["topic_tags"],
                "target_group": item["target_group"],
                "description": item["description"],
                "faculty_tag": item["faculty_tag"],
                "level_tag": item["level_tag"],
                "semester": item["semester"],
                "credits": item["credits"],
                "score": round(score, 2),
                "reasons": reasons_map.get(item_id, [])[:4],
            }
        )
        if len(recommendations) >= limit:
            break

    if not recommendations:
        popular = get_popular_items(limit=limit)
        return [
            {
                "id": item["id"],
                "module_code": item["module_code"],
                "title": item["title"],
                "category": item["category"],
                "topic_tags": item["topic_tags"],
                "target_group": item["target_group"],
                "description": item["description"],
                "faculty_tag": item["faculty_tag"],
                "level_tag": item["level_tag"],
                "semester": item["semester"],
                "credits": item["credits"],
                "score": 0,
                "reasons": ["Shown because it is currently a popular item"],
            }
            for item in popular
        ]

    return recommendations


def get_item(item_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    return row


def get_current_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    conn = get_connection()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return user


def log_interaction(user_id, item_id, action):
    conn = get_connection()
    conn.execute(
        "INSERT INTO interactions (user_id, item_id, action) VALUES (?, ?, ?)",
        (user_id, item_id, action),
    )
    conn.commit()
    conn.close()


@app.context_processor
def inject_user():
    return {"current_user": get_current_user()}


@app.route("/")
def home():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        conn = get_connection()
        user = conn.execute(
            "SELECT * FROM users WHERE username = ? AND password = ?",
            (username, password),
        ).fetchone()
        conn.close()

        if user:
            session["user_id"] = user["id"]
            if not profile_completed(user["id"]):
                return redirect(url_for("profile_setup"))
            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/profile", methods=["GET", "POST"])
def profile_setup():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    existing = get_profile(user["id"])

    if request.method == "POST":
        faculty = request.form.get("faculty", "").strip()
        study_level = request.form.get("study_level", "").strip()
        preferred_categories = request.form.getlist("preferred_categories")
        preferred_topics = request.form.get("preferred_topics", "").strip()
        career_interest = request.form.get("career_interest", "").strip()

        preferred_categories_text = ",".join(preferred_categories)

        conn = get_connection()
        conn.execute(
            """
            INSERT INTO user_profiles (user_id, faculty, study_level, preferred_categories, preferred_topics, career_interest, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id)
            DO UPDATE SET
                faculty = excluded.faculty,
                study_level = excluded.study_level,
                preferred_categories = excluded.preferred_categories,
                preferred_topics = excluded.preferred_topics,
                career_interest = excluded.career_interest,
                updated_at = CURRENT_TIMESTAMP
            """,
            (user["id"], faculty, study_level, preferred_categories_text, preferred_topics, career_interest),
        )
        conn.commit()
        conn.close()

        flash("Profile information saved successfully. Your recommendation results have been recalculated.")
        return redirect(url_for("dashboard"))

    existing_categories = tokenize_csv(existing["preferred_categories"]) if existing else set()

    return render_template(
        "profile.html",
        existing=existing,
        existing_categories=existing_categories
    )


@app.route("/dashboard")
def dashboard():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    if not profile_completed(user["id"]):
        flash("Please complete your profile before viewing recommendations.")
        return redirect(url_for("profile_setup"))

    recommendations = recommend_items_for_user(user["id"], limit=6)
    popular_items = get_popular_items(limit=4)
    profile = get_profile(user["id"])
    interaction_count = len(get_user_ratings(user["id"]))

    return render_template(
        "dashboard.html",
        user=user,
        recommendations=recommendations,
        popular_items=popular_items,
        profile=profile,
        interaction_count=interaction_count,
    )


@app.route("/item/<int:item_id>", methods=["GET", "POST"])
def item_detail(item_id):
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    item = get_item(item_id)
    if not item:
        flash("Module not found.")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        rating = int(request.form.get("rating"))
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO ratings (user_id, item_id, rating)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, item_id)
            DO UPDATE SET rating = excluded.rating
            """,
            (user["id"], item_id, rating),
        )
        conn.commit()
        conn.close()

        log_interaction(user["id"], item_id, f"rated_{rating}")
        flash("Your rating has been saved successfully. Future recommendations will adapt based on this feedback.")
        return redirect(url_for("dashboard"))

    log_interaction(user["id"], item_id, "viewed")

    conn = get_connection()
    existing = conn.execute(
        "SELECT rating FROM ratings WHERE user_id = ? AND item_id = ?",
        (user["id"], item_id),
    ).fetchone()
    conn.close()

    current_rating = existing["rating"] if existing else ""

    return render_template(
        "item_detail.html",
        item=item,
        current_rating=current_rating,
    )


@app.route("/analytics")
def analytics():
    user = get_current_user()
    if not user:
        return redirect(url_for("login"))

    conn = get_connection()
    popular_rows = conn.execute(
        """
        SELECT module_code, title, COUNT(inter.id) AS interaction_count
        FROM items i
        LEFT JOIN interactions inter ON i.id = inter.item_id
        GROUP BY i.id
        ORDER BY interaction_count DESC, i.title ASC
        LIMIT 5
        """
    ).fetchall()

    rating_rows = conn.execute(
        """
        SELECT module_code, title, ROUND(AVG(r.rating), 2) AS avg_rating
        FROM items i
        LEFT JOIN ratings r ON i.id = r.item_id
        GROUP BY i.id
        ORDER BY avg_rating DESC, i.title ASC
        LIMIT 5
        """
    ).fetchall()

    level_rows = conn.execute(
        """
        SELECT module_level_number, COUNT(*) AS cnt
        FROM items
        GROUP BY module_level_number
        ORDER BY module_level_number ASC
        """
    ).fetchall()

    profile_rows = conn.execute(
        """
        SELECT full_name, faculty, study_level, preferred_categories, preferred_topics
        FROM users u
        LEFT JOIN user_profiles p ON u.id = p.user_id
        ORDER BY u.full_name ASC
        """
    ).fetchall()
    conn.close()

    return render_template(
        "analytics.html",
        popular_rows=popular_rows,
        rating_rows=rating_rows,
        level_rows=level_rows,
        profile_rows=profile_rows,
    )


if __name__ == "__main__":
    init_db()
    ensure_item_columns()
    seed_users_and_profiles()
    seed_items_from_csv()
    seed_ratings()
    app.run(debug=True)


init_db()
ensure_item_columns()
seed_users_and_profiles()
seed_items_from_csv()
seed_ratings()

if __name__ == "__main__":
    app.run(debug=True)
