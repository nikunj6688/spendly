"""
tests/test_07-add-expense.py

Tests for the Add Expense feature (Step 07).

Spec: .claude/specs/07-add-expense.md

Coverage:
- Auth guard: GET /expenses/add while logged out redirects to /login
- Auth guard: POST /expenses/add while logged out redirects to /login
- GET renders form with all four fields (amount, category, date, description)
- GET date field defaults to today's date
- GET form contains all seven allowed category options
- Valid POST inserts a row in the expenses table and redirects to /profile with flash
- DB side effect: the new expense row exists immediately after submission
- Submitting missing/zero/negative/non-numeric amount shows inline error, no row inserted
- Submitting invalid date string shows inline error, no row inserted
- Submitting invalid category shows inline error, no row inserted
- Form values are re-populated on validation failure
- Expenses added by one user are not visible to another user (data isolation)
"""

import pytest
from datetime import datetime
from werkzeug.security import generate_password_hash
from app import app as flask_app
from database.db import init_db


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app(tmp_path):
    """Isolated Flask app backed by a temporary SQLite file, fresh per test."""
    db_file = str(tmp_path / "test_spendly.db")
    flask_app.config.update({
        'TESTING': True,
        'SECRET_KEY': 'test-secret',
        'WTF_CSRF_ENABLED': False,
    })

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


def _register_and_login(client, name='Test User', email='test@spendly.com',
                        password='testpass123'):
    """Helper: register then log in via POST, return the same client."""
    client.post('/register', data={'name': name, 'email': email, 'password': password})
    client.post('/login', data={'email': email, 'password': password})
    return client


def _get_user_id(app, email):
    """Helper: look up a user id by email."""
    import database.db as db_module
    conn = db_module.get_db()
    row = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    return row['id']


def _count_expenses(app, user_id=None):
    """Helper: count expense rows (optionally filtered by user_id)."""
    import database.db as db_module
    conn = db_module.get_db()
    if user_id is None:
        count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    else:
        count = conn.execute(
            "SELECT COUNT(*) FROM expenses WHERE user_id = ?", (user_id,)
        ).fetchone()[0]
    conn.close()
    return count


@pytest.fixture
def auth_client(client):
    """A test client that is already logged in as 'testuser'."""
    _register_and_login(client)
    return client


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------

class TestAuthGuard:
    def test_get_add_expense_logged_out_redirects_to_login(self, client):
        response = client.get('/expenses/add')
        assert response.status_code == 302, (
            'GET /expenses/add while logged out must return 302'
        )
        assert '/login' in response.headers['Location'], (
            'Redirect target must be /login'
        )

    def test_get_add_expense_logged_out_follows_redirect_to_login_page(self, client):
        response = client.get('/expenses/add', follow_redirects=True)
        assert response.status_code == 200
        assert b'Login' in response.data or b'login' in response.data, (
            'Following the redirect should land on the login page'
        )

    def test_post_add_expense_logged_out_redirects_to_login(self, client):
        response = client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Food',
            'date': '2026-06-01',
            'description': 'Lunch',
        })
        assert response.status_code == 302, (
            'POST /expenses/add while logged out must return 302'
        )
        assert '/login' in response.headers['Location'], (
            'POST redirect target must be /login'
        )

    def test_post_add_expense_logged_out_inserts_no_row(self, client, app):
        client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Food',
            'date': '2026-06-01',
            'description': 'Lunch',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when the user is not logged in'
        )


# ---------------------------------------------------------------------------
# GET /expenses/add — form rendering
# ---------------------------------------------------------------------------

class TestGetFormRendering:
    def test_get_returns_200_when_logged_in(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert response.status_code == 200, (
            'GET /expenses/add must return 200 for a logged-in user'
        )

    def test_get_form_contains_amount_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'name="amount"' in response.data, (
            'Form must contain an amount input'
        )

    def test_get_form_contains_category_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'name="category"' in response.data, (
            'Form must contain a category select/input'
        )

    def test_get_form_contains_date_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'name="date"' in response.data, (
            'Form must contain a date input'
        )

    def test_get_form_contains_description_field(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'name="description"' in response.data, (
            'Form must contain a description input'
        )

    def test_get_form_contains_submit_button(self, auth_client):
        response = auth_client.get('/expenses/add')
        assert b'Add Expense' in response.data, (
            'Form must contain a submit button labelled "Add Expense"'
        )

    def test_get_form_method_is_post(self, auth_client):
        response = auth_client.get('/expenses/add')
        data = response.data.decode()
        assert 'method="post"' in data or 'method="POST"' in data, (
            'The form must use the POST method'
        )

    def test_get_form_action_points_to_add_expense(self, auth_client):
        response = auth_client.get('/expenses/add')
        data = response.data.decode()
        assert 'action="/expenses/add"' in data or "action='/expenses/add'" in data, (
            'Form action must be /expenses/add'
        )

    def test_get_form_cancel_link_points_to_profile(self, auth_client):
        response = auth_client.get('/expenses/add')
        data = response.data.decode()
        assert '/profile' in data, (
            'A cancel link back to /profile must be present on the form'
        )

    def test_get_form_extends_base_html(self, auth_client):
        """Template must extend base.html — confirmed by navbar/footer landmarks."""
        response = auth_client.get('/expenses/add')
        data = response.data.decode()
        assert (
            '/login' in data or '/register' in data or
            'Terms' in data or 'Privacy' in data
        ), 'Page must extend base.html (navbar or footer landmarks missing)'


# ---------------------------------------------------------------------------
# GET — default date and category options
# ---------------------------------------------------------------------------

class TestGetFormDefaults:
    def test_date_field_defaults_to_today(self, auth_client):
        today = datetime.today().strftime('%Y-%m-%d')
        response = auth_client.get('/expenses/add')
        data = response.data.decode()
        assert today in data, (
            f'The date field must default to today ({today})'
        )

    def test_all_seven_category_options_present(self, auth_client):
        response = auth_client.get('/expenses/add')
        data = response.data
        for cat in [b'Food', b'Transport', b'Bills', b'Health',
                    b'Entertainment', b'Shopping', b'Other']:
            assert cat in data, f'Category option "{cat.decode()}" must be present in the form'


# ---------------------------------------------------------------------------
# POST — happy path (valid submission)
# ---------------------------------------------------------------------------

class TestValidPost:
    def test_valid_post_redirects_to_profile(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '42.50',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Lunch at work',
        })
        assert response.status_code == 302, (
            'Valid POST must redirect (302)'
        )
        assert '/profile' in response.headers['Location'], (
            'Redirect target after valid submission must be /profile'
        )

    def test_valid_post_shows_success_flash_after_redirect(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '42.50',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Lunch at work',
        }, follow_redirects=True)
        assert response.status_code == 200
        assert b'Expense added.' in response.data, (
            'Flash message "Expense added." must appear after a successful submission'
        )

    def test_valid_post_inserts_one_row_in_db(self, auth_client, app):
        before = _count_expenses(app)
        auth_client.post('/expenses/add', data={
            'amount': '15.00',
            'category': 'Transport',
            'date': '2026-06-15',
            'description': 'Bus ticket',
        })
        after = _count_expenses(app)
        assert after == before + 1, (
            'Exactly one expense row must be inserted after a valid submission'
        )

    def test_valid_post_stores_correct_amount(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '99.99',
            'category': 'Shopping',
            'date': '2026-06-20',
            'description': 'Books',
        })
        import database.db as db_module
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT amount FROM expenses WHERE description = ?", ('Books',)
        ).fetchone()
        conn.close()
        assert row is not None, 'Inserted expense must be found in the DB'
        assert abs(row['amount'] - 99.99) < 0.001, (
            f'Stored amount must be 99.99, got {row["amount"]}'
        )

    def test_valid_post_stores_correct_category(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '25.00',
            'category': 'Health',
            'date': '2026-06-21',
            'description': 'Vitamins',
        })
        import database.db as db_module
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT category FROM expenses WHERE description = ?", ('Vitamins',)
        ).fetchone()
        conn.close()
        assert row is not None, 'Inserted expense must be found in the DB'
        assert row['category'] == 'Health', (
            f'Stored category must be "Health", got "{row["category"]}"'
        )

    def test_valid_post_stores_correct_date(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '5.00',
            'category': 'Other',
            'date': '2026-06-22',
            'description': 'TestDateRow',
        })
        import database.db as db_module
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT date FROM expenses WHERE description = ?", ('TestDateRow',)
        ).fetchone()
        conn.close()
        assert row is not None, 'Inserted expense must be found in the DB'
        assert row['date'] == '2026-06-22', (
            f'Stored date must be "2026-06-22", got "{row["date"]}"'
        )

    def test_valid_post_stores_description(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '7.50',
            'category': 'Entertainment',
            'date': '2026-06-18',
            'description': 'Cinema night out',
        })
        import database.db as db_module
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT description FROM expenses WHERE description = ?",
            ('Cinema night out',)
        ).fetchone()
        conn.close()
        assert row is not None, 'Expense with the submitted description must be in the DB'

    def test_valid_post_optional_description_empty_string_accepted(self, auth_client, app):
        """description is optional — an empty string must be accepted and stored."""
        response = auth_client.post('/expenses/add', data={
            'amount': '3.00',
            'category': 'Food',
            'date': '2026-06-01',
            'description': '',
        })
        assert response.status_code == 302, (
            'Empty description must still be accepted and result in a redirect'
        )
        assert _count_expenses(app) == 1, (
            'One row must be inserted even when description is empty'
        )

    def test_valid_post_stores_correct_user_id(self, auth_client, app):
        """The inserted row must belong to the logged-in user."""
        user_id = _get_user_id(app, 'test@spendly.com')
        auth_client.post('/expenses/add', data={
            'amount': '20.00',
            'category': 'Bills',
            'date': '2026-06-05',
            'description': 'UserIdCheck',
        })
        import database.db as db_module
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT user_id FROM expenses WHERE description = ?", ('UserIdCheck',)
        ).fetchone()
        conn.close()
        assert row is not None, 'Inserted row must be found in the DB'
        assert row['user_id'] == user_id, (
            f'Row must belong to user {user_id}, got user_id={row["user_id"]}'
        )

    def test_valid_post_expense_appears_on_profile_page(self, auth_client):
        """After submission, the expense description should appear on the profile page."""
        auth_client.post('/expenses/add', data={
            'amount': '11.11',
            'category': 'Food',
            'date': '2026-06-12',
            'description': 'UniqueProfileCheck',
        })
        response = auth_client.get('/profile')
        assert b'UniqueProfileCheck' in response.data, (
            'Newly added expense must appear on the profile page immediately'
        )


# ---------------------------------------------------------------------------
# POST — amount validation errors
# ---------------------------------------------------------------------------

class TestAmountValidation:
    def test_missing_amount_shows_error(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert response.status_code == 200, (
            'Missing amount must re-render the form (200), not redirect'
        )
        assert b'error' in response.data.lower() or b'Error' in response.data or \
               b'Amount' in response.data, (
            'An error message about the amount must be displayed'
        )

    def test_missing_amount_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when amount is missing'
        )

    def test_zero_amount_shows_error(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert response.status_code == 200, (
            'Zero amount must re-render the form (200)'
        )

    def test_zero_amount_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when amount is zero'
        )

    def test_negative_amount_shows_error(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '-5.00',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert response.status_code == 200, (
            'Negative amount must re-render the form (200)'
        )

    def test_negative_amount_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '-5.00',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when amount is negative'
        )

    def test_non_numeric_amount_shows_error(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert response.status_code == 200, (
            'Non-numeric amount must re-render the form (200)'
        )

    def test_non_numeric_amount_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': 'abc',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when amount is non-numeric'
        )

    @pytest.mark.parametrize('bad_amount', [
        '',        # missing
        '0',       # zero
        '0.00',    # zero as float string
        '-1',      # negative integer
        '-0.01',   # tiny negative
        'abc',     # letters
        '1e999',   # overflow (may raise ValueError in float())
        'none',    # word
        '10.00.00',  # malformed float
    ])
    def test_parametrized_invalid_amounts_no_row_inserted(
            self, auth_client, app, bad_amount):
        auth_client.post('/expenses/add', data={
            'amount': bad_amount,
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'ParamTest',
        })
        assert _count_expenses(app) == 0, (
            f'No row must be inserted for invalid amount: {bad_amount!r}'
        )


# ---------------------------------------------------------------------------
# POST — date validation errors
# ---------------------------------------------------------------------------

class TestDateValidation:
    def test_invalid_date_format_shows_error(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Food',
            'date': '15-06-2026',   # DD-MM-YYYY — wrong format
            'description': 'Test',
        })
        assert response.status_code == 200, (
            'Invalid date format must re-render the form (200)'
        )

    def test_invalid_date_format_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Food',
            'date': '15-06-2026',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when date format is invalid'
        )

    def test_missing_date_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Food',
            'date': '',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when date is missing'
        )

    @pytest.mark.parametrize('bad_date', [
        '',              # missing
        'abc',           # letters
        '2026/06/10',    # wrong separator
        '10-06-2026',    # DD-MM-YYYY
        '2026-13-01',    # month 13 out of range
        '2026-00-10',    # month 00 out of range
        '2026-06-32',    # day 32 out of range
        'June 10, 2026', # natural language
        '20260610',      # no separators
    ])
    def test_parametrized_invalid_dates_no_row_inserted(
            self, auth_client, app, bad_date):
        auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Food',
            'date': bad_date,
            'description': 'DateParamTest',
        })
        assert _count_expenses(app) == 0, (
            f'No row must be inserted for invalid date: {bad_date!r}'
        )

    @pytest.mark.parametrize('bad_date', [
        '',
        'abc',
        '2026/06/10',
        '10-06-2026',
        '2026-13-01',
    ])
    def test_parametrized_invalid_dates_return_200(
            self, auth_client, bad_date):
        response = auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Food',
            'date': bad_date,
            'description': 'DateParamTest',
        })
        assert response.status_code == 200, (
            f'Invalid date {bad_date!r} must re-render the form, not redirect'
        )


# ---------------------------------------------------------------------------
# POST — category validation errors
# ---------------------------------------------------------------------------

class TestCategoryValidation:
    def test_invalid_category_shows_error(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Gambling',   # not in the allowed list
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert response.status_code == 200, (
            'Invalid category must re-render the form (200)'
        )

    def test_invalid_category_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Gambling',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when category is not in the allowed list'
        )

    def test_empty_category_inserts_no_row(self, auth_client, app):
        auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': '',
            'date': '2026-06-10',
            'description': 'Test',
        })
        assert _count_expenses(app) == 0, (
            'No expense row must be inserted when category is empty'
        )

    @pytest.mark.parametrize('bad_category', [
        '',
        'Gambling',
        'food',          # lowercase — must be rejected (exact match required)
        'FOOD',          # uppercase
        'food ',         # trailing space
        '<script>',      # injection attempt
        'random',
    ])
    def test_parametrized_invalid_categories_no_row_inserted(
            self, auth_client, app, bad_category):
        auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': bad_category,
            'date': '2026-06-10',
            'description': 'CatParamTest',
        })
        assert _count_expenses(app) == 0, (
            f'No row must be inserted for invalid category: {bad_category!r}'
        )


# ---------------------------------------------------------------------------
# POST — form re-population on validation failure
# ---------------------------------------------------------------------------

class TestFormRepopulationOnError:
    def test_amount_repopulated_after_invalid_category(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '77.77',
            'category': 'INVALID',
            'date': '2026-06-10',
            'description': 'My lunch',
        })
        assert b'77.77' in response.data, (
            'Submitted amount must be re-populated in the form on validation failure'
        )

    def test_date_repopulated_after_invalid_amount(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '-999',
            'category': 'Food',
            'date': '2026-06-22',
            'description': 'Coffee',
        })
        assert b'2026-06-22' in response.data, (
            'Submitted date must be re-populated in the form on validation failure'
        )

    def test_description_repopulated_after_invalid_amount(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': 'bad',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'My unique description',
        })
        assert b'My unique description' in response.data, (
            'Submitted description must be re-populated in the form on validation failure'
        )

    def test_category_repopulated_after_invalid_date(self, auth_client):
        response = auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Health',
            'date': 'not-a-date',
            'description': 'Vitamins',
        })
        assert b'Health' in response.data, (
            'Submitted category must be present in the re-rendered form on validation failure'
        )

    def test_all_four_fields_repopulated_after_invalid_date(self, auth_client):
        """All four submitted values must survive a date-validation failure."""
        response = auth_client.post('/expenses/add', data={
            'amount': '55.55',
            'category': 'Shopping',
            'date': 'wrong-date',
            'description': 'New shoes',
        })
        data = response.data
        assert b'55.55' in data, 'amount must be re-populated'
        assert b'Shopping' in data, 'category must be re-populated'
        assert b'wrong-date' in data, 'submitted date value must be re-populated'
        assert b'New shoes' in data, 'description must be re-populated'

    def test_error_message_present_on_validation_failure(self, auth_client):
        """An inline error message must appear on the re-rendered form."""
        response = auth_client.post('/expenses/add', data={
            'amount': '0',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'Zero amount',
        })
        # The spec says "Display an inline error message when validation fails"
        data = response.data.decode()
        has_error = (
            'error' in data.lower() or
            'Error' in data or
            'invalid' in data.lower() or
            'must be' in data.lower()
        )
        assert has_error, (
            'An inline error message must be rendered when validation fails'
        )


# ---------------------------------------------------------------------------
# Data isolation — expenses added by one user not visible to another
# ---------------------------------------------------------------------------

class TestDataIsolation:
    def test_expense_added_by_user_a_not_visible_to_user_b(self, client, app):
        """User A's expense must never appear on User B's profile."""
        # Register and log in as User A, add an expense
        _register_and_login(client, name='User A', email='usera@spendly.com',
                            password='passA123')
        client.post('/expenses/add', data={
            'amount': '88.88',
            'category': 'Food',
            'date': '2026-06-10',
            'description': 'UserASecretExpense',
        })
        client.get('/logout')

        # Register and log in as User B
        client.post('/register', data={
            'name': 'User B',
            'email': 'userb@spendly.com',
            'password': 'passB123',
        })
        client.post('/login', data={
            'email': 'userb@spendly.com',
            'password': 'passB123',
        })

        response = client.get('/profile')
        assert b'UserASecretExpense' not in response.data, (
            "User A's expense description must not appear on User B's profile"
        )
        assert b'88.88' not in response.data, (
            "User A's expense amount must not appear on User B's profile"
        )

    def test_user_b_expense_not_visible_after_login_as_user_a(self, client, app):
        """After switching sessions, a user only sees their own expenses."""
        # Register User A (no expenses)
        client.post('/register', data={
            'name': 'UserAlpha',
            'email': 'alpha@spendly.com',
            'password': 'alphapass',
        })

        # Register and log in as User B, add an expense
        _register_and_login(client, name='User B', email='beta@spendly.com',
                            password='betapass')
        client.post('/expenses/add', data={
            'amount': '123.45',
            'category': 'Bills',
            'date': '2026-06-15',
            'description': 'BetaOnlyExpense',
        })
        client.get('/logout')

        # Log in as User A and check their profile
        client.post('/login', data={
            'email': 'alpha@spendly.com',
            'password': 'alphapass',
        })
        response = client.get('/profile')
        assert b'BetaOnlyExpense' not in response.data, (
            "User B's expense must not appear on User A's profile"
        )

    def test_each_user_sees_only_own_expenses_on_add(self, client, app):
        """The inserted row's user_id must match the logged-in user's id."""
        _register_and_login(client, name='Owner', email='owner@spendly.com',
                            password='ownerpass')
        owner_id = _get_user_id(app, 'owner@spendly.com')

        client.post('/expenses/add', data={
            'amount': '9.99',
            'category': 'Other',
            'date': '2026-06-01',
            'description': 'OwnerExpense',
        })

        import database.db as db_module
        conn = db_module.get_db()
        row = conn.execute(
            "SELECT user_id FROM expenses WHERE description = ?",
            ('OwnerExpense',)
        ).fetchone()
        conn.close()

        assert row is not None, 'Expense must exist in the DB'
        assert row['user_id'] == owner_id, (
            f'Expense user_id {row["user_id"]} must equal the logged-in user id {owner_id}'
        )

    def test_second_user_expense_directly_in_db_not_shown_to_first_user(
            self, auth_client, app):
        """Even when another user's expense is inserted directly, it stays hidden."""
        from werkzeug.security import generate_password_hash as gph
        import database.db as db_module

        conn = db_module.get_db()
        conn.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (?, ?, ?)",
            ('Intruder', 'intruder@spendly.com', gph('intruderpass'))
        )
        conn.commit()
        intruder_id = conn.execute(
            "SELECT id FROM users WHERE email = ?", ('intruder@spendly.com',)
        ).fetchone()['id']
        conn.execute(
            "INSERT INTO expenses (user_id, amount, category, date, description)"
            " VALUES (?, ?, ?, ?, ?)",
            (intruder_id, 777.77, 'Food', '2026-06-10', 'IntruderExpense')
        )
        conn.commit()
        conn.close()

        response = auth_client.get('/profile')
        assert b'IntruderExpense' not in response.data, (
            "Another user's expense inserted directly into DB must not appear on the "
            "logged-in user's profile"
        )
        assert b'777.77' not in response.data, (
            "Another user's amount must not appear on the logged-in user's profile"
        )


# ---------------------------------------------------------------------------
# SQL injection safety
# ---------------------------------------------------------------------------

class TestSqlInjectionSafety:
    def test_sql_injection_in_description_does_not_crash(self, auth_client, app):
        """A SQL injection attempt in description must be stored safely or rejected."""
        response = auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': 'Other',
            'date': '2026-06-10',
            'description': "'; DROP TABLE expenses; --",
        })
        # Either stored safely (redirect) or re-rendered (200) — must not crash (500)
        assert response.status_code in (200, 302), (
            'SQL injection in description must not cause a 500 error'
        )
        # If it redirected (stored), the expenses table must still exist
        if response.status_code == 302:
            import database.db as db_module
            conn = db_module.get_db()
            count = conn.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
            conn.close()
            assert count >= 1, 'expenses table must still exist after injection attempt'

    def test_sql_injection_in_category_is_rejected(self, auth_client, app):
        """An injected string in category is not in the allowed list and must be rejected."""
        auth_client.post('/expenses/add', data={
            'amount': '10.00',
            'category': "'; DROP TABLE expenses; --",
            'date': '2026-06-10',
            'description': 'InjectCat',
        })
        assert _count_expenses(app) == 0, (
            'SQL injection as category must be rejected (not in allowed list)'
        )
