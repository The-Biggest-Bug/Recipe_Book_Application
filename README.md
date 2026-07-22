# Recipe Book Application

## Features:
- Search for recipes by name or ingredients using TheMealDB.
- Browse recipes by category or cuisine.
- Create a user account, log in, and log out.
- Save recipes to a personal favorites list, including directly from any recipe list.
- Track ingredient search history for each logged-in user.
- View a user profile with account stats.
- Change account password.
- Browse random new recipe suggestions.

## How to use:
### 1. Clone Repo: `git clone <repo link>`
### 2. Install dependencies: `pip install -r requirements.txt`
### 3. Configure environment variables:
- Copy `.env.example` to `.env`.
- Set `FLASK_DEBUG=1` for local development (this also allows the app to fall
  back to an insecure development `SECRET_KEY`).
- For anything other than local development, set a real `SECRET_KEY` instead
  (generate one with `python -c "import secrets; print(secrets.token_hex(32))"`).
  The app will refuse to start without one.
### 4a. If using VSCode, press the run button
### 4b. If using command line, type `flask run` within your terminal

## Running tests
```
pytest
```
Tests use a temporary SQLite database per test and never call the real
TheMealDB API (network calls are mocked).

## Project Structure:
- `app.py` contains the Flask routes.
- `database.py` contains SQLite setup and database helper functions.
- `mealdb.py` contains TheMealDB API helper functions (with response caching
  and retry/backoff).
- `templates/` contains the HTML pages.
- `static/style.css` contains the app styling.
- `tests/` contains the pytest test suite.
<hr>

# Branching Strategy

### For the branching stretegy, our team will firstly announce and discuss which feature needs a branch, name the branch to coorespond to that particular feature, and then after a PR is instantiated and verified by one developer the branch being merged will be able to merge successfully. While this process may seem simple on the outside, it is sure to cause some issues within development, as there are always roadblocks during the process. If any obstacles do come our way then we will mitigate them by: establishing specific times for repo pulls, verifying PR's, and discussing development plans with scrum meetings. 
