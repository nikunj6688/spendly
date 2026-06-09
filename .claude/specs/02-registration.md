# Spec: Registration

## Overview
Complete the user registration flow for Spendly. The `POST /register` route skeleton exists in `app.py` and `register.html` is scaffolded, but several gaps remain: there is no confirm-password field or server-side length validation, the navbar always shows "Sign in / Get started" regardless of session state, logged-in users are not redirected away from the form, and a successful registration does not auto-login the user. This step closes all those gaps and makes registration fully functional end-to-end.

## Depends on
- Step 1 — Database setup (`users` table must exist via `init_db()`)

## Routes
- `GET /register` — Show registration form; redirect to `/` if already logged in — public
- `POST /register` — Validate inputs, insert user, auto-login, redirect to `/` — public

## Database changes
No database changes. The `users` table schema in `database/db.py` already has all required columns (`id`, `name`, `email`, `password_hash`, `created_at`).

## Templates
- **Modify:** `templates/register.html`
  - Add a confirm-password `<input>` field
  - Surface both field-level and general error messages
  - Preserve submitted `name` and `email` values on validation failure (sticky fields)
- **Modify:** `templates/base.html`
  - Navbar: when `session.user_id` is set, show the user's name and a "Sign out" link instead of "Sign in / Get started"

## Files to change
- `app.py` — complete `POST /register` logic (confirm-password check, min-length validation, auto-login, already-logged-in redirect)
- `templates/register.html` — add confirm-password field, sticky fields, error display
- `templates/base.html` — session-aware navbar

## Files to create
No new files.

## New dependencies
No new dependencies. `werkzeug.security.generate_password_hash` is already imported in `app.py`.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL via `get_db()` only
- Parameterised queries only — no f-strings or `%` formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`
- Minimum password length: 8 characters (enforced server-side; `minlength` attribute on the input is optional but not sufficient alone)
- Use CSS variables — never hardcode hex values in stylesheets
- All templates extend `base.html`
- Vanilla JS only — no frameworks
- After successful registration, set `session["user_id"]` and `session["user_name"]` then redirect to `/`
- If a logged-in user visits `GET /register`, redirect to `/`
- On validation failure, re-render `register.html` with the error message and the original `name` and `email` values passed back to the template

## Definition of done
- [ ] Visiting `/register` while logged in redirects to `/` without showing the form
- [ ] Submitting the form with any empty field shows "All fields are required." and re-renders the form
- [ ] Submitting a password shorter than 8 characters shows "Password must be at least 8 characters."
- [ ] Submitting mismatched passwords shows "Passwords do not match."
- [ ] Submitting a duplicate email shows "Email already registered."
- [ ] A valid submission inserts the user into the `users` table (verifiable via `/seed-user` or SQLite browser)
- [ ] After valid submission the user is immediately logged in and redirected to `/`
- [ ] The navbar on `/` shows the user's name and a "Sign out" link after registration
- [ ] Clicking "Sign out" clears the session and the navbar reverts to "Sign in / Get started"
- [ ] The `name` and `email` fields retain their submitted values when the form is re-rendered with an error
