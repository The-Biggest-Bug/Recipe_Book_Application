from functools import wraps
import os
import re
import secrets
import sqlite3
from authlib.integrations.flask_client import OAuth

from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash, generate_password_hash

from database import (
    add_favorite,
    add_search_history,
    clear_user_search_history,
    close_db,
    create_user,
    get_profile_counts,
    get_user_by_id,
    get_user_favorite_ids,
    get_user_favorites,
    get_user_for_login,
    get_user_search_history,
    init_database,
    is_recipe_favorite,
    remove_favorite,
    update_user_password,
    get_user_recipes,
    add_user_recipe,
    get_uploaded_recipe,
    search_user_recipes_by_name,
    search_user_recipes_by_ingredients
)
from mealdb import (
    MealDBError,
    get_areas,
    get_categories,
    get_default_recipes,
    get_random_recipes,
    get_recipe_by_id,
    get_recipe_ingredients,
    get_recipes_by_area,
    get_recipes_by_category,
    search_recipes_by_ingredients,
    search_recipes_by_name,
)


load_dotenv()

PASSWORD_MIN_LENGTH = 8
RESULTS_PER_PAGE = 12


def resolve_secret_key():
    secret_key = os.environ.get("SECRET_KEY")

    if secret_key:
        return secret_key

    if os.environ.get("FLASK_DEBUG", "").lower() in ("1", "true", "on"):
        return "recipe-book-development-key"

    raise RuntimeError(
        "SECRET_KEY environment variable must be set. "
        "Set FLASK_DEBUG=1 in your .env for local development to use an "
        "insecure fallback key instead."
    )


app = Flask(__name__)
app.secret_key = resolve_secret_key()

oauth = OAuth(app)

google = oauth.register(
    name="google",
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    server_metadata_url=(
        "https://accounts.google.com/.well-known/openid-configuration"
    ),
    client_kwargs={
        "scope": "openid email profile"
    },
)

app.teardown_appcontext(close_db)

csrf = CSRFProtect(app)
limiter = Limiter(get_remote_address, app=app, storage_uri="memory://", default_limits=[])


@app.errorhandler(CSRFError)
def handle_csrf_error(error):
    flash("Your session expired or the form was resubmitted. Please try again.")
    return redirect(request.referrer or url_for("home_page"))


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if session.get("user_id") is None:
            flash("Please log in to view this page.")
            return redirect(url_for("login_page", next=request.path))

        return view(*args, **kwargs)

    return wrapped_view


def get_current_user():
    user_id = session.get("user_id")

    if user_id is None:
        return None

    return get_user_by_id(user_id)


def get_current_favorite_ids():
    user_id = session.get("user_id")

    if user_id is None:
        return set()

    return get_user_favorite_ids(user_id)


@app.context_processor
def inject_current_user():
    return {"current_user": get_current_user()}


def is_safe_redirect(next_page):
    return next_page and next_page.startswith("/") and not next_page.startswith("//")


def get_search_type(raw_search_type):
    if raw_search_type in ("name", "ingredients"):
        return raw_search_type

    return "ingredients"


def get_password_error(password):
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters long."

    if not re.search(r"[a-zA-Z]", password):
        return "Password must include at least one letter."

    if not re.search(r"[0-9]", password):
        return "Password must include at least one number."

    return None


def paginate(items, page):
    total_pages = max((len(items) + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE, 1)
    page = min(max(page, 1), total_pages)
    start = (page - 1) * RESULTS_PER_PAGE

    return items[start:start + RESULTS_PER_PAGE], page, total_pages


@app.route("/", methods=["GET", "POST"])
def home_page():
    if request.method == "POST":
        search_text = request.form.get("search_text", "")
        search_type = get_search_type(request.form.get("search_type"))

        return redirect(
            url_for(
                "search_results_page",
                search_text=search_text,
                search_type=search_type
            )
        )

    try:
        recipes = get_default_recipes()
        api_error = False
    except MealDBError:
        recipes = []
        api_error = True

    return render_template(
        "index.html",
        recipes=recipes,
        search_text="",
        search_type="ingredients",
        searched=False,
        api_error=api_error,
        favorite_ids=get_current_favorite_ids()
    )

@app.get("/auth/google")
def google_login():
    redirect_uri = url_for("google_callback", _external=True)
    return google.authorize_redirect(redirect_uri)

@app.get("/auth/google/callback")
def google_callback():
    try:
        token = google.authorize_access_token()
        google_user = token.get("userinfo")
    except Exception:
        flash("Google sign-in failed. Please try again.")
        return redirect(url_for("login_page"))

    if not google_user or not google_user.get("email_verified"):
        flash("Google could not verify your email.")
        return redirect(url_for("login_page"))

    email = google_user["email"].lower()
    user = get_user_for_login(email)

    if user is None:
        base_username = re.sub(
            r"[^a-zA-Z0-9_]",
            "",
            email.split("@")[0]
        ) or "google_user"

        username = base_username
        number = 1

        while get_user_for_login(username) is not None:
            username = f"{base_username}{number}"
            number += 1

        random_password = secrets.token_urlsafe(32)

        try:
            create_user(
                username,
                email,
                generate_password_hash(random_password)
            )
        except sqlite3.IntegrityError:
            pass

        user = get_user_for_login(email)

    if user is None:
        flash("Your Google account could not be created.")
        return redirect(url_for("login_page"))

    session.clear()
    session["user_id"] = user["id"]
    session["username"] = user["username"]

    flash(f"Welcome, {user['username']}!")
    return redirect(url_for("home_page"))

@app.route("/search-results", methods=["GET"])
def search_results_page():
    search_text = request.args.get("search_text", request.args.get("ingredients", ""))
    search_type = get_search_type(request.args.get("search_type"))

    try:
        # Search MealDB API
        if search_type == "name":
            api_recipes = search_recipes_by_name(search_text)
            user_recipes = search_user_recipes_by_name(search_text)
        else:
            api_recipes = search_recipes_by_ingredients(search_text)
            user_recipes = search_user_recipes_by_ingredients(search_text)

        api_error = False
    except MealDBError:
        api_recipes = []
        user_recipes = []
        api_error = True

    # Convert sqlite3.Row → dict so we can add fields
    user_recipes = [dict(r) for r in user_recipes]

    # Tag user recipes so templates know they are custom
    for r in user_recipes:
        r["is_user_recipe"] = True

    # Combine both sets of results
    recipes = api_recipes + user_recipes

    # Save search history
    if session.get("user_id") and search_text.strip():
        add_search_history(session["user_id"], search_text, search_type)

    # Pagination
    page = request.args.get("page", 1, type=int) or 1
    page_recipes, page, total_pages = paginate(recipes, page)

    return render_template(
        "search_results.html",
        recipes=page_recipes,
        search_text=search_text,
        search_type=search_type,
        api_error=api_error,
        favorite_ids=get_current_favorite_ids(),
        page=page,
        total_pages=total_pages,
        total_results=len(recipes)
    )


@app.route("/browse", methods=["GET"])
def browse_page():
    category = request.args.get("category", "")
    area = request.args.get("area", "")
    api_error = False

    try:
        categories = get_categories()
        areas = get_areas()
    except MealDBError:
        categories, areas = [], []
        api_error = True

    recipes = []

    if category:
        try:
            recipes = get_recipes_by_category(category)
        except MealDBError:
            api_error = True
    elif area:
        try:
            recipes = get_recipes_by_area(area)
        except MealDBError:
            api_error = True

    page = request.args.get("page", 1, type=int) or 1
    page_recipes, page, total_pages = paginate(recipes, page)

    return render_template(
        "browse.html",
        categories=categories,
        areas=areas,
        category=category,
        area=area,
        recipes=page_recipes,
        api_error=api_error,
        favorite_ids=get_current_favorite_ids(),
        page=page,
        total_pages=total_pages,
        total_results=len(recipes)
    )


@app.route("/recipe/<recipe_id>", methods=["GET"])
def recipe_detail_page(recipe_id):
    try:
        recipe = get_recipe_by_id(recipe_id)
    except MealDBError:
        flash("The recipe service is unavailable right now. Please try again soon.")
        recipe = None

    if recipe is None:
        return render_template(
            "recipe_detail.html",
            recipe=None,
            ingredients=[],
            is_favorite=False
        )

    user_id = session.get("user_id")
    favorite_status = bool(user_id and is_recipe_favorite(user_id, recipe_id))

    return render_template(
        "recipe_detail.html",
        recipe=recipe,
        ingredients=get_recipe_ingredients(recipe),
        is_favorite=favorite_status
    )


@app.route("/register", methods=["GET", "POST"])
def register_page():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not username or not email or not password:
            flash("Username, email, and password are required.")
            return render_template("register.html", username=username, email=email)

        if password != confirm_password:
            flash("Passwords do not match.")
            return render_template("register.html", username=username, email=email)

        password_error = get_password_error(password)
        if password_error:
            flash(password_error)
            return render_template("register.html", username=username, email=email)

        try:
            create_user(username, email, generate_password_hash(password))
        except sqlite3.IntegrityError:
            flash("That username or email is already registered.")
            return render_template("register.html", username=username, email=email)

        flash("Account created successfully. Please log in.")
        return redirect(url_for("login_page"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login_page():
    if request.method == "POST":
        username_or_email = request.form.get("username_or_email", "").strip()
        password = request.form.get("password", "")
        next_page = request.form.get("next") or url_for("home_page")
        user = get_user_for_login(username_or_email)

        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Invalid username, email, or password.")
            return render_template(
                "login.html",
                username_or_email=username_or_email,
                next_page=next_page
            )

        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        flash(f"Welcome back, {user['username']}!")

        if not is_safe_redirect(next_page):
            next_page = url_for("home_page")

        return redirect(next_page)

    return render_template("login.html", next_page=request.args.get("next", ""))


@app.route("/logout")
def logout_page():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home_page"))


@app.route("/profile")
@login_required
def profile_page():
    user = get_current_user()
    counts = get_profile_counts(user["id"])

    return render_template("profile.html", user=user, counts=counts)


@app.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password_page():
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")
        user = get_user_for_login(session["username"])

        if not check_password_hash(user["password_hash"], current_password):
            flash("Current password is incorrect.")
            return render_template("change_password.html")

        if new_password != confirm_password:
            flash("New passwords do not match.")
            return render_template("change_password.html")

        password_error = get_password_error(new_password)
        if password_error:
            flash(password_error)
            return render_template("change_password.html")

        update_user_password(user["id"], generate_password_hash(new_password))
        flash("Password updated successfully.")
        return redirect(url_for("profile_page"))

    return render_template("change_password.html")


@app.route("/favorites")
@login_required
def favorites_page():
    favorites = get_user_favorites(session["user_id"])
    return render_template("favorites.html", favorites=favorites)


@app.route("/favorites/add/<recipe_id>", methods=["POST"])
@login_required
def add_favorite_page(recipe_id):
    next_page = request.form.get("next")

    try:
        recipe = get_recipe_by_id(recipe_id)
    except MealDBError:
        flash("The recipe service is unavailable right now. Please try again soon.")
        recipe = None

    if recipe is None:
        flash("This recipe could not be found.")
        return redirect(
            next_page if is_safe_redirect(next_page)
            else url_for("recipe_detail_page", recipe_id=recipe_id)
        )

    add_favorite(session["user_id"], recipe)
    flash("Recipe saved to your favorites.")

    if is_safe_redirect(next_page):
        return redirect(next_page)

    return redirect(url_for("recipe_detail_page", recipe_id=recipe_id))


@app.route("/favorites/remove/<recipe_id>", methods=["POST"])
@login_required
def remove_favorite_page(recipe_id):
    remove_favorite(session["user_id"], recipe_id)
    flash("Recipe removed from your favorites.")
    next_page = request.form.get("next")

    if is_safe_redirect(next_page):
        return redirect(next_page)

    return redirect(url_for("favorites_page"))


@app.route("/new-recipes")
@login_required
def new_arrivals_page():
    try:
        recipes = get_random_recipes()
        api_error = False
    except MealDBError:
        recipes = []
        api_error = True

    return render_template(
        "new_recipes.html",
        recipes=recipes,
        api_error=api_error,
        favorite_ids=get_current_favorite_ids()
    )


@app.route("/history")
@login_required
def history_page():
    searches = get_user_search_history(session["user_id"])
    return render_template("history.html", searches=searches)


@app.route("/history/clear", methods=["POST"])
@login_required
def clear_history_page():
    clear_user_search_history(session["user_id"])
    flash("Search history cleared.")
    return redirect(url_for("history_page"))

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload_recipe_page():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        ingredients = request.form.get("ingredients", "").strip()
        instructions = request.form.get("instructions", "").strip()
        image_url = request.form.get("image_url", "").strip()

        if not name or not ingredients or not instructions:
            flash("Name, ingredients, and instructions are required.")
            return render_template("upload_recipe.html")

        add_user_recipe(
            session["user_id"],
            name,
            ingredients,
            instructions,
            image_url
        )

        flash("Recipe uploaded successfully!")
        return redirect(url_for("my_recipes_page"))

    return render_template("upload_recipe.html")

@app.route("/my-recipes")
@login_required
def my_recipes_page():
    recipes = get_user_recipes(session["user_id"])
    return render_template("my_recipes.html", recipes=recipes)

@app.route("/my-recipes/<int:recipe_id>")
@login_required
def uploaded_recipe_detail_page(recipe_id):
    recipe = get_uploaded_recipe(recipe_id)

    if recipe is None:
        flash("Recipe not found.")
        return redirect(url_for("my_recipes_page"))

    return render_template("uploaded_recipe_detail.html", recipe=recipe)


init_database()


if __name__ == "__main__":
    app.run(debug=True)
