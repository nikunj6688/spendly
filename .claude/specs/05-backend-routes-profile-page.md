# Spec: Backend Routes for Profile Page

## Overview
Extend the existing `/profile` page with the ability for logged-in users to
update their account details. This step adds a `POST /profile` route to handle
name and email updates, and a separate `POST /profile/change-password` route to
handle password changes. Both routes follow the login-required guard pattern
established in Step 4 and keep all logic in `app.py` with raw parameterised SQL.

## Depends on
- Step 1 — Database setup (`users` table with `name`, `email`, `password_hash`)
- Step 2 — Registration
- Step 3 — Login and Logout (session keys `user_id` / `user_name`)
- Step 4 — Profile page design (`GET /profile` route and `profile.html` template)

## Routes
- `POST /profile` — Handle profile update form (name, email) — logged-in only
- `POST /profile/change-password` — Handle password change form — logged-in only

## Database changes
No database changes. The existing `users` table (`name`, `email`, `password_hash`) already has everything needed.

## Templates
- **Modify:** `templates/profile.html`
  - Add an "Edit Profile" form (name + email fields, submit button) that POSTs to `/profile`
  - Add a "Change Password" form (current password, new password, confirm new password) that POSTs to `/profile/change-password`
  - Display a success or error flash message above the relevant form after submission

## Files to change
- `app.py` — add `POST /profile` and `POST /profile/change-password` route handlers
- `templates/profile.html` — add edit forms and flash message display

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL via `get_db()` only
- Parameterised queries only — no f-strings or `%` formatting in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`; verified with `check_password_hash`
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Vanilla JS only — no frameworks
- Both POST routes must check `session.get('user_id')`; redirect to `/login` if not set
- On email change, check for duplicate email before updating (exclude the current user's own row)
- On password change, verify the current password before accepting the new one
- On successful profile update, refresh `session['user_name']` if name changed
- After any successful POST, redirect back to `GET /profile` with a query-string flag (e.g. `?updated=1`) or use Flask's `flash()` to surface a success message — do not re-render on POST directly (PRG pattern)
- Validate that name and email are non-empty before updating
- New password and confirm-password must match before updating

## Definition of done
- [ ] `POST /profile` while logged out redirects to `/login`
- [ ] `POST /profile/change-password` while logged out redirects to `/login`
- [ ] Submitting valid name + email updates the `users` row in the DB
- [ ] After a successful profile update, the page reflects the new name and email
- [ ] Submitting a duplicate email (belonging to another user) shows an error and does not update
- [ ] Submitting an empty name or email shows an error and does not update
- [ ] Submitting the correct current password + matching new passwords updates `password_hash`
- [ ] Submitting the wrong current password shows an error and does not update
- [ ] Submitting mismatched new/confirm passwords shows an error and does not update
- [ ] After a name change, the navbar shows the updated name on the next page load
- [ ] No `password_hash` value is ever exposed in the template or HTML source
