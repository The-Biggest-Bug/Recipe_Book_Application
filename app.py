from functools import wraps
import os
import sqlite3

from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from database import (
    add_favorite,
    add_search_history,
    clear_user_search_history,
    close_db,
    create_user,
    get_profile_counts,
    get_user_by_id,
    get_user_favorites,
    get_user_for_login,
    get_user_search_history,
    init_database,
    is_recipe_favorite,
    remove_favorite,
    update_user_password,
)
from mealdb import (
    get_default_recipes,
    get_random_recipes,
    get_recipe_by_id,
    get_recipe_ingredients,
    search_recipes_by_ingredients,
    search_recipes_by_name,
)


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "recipe-book-development-key")
app.teardown_appcontext(close_db)


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


@app.context_processor
def inject_current_user():
    return {"current_user": get_current_user()}


def is_safe_redirect(next_page):
    return next_page and next_page.startswith("/") and not next_page.startswith("//")


def get_search_type(raw_search_type):
    if raw_search_type == "name":
        return "name"

    return "ingredients"


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

    recipes = get_default_recipes()
    return render_template(
        "index.html",
        recipes=recipes,
        search_text="",
        search_type="ingredients",
        searched=False,
        api_error=not recipes
    )


@app.route("/search-results", methods=["GET"])
def search_results_page():
    search_text = request.args.get("search_text", request.args.get("ingredients", ""))
    search_type = get_search_type(request.args.get("search_type"))

    if search_type == "name":
        recipes = search_recipes_by_name(search_text)
    else:
        recipes = search_recipes_by_ingredients(search_text)

    if session.get("user_id") and search_text.strip():
        add_search_history(session["user_id"], search_text, search_type)

    return render_template(
        "search_results.html",
        recipes=recipes,
        search_text=search_text,
        search_type=search_type,
        api_error=bool(search_text.strip()) and not recipes
    )


@app.route("/recipe/<recipe_id>", methods=["GET"])
def recipe_detail_page(recipe_id):
    recipe = get_recipe_by_id(recipe_id)

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

        if len(password) < 6:
            flash("Password must be at least 6 characters long.")
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

        if len(new_password) < 6:
            flash("New password must be at least 6 characters long.")
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
    recipe = get_recipe_by_id(recipe_id)

    if recipe is None:
        flash("This recipe could not be found.")
        return redirect(url_for("recipe_detail_page", recipe_id=recipe_id))

    add_favorite(session["user_id"], recipe)
    flash("Recipe saved to your favorites.")
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
    recipes = get_random_recipes()
    return render_template("new_recipes.html", recipes=recipes, api_error=not recipes)


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


init_database()


if __name__ == "__main__":
    app.run(debug=True)
