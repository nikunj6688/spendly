# Spec: Date Filter for Profile Page

## Overview
Add a date-range filter to the profile page so logged-in users can view their
expenses scoped to a chosen period. The page will display a filterable expense
table alongside summary stats (total spent, number of transactions, top category)
for the selected range. Filters are submitted as query-string parameters so results
are bookmarkable and browser-back works correctly. This is the first step that
surfaces expense data to the user in a meaningful way, bridging the profile UI
completed in Steps 4–5 with the expense CRUD work starting in Step 7.

## Depends on
- Step 1 — Database setup (`expenses` table with `user_id`, `amount`, `category`, `date`)
- Step 3 — Login / Logout (session keys `user_id` / `user_name`)
- Step 4 — Profile page design (`GET /profile` route and `profile.html` template)
- Step 5 — Backend routes for profile page (profile route now handles GET/POST)

## Routes
- `GET /profile?from=YYYY-MM-DD&to=YYYY-MM-DD` — return profile page filtered by date range — logged-in only

No new routes. The existing `GET /profile` route is extended to accept optional
`from` and `to` query-string parameters.

## Database changes
No database changes. The `expenses` table already has `date TEXT NOT NULL` and
`user_id INTEGER NOT NULL REFERENCES users(id)`.

## Templates
- **Modify:** `templates/profile.html`
  - Add a date-filter form (two `<input type="date">` fields for "From" and "To",
    a "Filter" submit button, and a "Clear" link that resets to no filter) that
    submits via `GET` to `/profile`
  - Add an expenses summary strip: total spent, number of transactions, top category
    for the active filter period
  - Add an expenses table listing: date, category, description, amount — ordered by
    date descending; show "No expenses found." row when the result set is empty
  - Preserve the existing edit-profile and change-password forms unchanged

## Files to change
- `app.py` — extend the `GET` branch of the `profile()` view to read `from` and
  `to` query params, validate/sanitise them, query the `expenses` table with
  parameterised SQL, and pass results + summary stats to the template
- `templates/profile.html` — add filter form, summary strip, and expense table
- `static/css/style.css` — add styles for filter form, summary strip, and expense table

## Files to create
No new files.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs — use raw SQL via `get_db()` only
- Parameterised queries only — no f-strings or `%` formatting in SQL
- Passwords hashed with `werkzeug` — do not touch auth logic
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Vanilla JS only — no frameworks
- Filter form must use `method="get"` so the URL reflects the active filter
- Date inputs must be validated server-side: if either value is not a valid
  `YYYY-MM-DD` string (use `datetime.strptime`), ignore that parameter and show
  a flash error
- If `from` > `to`, swap them silently before querying
- Default view (no query params) shows **all** expenses for the user, not an empty state
- Summary stats are calculated in Python from the query result, not with extra SQL queries
- Top category is the category with the highest total amount; if no expenses, show "—"
- Amount column must be formatted to 2 decimal places in the template (use `"%.2f" % amount`)
- The filter form must re-populate the date inputs with the currently active values
  so users can see what range they filtered by

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` with no query params shows all the logged-in user's expenses
- [ ] Submitting valid `from` and `to` dates shows only expenses within that range (inclusive)
- [ ] The summary strip shows correct total, count, and top category for the filtered set
- [ ] When no expenses match the filter, the table shows "No expenses found." and stats show 0 / "—"
- [ ] The date inputs are pre-filled with the active filter values after filtering
- [ ] Passing an invalid date string (e.g. `from=abc`) shows a flash error and falls back to all expenses
- [ ] If `from` > `to`, the query still returns correct results (values are swapped)
- [ ] Expenses from other users are never shown regardless of query params
- [ ] Clicking "Clear" removes the filter and shows all expenses again
- [ ] The existing edit-profile and change-password forms still work correctly
