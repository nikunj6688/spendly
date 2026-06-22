# Spec: Add Expense

## Overview
This step implements the Add Expense feature, giving logged-in users a form to
record a new expense. The route stub at `GET /expenses/add` is converted into a
full `GET/POST` handler: `GET` renders a form with fields for amount, category,
date, and description; `POST` validates the input, inserts a row into the
`expenses` table, and redirects to `/profile` with a success flash. This is the
first write operation on the `expenses` table from the UI, enabling users to build
their own expense history rather than relying solely on seeded data.

## Depends on
- Step 1 — Database setup (`expenses` table with `user_id`, `amount`, `category`, `date`, `description`)
- Step 3 — Login / Logout (session keys `user_id` / `user_name`)
- Step 4 & 5 — Profile page (redirect target after successful submission)

## Routes
- `GET /expenses/add` — render the add-expense form — logged-in only
- `POST /expenses/add` — validate and insert the new expense, then redirect — logged-in only

## Database changes
No database changes. The `expenses` table already has all required columns:
`id`, `user_id`, `amount`, `category`, `date`, `description`, `created_at`.

## Templates
- **Create:** `templates/add_expense.html`
  - Extends `base.html`
  - Form with `method="post"` and `action="/expenses/add"`
  - Fields:
    - `amount` — number input, step="0.01", min="0.01", required
    - `category` — `<select>` with fixed options: Food, Transport, Bills, Health, Entertainment, Shopping, Other
    - `date` — date input, required, defaults to today's date
    - `description` — text input, optional, max 200 characters
  - Submit button labelled "Add Expense"
  - Cancel link back to `/profile`
  - Display an inline error message when validation fails (re-populate form values so the user doesn't retype)

## Files to change
- `app.py` — replace the `add_expense()` stub with a proper `GET/POST` handler

## Files to create
- `templates/add_expense.html` — the add-expense form template
- `static/css/add_expense.css` — page-specific styles for the form (import in template via `<link>`)

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
- Server-side validation rules:
  - `amount` must be a positive number greater than 0 (cast with `float()`; catch `ValueError`)
  - `category` must be one of the seven allowed values; reject anything else
  - `date` must be a valid `YYYY-MM-DD` string (validate with `datetime.strptime`)
  - `description` is optional; strip whitespace and store as-is (empty string is fine)
- On validation failure: re-render the form with an error message and the submitted values pre-filled
- On success: insert the row, then `redirect(url_for("profile"))` with a `flash("Expense added.", "success")`
- The `date` field should be pre-filled to today's date on `GET` using `datetime.today().strftime('%Y-%m-%d')`
- The navbar "Add Expense" link (if present in `base.html`) should only be shown to logged-in users

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] `GET /expenses/add` renders a form with amount, category, date, and description fields
- [ ] The date field defaults to today's date on initial load
- [ ] Submitting valid data inserts a row in the `expenses` table and redirects to `/profile` with a success flash
- [ ] The new expense appears in the profile page expense table immediately after submission
- [ ] Submitting with a missing or zero/negative amount shows an inline error and re-populates the other fields
- [ ] Submitting with an invalid date string shows an inline error and re-populates the other fields
- [ ] Submitting with a category not in the allowed list is rejected with an error
- [ ] The form re-populates submitted values (amount, category, date, description) on validation failure
- [ ] No expense row is inserted when validation fails
- [ ] Expenses added by one user are not visible to another user on their profile page
