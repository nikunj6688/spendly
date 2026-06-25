# Spec: Edit Expense

## Overview
This step converts the `GET /expenses/<id>/edit` stub into a fully working edit
flow. A logged-in user can click an **Edit** button next to any of their own
expenses on the profile page, land on a pre-populated form, change fields, and
save. The route enforces ownership — users can only edit their own expenses.
This is the first operation that mutates an existing row in the `expenses` table
from the UI.

## Depends on
- Step 1 — Database setup (`expenses` table with `id`, `user_id`, `amount`, `category`, `date`, `description`)
- Step 3 — Login / Logout (session key `user_id`)
- Step 5 — Profile page (entry point; expenses list must expose `id` for edit links)
- Step 7 — Add Expense (validation rules are the same; form is structurally identical)

## Routes
- `GET /expenses/<int:id>/edit` — render pre-populated edit form for expense `id` — logged-in only
- `POST /expenses/<int:id>/edit` — validate and update the expense row, then redirect — logged-in only

## Database changes
No new tables or columns. The existing `expenses` table has all required columns.

## Templates
- **Create:** `templates/edit_expense.html`
  - Extends `base.html`
  - Form with `method="post"` and `action="/expenses/<id>/edit"`
  - Fields (pre-populated from the existing row):
    - `amount` — number input, `step="0.01"`, `min="0.01"`, required
    - `category` — `<select>` with the same seven fixed options as add-expense; selected option pre-filled
    - `date` — date input, required, pre-filled from the existing row
    - `description` — text input, optional, max 200 characters, pre-filled
  - Submit button labelled "Save Changes"
  - Cancel link back to `/profile`
  - Inline error message when validation fails (re-populate submitted values)

- **Modify:** `templates/profile.html`
  - Add an **Actions** column header to the expenses table `<thead>`
  - Add an **Edit** link per row: `<a href="{{ url_for('edit_expense', id=e.id) }}">Edit</a>`
  - The profile route query must also `SELECT id` so `e.id` is available in the template

## Files to change
- `app.py`
  - Replace the `edit_expense()` stub with a proper `GET/POST` handler
  - Update the `profile()` route's SQL query to include `id` in the `SELECT` list
- `templates/profile.html`
  - Add Actions column header and per-row Edit link (see Templates section above)

## Files to create
- `templates/edit_expense.html` — pre-populated edit form
- `static/css/edit_expense.css` — page-specific styles (import in template via `<link>`; may reuse add-expense styles)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL via `get_db()` only
- Parameterised queries only — no f-strings or `%` formatting in SQL
- Passwords hashed with `werkzeug` — do not touch auth logic
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Vanilla JS only — no frameworks
- Unauthenticated requests to both `GET` and `POST` must redirect to `/login`
- Ownership check: after fetching the expense by `id`, verify `expense["user_id"] == session["user_id"]`; if not, return `404` (do not reveal the expense exists)
- If the expense `id` does not exist, return `404`
- Server-side validation rules (identical to add-expense):
  - `amount` must be a positive finite number (cast with `float()`; catch `ValueError`)
  - `category` must be one of the seven allowed values
  - `date` must be a valid `YYYY-MM-DD` string (validate with `datetime.strptime`)
  - `description` is optional; strip whitespace; max 200 characters
- On validation failure: re-render the edit form with an error message and the submitted values pre-filled
- On success: `UPDATE` the row, then `redirect(url_for("profile"))` with `flash("Expense updated.", "success")`
- Only `amount`, `category`, `date`, and `description` may be updated — never `user_id`, `id`, or `created_at`

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense belonging to another user returns 404
- [ ] Visiting `/expenses/<id>/edit` for a non-existent `id` returns 404
- [ ] `GET /expenses/<id>/edit` renders the edit form with all four fields pre-populated from the database
- [ ] Submitting valid changes updates the row in `expenses` and redirects to `/profile` with a success flash
- [ ] The updated values are visible in the profile page expense table immediately after saving
- [ ] Submitting with a missing or invalid amount shows an inline error and re-populates all fields with the submitted values
- [ ] Submitting with an invalid date string shows an inline error and re-populates all fields
- [ ] Submitting with a category not in the allowed list is rejected with an error
- [ ] The profile page expenses table has an Edit link per row that points to the correct `/expenses/<id>/edit` URL
- [ ] No database row is modified when validation fails
