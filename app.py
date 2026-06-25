import math
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db, init_db, seed_db

app = Flask(__name__)
app.secret_key = 'spendly-secret-key'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

EXPENSE_CATEGORIES = ["Food", "Transport", "Bills", "Health", "Entertainment", "Shopping", "Other"]

# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #

@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()

        if not name or not email or not password:
            return render_template("register.html", error="All fields are required.")

        db = get_db()
        if db.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            db.close()
            return render_template("register.html", error="Email already registered.")

        db.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            (name, email, generate_password_hash(password))
        )
        db.commit()
        db.close()
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("landing"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        db = get_db()
        user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        db.close()

        if not user or not check_password_hash(user["password_hash"], password):
            return render_template("login.html", error="Invalid email or password.", email=email)

        session["user_id"] = user["id"]
        session["user_name"] = user["name"]
        return redirect(url_for("profile"))

    return render_template("login.html")


# ------------------------------------------------------------------ #
# Placeholder routes — students will implement these                  #
# ------------------------------------------------------------------ #

@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("landing"))


@app.route("/profile", methods=["GET", "POST"])
def profile():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()

        if not name or not email:
            flash("Name and email are required.", "error")
            return redirect(url_for("profile"))

        db = get_db()
        duplicate = db.execute(
            "SELECT 1 FROM users WHERE email = ? AND id != ?",
            (email, session["user_id"])
        ).fetchone()

        if duplicate:
            db.close()
            flash("That email is already used by another account.", "error")
            return redirect(url_for("profile"))

        db.execute(
            "UPDATE users SET name = ?, email = ? WHERE id = ?",
            (name, email, session["user_id"])
        )
        db.commit()
        db.close()

        session["user_name"] = name
        flash("Profile updated successfully.", "success")
        return redirect(url_for("profile"))

    # Parse & validate date filter query params
    date_from = request.args.get('from', '').strip()
    date_to   = request.args.get('to', '').strip()

    valid_from = valid_to = None
    try:
        if date_from:
            datetime.strptime(date_from, '%Y-%m-%d')
            valid_from = date_from
    except ValueError:
        flash('Invalid "from" date — showing all expenses.', 'error')

    try:
        if date_to:
            datetime.strptime(date_to, '%Y-%m-%d')
            valid_to = date_to
    except ValueError:
        flash('Invalid "to" date — showing all expenses.', 'error')

    # If either date is invalid, discard both to show all expenses
    if date_from and valid_from is None:
        valid_to = None
    if date_to and valid_to is None:
        valid_from = None

    # Swap silently if from > to
    if valid_from and valid_to and valid_from > valid_to:
        valid_from, valid_to = valid_to, valid_from

    db = get_db()
    user = db.execute(
        "SELECT id, name, email, created_at FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    query = (
        "SELECT id, date, category, description, amount FROM expenses "
        "WHERE user_id = ?"
    )
    params = [session["user_id"]]
    if valid_from:
        query += " AND date >= ?"
        params.append(valid_from)
    if valid_to:
        query += " AND date <= ?"
        params.append(valid_to)
    query += " ORDER BY date DESC"
    rows = db.execute(query, params).fetchall()
    db.close()

    # Compute summary stats in Python
    expenses = [dict(r) for r in rows]
    total = sum(e['amount'] for e in expenses)
    count = len(expenses)
    cat_totals = {}
    for e in expenses:
        cat_totals[e['category']] = cat_totals.get(e['category'], 0) + e['amount']
    top_category = max(cat_totals, key=cat_totals.get) if cat_totals else '—'

    dt = datetime.fromisoformat(user["created_at"])
    member_since = dt.strftime("%B ") + str(dt.day) + dt.strftime(", %Y")

    return render_template(
        "profile.html",
        user=user,
        member_since=member_since,
        expenses=expenses,
        date_from=valid_from or '',
        date_to=valid_to or '',
        total=total,
        count=count,
        top_category=top_category,
    )


@app.route("/profile/change-password", methods=["POST"])
def change_password():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    current = request.form.get("current_password", "")
    new_pw = request.form.get("new_password", "")
    confirm = request.form.get("confirm_password", "")

    if not current or not new_pw or not confirm:
        flash("All password fields are required.", "error")
        return redirect(url_for("profile"))

    if new_pw != confirm:
        flash("New password and confirmation do not match.", "error")
        return redirect(url_for("profile"))

    db = get_db()
    user = db.execute(
        "SELECT password_hash FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    if not check_password_hash(user["password_hash"], current):
        db.close()
        flash("Current password is incorrect.", "error")
        return redirect(url_for("profile"))

    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (generate_password_hash(new_pw), session["user_id"])
    )
    db.commit()
    db.close()

    flash("Password changed successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/analytics")
def analytics():
    if not session.get("user_id"):
        return redirect(url_for("login"))
    return render_template("analytics.html")



@app.route("/expenses/add", methods=["GET", "POST"])
def add_expense():
    if not session.get("user_id"):
        return redirect(url_for("login"))

    if request.method == "POST":
        amount_raw  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        date_raw    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        error  = None
        amount = None

        if not amount_raw:
            error = "Amount is required."
        else:
            try:
                amount = float(amount_raw)
                if amount <= 0 or not math.isfinite(amount):
                    error = "Amount must be a positive number."
            except ValueError:
                error = "Amount must be a number (e.g. 12.50)."

        if not error and category not in EXPENSE_CATEGORIES:
            error = "Please select a valid category."

        if not error:
            try:
                datetime.strptime(date_raw, "%Y-%m-%d")
            except ValueError:
                error = "Date must be a valid YYYY-MM-DD value."

        if not error and len(description) > 200:
            error = "Description must be 200 characters or fewer."

        if error:
            return render_template(
                "add_expense.html",
                error=error,
                categories=EXPENSE_CATEGORIES,
                form={"amount": amount_raw, "category": category,
                      "date": date_raw, "description": description},
            )

        db = get_db()
        try:
            db.execute(
                "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
                (session["user_id"], amount, category, date_raw, description),
            )
            db.commit()
        finally:
            db.close()

        flash("Expense added.", "success")
        return redirect(url_for("profile"))

    today = datetime.today().strftime("%Y-%m-%d")
    return render_template(
        "add_expense.html",
        categories=EXPENSE_CATEGORIES,
        form={"amount": "", "category": "", "date": today, "description": ""},
    )


@app.route("/expenses/<int:id>/edit", methods=["GET", "POST"])
def edit_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    expense = db.execute(
        "SELECT id, user_id, amount, category, date, description "
        "FROM expenses WHERE id = ?",
        (id,)
    ).fetchone()
    db.close()

    if expense is None or expense["user_id"] != session["user_id"]:
        abort(404)

    if request.method == "POST":
        amount_raw  = request.form.get("amount", "").strip()
        category    = request.form.get("category", "").strip()
        date_raw    = request.form.get("date", "").strip()
        description = request.form.get("description", "").strip()

        error  = None
        amount = None

        if not amount_raw:
            error = "Amount is required."
        else:
            try:
                amount = float(amount_raw)
                if amount <= 0 or not math.isfinite(amount):
                    error = "Amount must be a positive number."
            except ValueError:
                error = "Amount must be a number (e.g. 12.50)."

        if not error and category not in EXPENSE_CATEGORIES:
            error = "Please select a valid category."

        if not error:
            try:
                datetime.strptime(date_raw, "%Y-%m-%d")
            except ValueError:
                error = "Date must be a valid YYYY-MM-DD value."

        if not error and len(description) > 200:
            error = "Description must be 200 characters or fewer."

        if error:
            return render_template(
                "edit_expense.html",
                error=error,
                categories=EXPENSE_CATEGORIES,
                form={"amount": amount_raw, "category": category,
                      "date": date_raw, "description": description},
                expense_id=id,
            )

        db = get_db()
        try:
            db.execute(
                "UPDATE expenses "
                "SET amount = ?, category = ?, date = ?, description = ? "
                "WHERE id = ? AND user_id = ?",
                (amount, category, date_raw, description,
                 id, session["user_id"]),
            )
            db.commit()
        finally:
            db.close()

        flash("Expense updated.", "success")
        return redirect(url_for("profile"))

    return render_template(
        "edit_expense.html",
        categories=EXPENSE_CATEGORIES,
        form={
            "amount": expense["amount"],
            "category": expense["category"],
            "date": expense["date"],
            "description": expense["description"] or "",
        },
        expense_id=id,
    )


@app.route("/expenses/<int:id>/delete", methods=["GET", "POST"])
def delete_expense(id):
    if not session.get("user_id"):
        return redirect(url_for("login"))

    db = get_db()
    expense = db.execute(
        "SELECT id, user_id, amount, category, date, description "
        "FROM expenses WHERE id = ?",
        (id,)
    ).fetchone()
    db.close()

    if expense is None or expense["user_id"] != session["user_id"]:
        abort(404)

    if request.method == "POST":
        db = get_db()
        try:
            db.execute(
                "DELETE FROM expenses WHERE id = ? AND user_id = ?",
                (id, session["user_id"]),
            )
            db.commit()
        finally:
            db.close()
        flash("Expense deleted.", "success")
        return redirect(url_for("profile"))

    return render_template("delete_expense.html", expense=expense)


with app.app_context():
    init_db()
    seed_db()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
