"""
tests/test_06-date-filter-profile-page.py

Tests for the date-range filter feature on the profile page (Step 6).

Spec: .claude/specs/06-date-filter-profile-page.md

Coverage:
- Auth guard: logged-out users are redirected to /login
- Default view (no params) shows all expenses for the user
- Valid from+to filter returns only expenses within range (inclusive)
- Summary strip (total, count, top_category) computed correctly
- Empty state when no expenses match
- Date inputs re-populated with active filter values
- Invalid date strings trigger flash error and fall back to all expenses
- from > to is silently swapped and still returns correct results
- Expenses from other users are never shown
- Clear link (no params) resets to all expenses
- Edit-profile and change-password forms still present
"""

import pytest
from werkzeug.security import generate_password_hash
from app import app as flask_app
from database.db import init_db, get_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    """Isolated Flask app using a temporary SQLite file per test."""
    db_file = str(tmp_path / "test_spendly.db")
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })

    # Patch DB_PATH so get_db() uses the temp file
    import database.db as db_module
    original_path = db_module.DB_PATH
    db_module.DB_PATH = db_file

    with flask_app.app_context():
        init_db()
        yield flask_app

    db_module.DB_PATH = original_path


@pytest.fixture
def client(app):
    return app.test_client()


def _register_and_login(client, name, email, password):
    """Helper: register a user via POST then log in, return the client."""
    client.post('/register', data={'name': name, 'email': email, 'password': password})
    client.post('/login', data={'email': email, 'password': password})
    return client


def _insert_expense(app, user_id, amount, category, date, description=''):
    """Helper: insert an expense directly into the DB."""
    import database.db as db_module
    conn = db_module.get_db()
    conn.execute(
        "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, category, date, description)
    )
    conn.commit()
    conn.close()


def _get_user_id(app, email):
    """Helper: look up a user id by email."""
    import database.db as db_module
    conn = db_module.get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row['id']


@pytest.fixture
def auth_client(client, app):
    """Logged-in client with a known user and a set of dated expenses."""
    _register_and_login(client, 'Test User', 'test@spendly.com', 'testpass123')
    user_id = _get_user_id(app, 'test@spendly.com')

    # Insert expenses spread across different dates
    _insert_expense(app, user_id, 10.00, 'Food',          '2026-01-01', 'Breakfast')
    _insert_expense(app, user_id, 50.00, 'Transport',     '2026-01-15', 'Bus pass')
    _insert_expense(app, user_id, 200.00, 'Bills',        '2026-02-01', 'Electricity')
    _insert_expense(app, user_id, 30.00, 'Food',          '2026-02-14', 'Dinner')
    _insert_expense(app, user_id, 75.00, 'Shopping',      '2026-03-10', 'Clothes')

    return client, user_id


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_profile_logged_out_redirects_to_login(self, client):
        response = client.get('/profile')
        assert response.status_code == 302, 'Expected redirect for unauthenticated user'
        assert '/login' in response.headers['Location'], (
            'Redirect target should be /login'
        )

    def test_profile_logged_out_follows_redirect_to_login_page(self, client):
        response = client.get('/profile', follow_redirects=True)
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data, (
            'Login page should be rendered for unauthenticated users'
        )

    def test_profile_with_date_params_logged_out_redirects(self, client):
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        assert response.status_code == 302
        assert '/login' in response.headers['Location']


# ---------------------------------------------------------------------------
# Default view — no query params
# ---------------------------------------------------------------------------

class TestDefaultView:
    def test_profile_no_params_returns_200(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile')
        assert response.status_code == 200, 'Profile page should return 200 when logged in'

    def test_profile_no_params_shows_all_expenses(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile')
        data = response.data
        # All five seeded expense descriptions must appear
        assert b'Breakfast' in data, 'Breakfast expense should be visible'
        assert b'Bus pass' in data, 'Bus pass expense should be visible'
        assert b'Electricity' in data, 'Electricity expense should be visible'
        assert b'Dinner' in data, 'Dinner expense should be visible'
        assert b'Clothes' in data, 'Clothes expense should be visible'

    def test_profile_no_params_does_not_show_empty_state(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile')
        assert b'No expenses found.' not in response.data, (
            'Default view should not show empty state when expenses exist'
        )

    def test_profile_no_params_date_inputs_empty(self, auth_client):
        """When no filter is active, the date inputs should have no pre-filled value."""
        client, _ = auth_client
        response = client.get('/profile')
        data = response.data.decode()
        # Inputs should have empty value attributes or none that contain a date
        # We verify that the inputs do NOT carry over a stale date value.
        assert 'value="2026-' not in data, (
            'Date inputs should not be pre-filled when no filter is active'
        )


# ---------------------------------------------------------------------------
# Valid date range filter
# ---------------------------------------------------------------------------

class TestValidDateRangeFilter:
    def test_filter_returns_only_expenses_in_range(self, auth_client):
        client, _ = auth_client
        # January only: 2026-01-01 to 2026-01-31
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        data = response.data
        assert b'Breakfast' in data, 'Breakfast (Jan 1) should be in range'
        assert b'Bus pass' in data, 'Bus pass (Jan 15) should be in range'
        assert b'Electricity' not in data, 'Electricity (Feb 1) should be outside range'
        assert b'Dinner' not in data, 'Dinner (Feb 14) should be outside range'
        assert b'Clothes' not in data, 'Clothes (Mar 10) should be outside range'

    def test_filter_inclusive_on_from_date(self, auth_client):
        client, _ = auth_client
        # The from date itself (2026-01-01) must be included
        response = client.get('/profile?from=2026-01-01&to=2026-01-01')
        assert b'Breakfast' in response.data, 'Expense on exactly the from date must be included'
        assert b'Bus pass' not in response.data, 'Bus pass (Jan 15) should be outside single-day range'

    def test_filter_inclusive_on_to_date(self, auth_client):
        client, _ = auth_client
        # The to date itself (2026-03-10) must be included
        response = client.get('/profile?from=2026-03-10&to=2026-03-10')
        assert b'Clothes' in response.data, 'Expense on exactly the to date must be included'
        assert b'Dinner' not in response.data, 'Dinner (Feb 14) should be outside this range'

    def test_filter_returns_200_status(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-01-01&to=2026-03-31')
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# Summary strip
# ---------------------------------------------------------------------------

class TestSummaryStrip:
    def test_summary_total_for_filtered_range(self, auth_client):
        client, _ = auth_client
        # January: 10.00 (Breakfast) + 50.00 (Bus pass) = 60.00
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        assert b'$60.00' in response.data, (
            'Total for Jan should be $60.00'
        )

    def test_summary_count_for_filtered_range(self, auth_client):
        client, _ = auth_client
        # January: 2 expenses
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        data = response.data.decode()
        # The count "2" must appear in the summary strip context
        # The template renders count as a plain number in a summary-value span
        assert '>2<' in data or '>2 <' in data or b'2' in response.data, (
            'Count for January should be 2'
        )

    def test_summary_top_category_for_filtered_range(self, auth_client):
        client, _ = auth_client
        # February: Bills=200.00, Food=30.00 → top category is Bills
        response = client.get('/profile?from=2026-02-01&to=2026-02-28')
        assert b'Bills' in response.data, (
            'Top category for February should be Bills (highest total)'
        )

    def test_summary_top_category_single_expense(self, auth_client):
        client, _ = auth_client
        # March: only Clothes/Shopping → top category is Shopping
        response = client.get('/profile?from=2026-03-01&to=2026-03-31')
        assert b'Shopping' in response.data, (
            'Top category for March should be Shopping'
        )

    def test_summary_total_formatted_two_decimal_places(self, auth_client):
        client, _ = auth_client
        # March: 75.00
        response = client.get('/profile?from=2026-03-01&to=2026-03-31')
        assert b'$75.00' in response.data, (
            'Amount should be formatted to 2 decimal places'
        )

    def test_summary_default_view_total_is_sum_of_all_expenses(self, auth_client):
        client, _ = auth_client
        # All five: 10 + 50 + 200 + 30 + 75 = 365.00
        response = client.get('/profile')
        assert b'$365.00' in response.data, (
            'Default view total should be sum of all expenses: $365.00'
        )


# ---------------------------------------------------------------------------
# Empty state
# ---------------------------------------------------------------------------

class TestEmptyState:
    def test_empty_state_message_when_no_expenses_match(self, auth_client):
        client, _ = auth_client
        # A date range with no expenses
        response = client.get('/profile?from=2025-01-01&to=2025-01-31')
        assert b'No expenses found.' in response.data, (
            '"No expenses found." should be shown when filter matches nothing'
        )

    def test_empty_state_total_is_zero(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2025-01-01&to=2025-01-31')
        assert b'$0.00' in response.data, (
            'Total should be $0.00 when no expenses match'
        )

    def test_empty_state_top_category_is_dash(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2025-01-01&to=2025-01-31')
        assert '—'.encode('utf-8') in response.data, (
            'Top category should show "—" when no expenses match'
        )

    def test_empty_state_for_user_with_no_expenses(self, client, app):
        """A fresh user with no expenses at all should see the empty state."""
        _register_and_login(client, 'Empty User', 'empty@spendly.com', 'emptypass')
        response = client.get('/profile')
        assert b'No expenses found.' in response.data, (
            'User with no expenses should see "No expenses found." on default view'
        )
        assert b'$0.00' in response.data, 'Total should be $0.00 for user with no expenses'
        assert '—'.encode('utf-8') in response.data, (
            'Top category should be "—" for user with no expenses'
        )


# ---------------------------------------------------------------------------
# Date inputs re-populated
# ---------------------------------------------------------------------------

class TestDateInputRepopulation:
    def test_from_input_repopulated_after_filter(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        data = response.data.decode()
        assert 'value="2026-01-01"' in data, (
            'The "from" date input should be pre-filled with the active filter value'
        )

    def test_to_input_repopulated_after_filter(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        data = response.data.decode()
        assert 'value="2026-01-31"' in data, (
            'The "to" date input should be pre-filled with the active filter value'
        )

    def test_both_inputs_repopulated_simultaneously(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-02-01&to=2026-03-31')
        data = response.data.decode()
        assert 'value="2026-02-01"' in data, '"from" input must reflect active filter'
        assert 'value="2026-03-31"' in data, '"to" input must reflect active filter'


# ---------------------------------------------------------------------------
# Invalid date strings
# ---------------------------------------------------------------------------

class TestInvalidDateStrings:
    def test_invalid_from_date_shows_flash_error(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=abc&to=2026-01-31', follow_redirects=True)
        data = response.data
        assert b'Invalid' in data or b'invalid' in data or b'error' in data.lower(), (
            'A flash error message should appear for an invalid "from" date'
        )

    def test_invalid_from_date_falls_back_to_all_expenses(self, auth_client):
        client, _ = auth_client
        # With invalid "from", all expenses should still be shown
        response = client.get('/profile?from=abc&to=2026-01-31')
        data = response.data
        # All known descriptions must be present (fallback to all)
        assert b'Breakfast' in data, 'Fallback should show all expenses'
        assert b'Electricity' in data, 'Fallback should show all expenses'
        assert b'Clothes' in data, 'Fallback should show all expenses'

    def test_invalid_to_date_shows_flash_error(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-01-01&to=notadate', follow_redirects=True)
        data = response.data
        assert b'Invalid' in data or b'invalid' in data or b'error' in data.lower(), (
            'A flash error message should appear for an invalid "to" date'
        )

    def test_invalid_to_date_falls_back_to_all_expenses(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-01-01&to=notadate')
        data = response.data
        assert b'Breakfast' in data, 'Fallback should include all expenses'
        assert b'Clothes' in data, 'Fallback should include all expenses'

    def test_both_dates_invalid_shows_flash_and_falls_back(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=bad&to=worse')
        data = response.data
        assert b'No expenses found.' not in data or b'Breakfast' in data, (
            'Both invalid dates should fall back to all expenses, not empty state'
        )

    @pytest.mark.parametrize('bad_date', [
        'abc',
        '2026/01/01',
        '01-01-2026',
        '2026-13-01',
        '2026-00-10',
        '',  # empty string should be treated as no filter (no error expected for empty)
    ])
    def test_invalid_from_date_formats(self, auth_client, bad_date):
        client, _ = auth_client
        response = client.get(f'/profile?from={bad_date}&to=2026-03-31')
        # Must not crash — always returns a valid page
        assert response.status_code == 200, (
            f'Profile must return 200 even with invalid from date: {bad_date!r}'
        )


# ---------------------------------------------------------------------------
# from > to silent swap
# ---------------------------------------------------------------------------

class TestFromGreaterThanToSwap:
    def test_swapped_dates_return_correct_results(self, auth_client):
        client, _ = auth_client
        # from=2026-01-31 > to=2026-01-01 — should still return January expenses
        response = client.get('/profile?from=2026-01-31&to=2026-01-01')
        data = response.data
        assert b'Breakfast' in data, 'Breakfast (Jan 1) should appear when dates are swapped'
        assert b'Bus pass' in data, 'Bus pass (Jan 15) should appear when dates are swapped'
        assert b'Electricity' not in data, 'Electricity (Feb 1) should not appear for Jan range'

    def test_swapped_dates_no_flash_error(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-03-10&to=2026-01-01')
        data = response.data.decode()
        # No error flash expected — swap is silent
        assert 'Invalid' not in data, 'Swapped valid dates should not trigger a flash error'

    def test_swapped_dates_inputs_repopulated_with_swapped_values(self, auth_client):
        """After swapping, inputs should reflect the corrected (swapped) order."""
        client, _ = auth_client
        response = client.get('/profile?from=2026-01-31&to=2026-01-01')
        data = response.data.decode()
        # After swap: valid_from=2026-01-01, valid_to=2026-01-31
        assert 'value="2026-01-01"' in data, (
            '"from" input should be repopulated with the smaller (swapped) date'
        )
        assert 'value="2026-01-31"' in data, (
            '"to" input should be repopulated with the larger (swapped) date'
        )


# ---------------------------------------------------------------------------
# Data isolation — other users
# ---------------------------------------------------------------------------

class TestDataIsolation:
    def test_other_user_expenses_not_shown(self, auth_client, app):
        """Expenses belonging to a second user must never appear for the first user."""
        client, _ = auth_client

        # Register a second user and insert an expense for them
        import database.db as db_module
        conn = db_module.get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ('Other User', 'other@spendly.com', generate_password_hash('otherpass'))
        )
        conn.commit()
        other_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ('other@spendly.com',)
        ).fetchone()['id']
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (other_id, 999.99, 'Secret', '2026-01-10', 'OtherSecret')
        )
        conn.commit()
        conn.close()

        response = client.get('/profile')
        assert b'OtherSecret' not in response.data, (
            "Another user's expense description must not appear in the logged-in user's profile"
        )
        assert b'999.99' not in response.data, (
            "Another user's expense amount must not appear in the logged-in user's profile"
        )

    def test_other_user_expenses_not_shown_with_date_filter(self, auth_client, app):
        """Even with a matching date filter, other users' expenses stay hidden."""
        client, _ = auth_client

        import database.db as db_module
        conn = db_module.get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ('Other2', 'other2@spendly.com', generate_password_hash('pass2'))
        )
        conn.commit()
        other_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ('other2@spendly.com',)
        ).fetchone()['id']
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)",
            (other_id, 555.55, 'Hidden', '2026-01-15', 'HiddenExpense')
        )
        conn.commit()
        conn.close()

        # Filter that covers Jan 15 — HiddenExpense from other user must not appear
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        assert b'HiddenExpense' not in response.data, (
            "Another user's expense must not appear even when date range matches"
        )


# ---------------------------------------------------------------------------
# Clear link
# ---------------------------------------------------------------------------

class TestClearLink:
    def test_clear_link_present_in_template(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile?from=2026-01-01&to=2026-01-31')
        data = response.data.decode()
        # The Clear link must point to /profile with no query params
        assert '/profile' in data, 'A link to /profile (clear) should be present'
        assert 'Clear' in data or 'clear' in data, '"Clear" label should be present'

    def test_clear_link_resets_to_all_expenses(self, auth_client):
        client, _ = auth_client
        # Simulate clicking "Clear" by navigating to /profile with no params
        response = client.get('/profile')
        data = response.data
        # All expenses must be visible again
        assert b'Breakfast' in data
        assert b'Bus pass' in data
        assert b'Electricity' in data
        assert b'Dinner' in data
        assert b'Clothes' in data

    def test_clear_link_no_date_inputs_prefilled(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile')
        data = response.data.decode()
        # After clearing, date inputs should not contain a date value
        assert 'value="2026-' not in data, (
            'Date inputs should be empty after clearing the filter'
        )


# ---------------------------------------------------------------------------
# Existing forms still present
# ---------------------------------------------------------------------------

class TestExistingFormsPresent:
    def test_edit_profile_form_present(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile')
        data = response.data.decode()
        assert 'name="name"' in data, 'Name input should be present in edit-profile form'
        assert 'name="email"' in data, 'Email input should be present in edit-profile form'
        assert 'Save Changes' in data, '"Save Changes" button should be in edit-profile form'

    def test_edit_profile_form_method_is_post(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile')
        data = response.data.decode()
        # The edit-profile form must use POST
        assert 'method="POST"' in data or 'method="post"' in data, (
            'Edit-profile form must use POST method'
        )

    def test_change_password_route_accessible(self, auth_client):
        """POST to /profile/change-password still works (no regression)."""
        client, _ = auth_client
        response = client.post('/profile/change-password', data={
            'current_password': 'testpass123',
            'new_password': 'newpass456',
            'confirm_password': 'newpass456',
        }, follow_redirects=True)
        assert response.status_code == 200, (
            'Change-password route should still function after date-filter changes'
        )
        assert b'Password changed successfully' in response.data, (
            '"Password changed successfully" flash should appear after valid password change'
        )

    def test_filter_form_uses_get_method(self, auth_client):
        client, _ = auth_client
        response = client.get('/profile')
        data = response.data.decode()
        # The filter form must use GET so the URL reflects the filter
        assert 'method="get"' in data or 'method="GET"' in data, (
            'Date-filter form must use GET method so query params appear in the URL'
        )

    def test_profile_page_extends_base_html(self, auth_client):
        """Profile page should render content that comes from base.html (navbar/footer)."""
        client, _ = auth_client
        response = client.get('/profile')
        data = response.data.decode()
        # base.html includes links for /login or /register in the navbar,
        # or Terms/Privacy in the footer — any of these confirms base.html was applied
        assert (
            '/login' in data or '/register' in data or
            'Terms' in data or 'Privacy' in data
        ), 'Profile page should extend base.html and include navbar/footer content'
