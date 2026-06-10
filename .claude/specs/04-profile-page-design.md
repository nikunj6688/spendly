# Spec: Profile Page Design

## Overview
Implement the `/profile` route as a fully designed, logged-in-only page that
displays the current user's account information — name, email, and member since
date. This step turns the stub route into a real page, establishes the
login-required guard pattern that later steps (add/edit/delete expense) will
reuse, and gives the user a place to see their account details within the
Spendly UI.

## Depends on
- Step 1 — Database setup (`users` table with `name`, `email`, `created_at`)
- Step 2 — Registration (user record exists in DB)
- Step 3 — Login and Logout (session keys `user_id` / `user_name` set on login)

## Routes
- `GET /profile` — Show profile page with user details — logged-in only (redirect to `/login` if not authenticated)

## Database changes
No database changes.

## Templates
- **Create:** `templates/profile.html`
  - Extends `base.html`
  - Displays: full name, email address, member since date (formatted)
  - Includes a logout button/link

## Files to change
- `app.py` — implement the `profile()` view: add login guard, query the `users`
  table by `session['user_id']`, pass user data to the template

## Files to create
- `templates/profile.html` — profile page template

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL via `get_db()` only
- Parameterised queries only — no f-strings or `%` formatting in SQL
- Passwords hashed with werkzeug (no changes needed here)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Vanilla JS only — no frameworks
- If the user is not logged in (`session.get('user_id')` is falsy), redirect to `/login`
- Query the `users` table for the full user row (do not rely solely on session data)
- Format `created_at` as a human-readable date (e.g. "January 5, 2026") in the route before passing to the template
- Do not expose `password_hash` to the template

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` while logged in renders the profile page (HTTP 200)
- [ ] The page displays the logged-in user's full name
- [ ] The page displays the logged-in user's email address
- [ ] The page displays a formatted "Member since" date
- [ ] The page has a working logout link
- [ ] The navbar shows the user's name (inherited from `base.html`)
- [ ] No raw `password_hash` value is visible anywhere on the page or in the HTML source
