# Spec: Login and Logout

## Overview
Complete the login and logout flow for Spendly. The `POST /login` route already
validates credentials and sets the session, and `GET /logout` already clears it.
What remains: the login page has no redirect guard for already-logged-in users,
the email field is not preserved on failed login attempts (sticky field), and
`login.html` has no `value` binding for the email input. This step closes those
gaps and makes the full auth cycle — register → login → logout → login again —
work end-to-end without UX gaps.

## Depends on
- Step 1 — Database setup (`users` table, `get_db()`)
- Step 2 — Registration (session keys `user_id` / `user_name` must be set on login)

## Routes
- `GET /login` — Show login form; redirect to `/` if already logged in — public
- `POST /login` — Validate credentials, set session, redirect to `/` — public
- `GET /logout` — Clear session, redirect to `/` — logged-in (no change needed; already works)

## Database changes
No database changes.

## Templates
- **Modify:** `templates/login.html`
  - Add `value="{{ email or '' }}"` to the email input (sticky field on error)

## Files to change
- `app.py` — add logged-in redirect guard to `GET /login`; pass `email` back on failed login
- `templates/login.html` — add sticky `value` attribute to the email input

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL via `get_db()` only
- Parameterised queries only — no f-strings or `%` formatting in SQL
- Passwords checked with `werkzeug.security.check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Vanilla JS only — no frameworks
- If a logged-in user visits `GET /login`, redirect to `/`
- On failed login, re-render `login.html` with the error and the submitted `email` value
- Password field is intentionally NOT sticky (security)
- The `logout` route requires no changes — `session.clear()` + redirect to `/` is correct

## Definition of done
- [ ] Visiting `/login` while already logged in redirects to `/`
- [ ] Submitting the login form with empty fields shows "Invalid email or password."
- [ ] Submitting a wrong password shows "Invalid email or password."
- [ ] Submitting a correct email + password sets the session and redirects to `/`
- [ ] After login the navbar shows the user's name and a "Sign out" / "Logout" link
- [ ] Clicking logout clears the session; navbar reverts to "Sign in / Get started"
- [ ] After logout, visiting `/login` shows the form (not a redirect)
- [ ] On a failed login attempt the email field retains the submitted value
