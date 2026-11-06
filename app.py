import os, json, sqlite3
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
from config import SECRET_KEY, DATABASE
from database.db import get_db, init_db, close_db
from preprocessing.language_detection import detect_language
from models.predict import predict_query
from recommendations.recommendation_engine import build_recommendations

app = Flask(__name__)
app.config.update(SECRET_KEY=SECRET_KEY, MAX_CONTENT_LENGTH=2 * 1024 * 1024)
app.teardown_appcontext(close_db)
init_db(app)

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        uid = session.get("user_id")

        if uid is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))

        # Verify that user still exists in SQLite
        user = get_db().execute(
            "SELECT id FROM users WHERE id = ?", (uid,)
        ).fetchone()

        if user is None:
            session.clear()
            flash("Session expired. Please login again.", "warning")
            return redirect(url_for("login"))

        return fn(*args, **kwargs)

    return wrapper

def current_profile():
    row = get_db().execute("SELECT * FROM user_profiles WHERE user_id=?", (session["user_id"],)).fetchone()
    return dict(row) if row else {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip().lower()
        password = request.form.get("password","")
        if not name or not email or len(password) < 8:
            flash("Enter your name, valid email and a password of at least 8 characters.", "danger")
            return render_template("register.html")
        try:
            db = get_db()
            cur = db.execute("INSERT INTO users(name,email,password_hash) VALUES(?,?,?)",
                             (name,email,generate_password_hash(password)))
            db.execute("INSERT INTO user_profiles(user_id) VALUES(?)",(cur.lastrowid,))
            db.commit()
            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("That email is already registered.", "danger")
    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email","").strip().lower()
        user = get_db().execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], request.form.get("password","")):
            session.clear(); session["user_id"] = user["id"]; session["name"] = user["name"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db(); uid = session["user_id"]
    total_users = db.execute("SELECT COUNT(*) n FROM users").fetchone()["n"]
    total_queries = db.execute("SELECT COUNT(*) n FROM nutrition_queries WHERE user_id=?", (uid,)).fetchone()["n"]
    common = db.execute("""SELECT cr.predicted_intent, COUNT(*) n FROM classification_results cr
        JOIN nutrition_queries q ON q.id=cr.query_id WHERE q.user_id=?
        GROUP BY cr.predicted_intent ORDER BY n DESC LIMIT 1""",(uid,)).fetchone()
    recent = db.execute("""SELECT q.*, cr.predicted_intent, cr.confidence FROM nutrition_queries q
        LEFT JOIN classification_results cr ON cr.query_id=q.id
        WHERE q.user_id=? ORDER BY q.id DESC LIMIT 6""",(uid,)).fetchall()
    return render_template("dashboard.html", total_users=total_users, total_queries=total_queries,
                           common=common, recent=recent, profile=current_profile())

@app.route("/profile", methods=["GET","POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        def number(key, cast, minimum, maximum):
            value = request.form.get(key,"").strip()
            if not value: return None
            try:
                result = cast(value)
                if not minimum <= result <= maximum: raise ValueError()
                return result
            except ValueError: raise ValueError(f"Invalid {key}.")
        try:
            age = number("age", int, 1, 120)
            weight = number("weight", float, 1, 500)
            height = number("height", float, 30, 260)
            db.execute("""UPDATE user_profiles SET age=?,gender=?,weight=?,height=?,diet_preference=?,
                health_goal=?,activity_level=?,allergies=? WHERE user_id=?""",
                (age, request.form.get("gender",""), weight, height,
                 request.form.get("diet_preference",""), request.form.get("health_goal",""),
                 request.form.get("activity_level",""), request.form.get("allergies","").strip(),
                 session["user_id"]))
            db.commit(); flash("Profile saved.", "success")
            return redirect(url_for("profile"))
        except ValueError as e:
            flash(str(e), "danger")
    return render_template("profile.html", profile=current_profile())

@app.route("/classify", methods=["GET","POST"])
@login_required
def classify():
    if request.method == "POST":
        query = request.form.get("query","").strip()
        if not query or len(query) > 1000:
            flash("Enter a question up to 1,000 characters.", "danger")
            return redirect(url_for("classify"))
        try:
            result = predict_query(query)
            language = detect_language(query)
            recs = build_recommendations(result, current_profile(), query)
            db = get_db()
            cur = db.execute("INSERT INTO nutrition_queries(user_id,query_text,detected_language) VALUES(?,?,?)",
                             (session["user_id"],query,language))
            qid = cur.lastrowid
            db.execute("""INSERT INTO classification_results(query_id,predicted_intent,confidence,food_item,top_predictions)
                          VALUES(?,?,?,?,?)""",
                       (qid,result["intent"],result["confidence"],recs["items"][0]["food"] if recs["items"] else None,
                        json.dumps(result["top_predictions"])))
            db.execute("INSERT INTO recommendation_history(query_id,user_id,recommendations_json) VALUES(?,?,?)",
                       (qid,session["user_id"],json.dumps(recs)))
            db.commit()
            return render_template("results.html", query=query, result=result, language=language, recs=recs)
        except sqlite3.IntegrityError:
            get_db().rollback()
            app.logger.exception("Database integrity error")
            flash("Database session mismatch. Please login again.", "danger")
    return redirect(url_for("login"))

except Exception as e:
    get_db().rollback()
    app.logger.exception("Classification failed")
    flash(f"Classification error: {str(e)}", "danger")
    return redirect(url_for("classify"))
    return render_template("index.html", show_query=True)

@app.route("/history")
@login_required
def history():
    q = request.args.get("q","").strip()
    sql = """SELECT q.*, cr.predicted_intent, cr.confidence FROM nutrition_queries q
             LEFT JOIN classification_results cr ON cr.query_id=q.id WHERE q.user_id=?"""
    params = [session["user_id"]]
    if q:
        sql += " AND (q.query_text LIKE ? OR cr.predicted_intent LIKE ?)"
        params += [f"%{q}%", f"%{q}%"]
    rows = get_db().execute(sql+" ORDER BY q.id DESC", params).fetchall()
    return render_template("history.html", rows=rows, search=q)

@app.post("/history/clear")
@login_required
def clear_history():
    get_db().execute("DELETE FROM nutrition_queries WHERE user_id=?", (session["user_id"],))
    get_db().commit()
    flash("Your query history was cleared.", "success")
    return redirect(url_for("history"))

@app.route("/api/classify", methods=["POST"])
@login_required
def api_classify():
    data = request.get_json(silent=True) or {}
    query = str(data.get("query","")).strip()
    if not query or len(query) > 1000:
        return jsonify({"error":"query is required and must be at most 1,000 characters"}), 400
    try:
        result = predict_query(query)
        result["language"] = detect_language(query)
        result["recommendations"] = build_recommendations(result, current_profile(), query)
        return jsonify(result)
    except Exception:
        app.logger.exception("API classification failed")
        return jsonify({"error":"Classifier unavailable; train the model first."}), 503

@app.errorhandler(404)
def not_found(e):
    return render_template("base.html", standalone_message="Page not found."), 404

if __name__ == "__main__":
    app.run(debug=True)
