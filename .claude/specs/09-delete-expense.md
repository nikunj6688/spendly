# Spec: Delete Expense

## Overview
This step converts the `GET /expenses/<id>/delete` stub into a two-step delete
flow. Clicking a **Delete** link in the profile page expense table takes the user
to a confirmation page that shows the expense details and asks "Are you sure?"
Confirming submits a POST that deletes the row and redirects back to `/profile`
with a flash message. The two-step pattern prevents accidental deletions from a
misclick, and the POST-for-mutation rule means no expense can be deleted by
following a link alone.

## Depends on
- Step 1 — Database setup (`expenses` table with `id`, `user_id`)
- Step 3 — Login / Logout (session key `user_id`)
- Step 5 — Profile page (redirect target after deletion)
- Step 8 — Edit Expense (Actions column in the profile table already exists;
  this step adds the Delete link alongside Edit)

## Routes
- `GET /expenses/<int:id>/delete` — render confirmation page for expense `id` — logged-in only
- `POST /expenses/<int:id>/delete` — delete the expense row and redirect to `/profile` — logged-in only

## Database changes
No database changes. Deletion uses the existing `expenses` table.

## Templates
- **Create:** `templates/delete_expense.html`
  - Extends `base.html`
  - Shows the expense details (date, category, amount, description) so the user
    knows exactly what they are deleting
  - "Yes, delete" button — a `<form method="POST">` that submits to
    `POST /expenses/<id>/delete`
  - "Cancel" link back to `/profile`

- **Modify:** `templates/profile.html`
  - Add a **Delete** link in the existing `col-actions` cell, next to the Edit link:
    `<a href="{{ url_for('delete_expense', id=e.id) }}" class="btn-delete">Delete</a>`

## Files to change
- `app.py` — replace `delete_expense()` stub with a GET/POST handler
- `templates/profile.html` — add Delete link in the Actions column
- `static/css/style.css` — add `.btn-delete` and `.btn-delete:hover` rules in the
  profile/expenses section (same location as `.btn-edit`)

## Files to create
- `templates/delete_expense.html` — confirmation page

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL via `get_db()` only
- Parameterised queries only — no f-strings or `%` formatting in SQL
- Passwords hashed with `werkzeug` — do not touch auth logic
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Vanilla JS only — no frameworks
- Unauthenticated GET and POST must both redirect to `/login`
- Ownership check: fetch the expense by `id`; if not found or
  `expense["user_id"] != session["user_id"]`, return 404 (same pattern as edit)
- The actual `DELETE FROM` SQL must only run on `POST`, never on `GET`
- The `DELETE` query must include `AND user_id = ?` as a defense-in-depth safeguard
- On successful POST deletion: `flash("Expense deleted.", "success")` then
  `redirect(url_for("profile"))`
- `.btn-delete` must use `--danger` / `--danger-light` CSS variables (not hardcoded red)

## Definition of done
- [ ] Visiting `/expenses/<id>/delete` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/delete` for an expense belonging to another user returns 404
- [ ] Visiting `/expenses/<id>/delete` for a non-existent `id` returns 404
- [ ] `GET /expenses/<id>/delete` renders the confirmation page showing the expense's date, category, amount, and description
- [ ] The confirmation page has a "Yes, delete" submit button and a "Cancel" link back to `/profile`
- [ ] Submitting the confirmation form deletes the row and redirects to `/profile` with a "Expense deleted." flash
- [ ] The deleted expense no longer appears in the profile table after deletion
- [ ] The profile page Actions column now shows both Edit and Delete links per row
- [ ] A GET request to `/expenses/<id>/delete` does NOT delete any data
- [ ] No other user's expenses are affected by the deletion
