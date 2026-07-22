import sqlite3
from flask import g


DATABASE = "users.db"


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


def init_database():
    db = sqlite3.connect(DATABASE)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            recipe_id TEXT NOT NULL,
            recipe_name TEXT NOT NULL,
            thumbnail TEXT,
            category TEXT,
            area TEXT,
            source_url TEXT,
            youtube_url TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE (user_id, recipe_id)
        );

        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            search_text TEXT NOT NULL,
            search_type TEXT NOT NULL DEFAULT 'ingredients',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        );
        """
    )
    columns = [
        column[1]
        for column in db.execute("PRAGMA table_info(search_history)").fetchall()
    ]

    if "search_type" not in columns:
        db.execute(
            "ALTER TABLE search_history "
            "ADD COLUMN search_type TEXT NOT NULL DEFAULT 'ingredients'"
        )

    db.commit()
    db.close()


def create_user(username, email, password_hash):
    db = get_db()
    db.execute(
        "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
        (username, email, password_hash)
    )
    db.commit()


def get_user_by_id(user_id):
    return get_db().execute(
        "SELECT id, username, email, created_at FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()


def get_user_for_login(username_or_email):
    return get_db().execute(
        """
        SELECT * FROM users
        WHERE username = ? OR email = ?
        """,
        (username_or_email, username_or_email.lower())
    ).fetchone()


def update_user_password(user_id, password_hash):
    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ? WHERE id = ?",
        (password_hash, user_id)
    )
    db.commit()


def add_favorite(user_id, recipe):
    db = get_db()
    db.execute(
        """
        INSERT OR IGNORE INTO favorites (
            user_id, recipe_id, recipe_name, thumbnail, category, area, source_url, youtube_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            recipe.get("idMeal"),
            recipe.get("strMeal"),
            recipe.get("strMealThumb"),
            recipe.get("strCategory"),
            recipe.get("strArea"),
            recipe.get("strSource"),
            recipe.get("strYoutube")
        )
    )
    db.commit()


def remove_favorite(user_id, recipe_id):
    db = get_db()
    db.execute(
        "DELETE FROM favorites WHERE user_id = ? AND recipe_id = ?",
        (user_id, recipe_id)
    )
    db.commit()


def get_user_favorites(user_id):
    return get_db().execute(
        """
        SELECT * FROM favorites
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user_id,)
    ).fetchall()


def is_recipe_favorite(user_id, recipe_id):
    favorite = get_db().execute(
        """
        SELECT id FROM favorites
        WHERE user_id = ? AND recipe_id = ?
        """,
        (user_id, recipe_id)
    ).fetchone()

    return favorite is not None


def add_search_history(user_id, search_text, search_type):
    if not search_text.strip():
        return

    db = get_db()
    db.execute(
        """
        INSERT INTO search_history (user_id, search_text, search_type)
        VALUES (?, ?, ?)
        """,
        (user_id, search_text.strip(), search_type)
    )
    db.commit()


def get_user_search_history(user_id):
    return get_db().execute(
        """
        SELECT * FROM search_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 25
        """,
        (user_id,)
    ).fetchall()


def clear_user_search_history(user_id):
    db = get_db()
    db.execute("DELETE FROM search_history WHERE user_id = ?", (user_id,))
    db.commit()


def get_profile_counts(user_id):
    db = get_db()
    favorite_count = db.execute(
        "SELECT COUNT(*) AS count FROM favorites WHERE user_id = ?",
        (user_id,)
    ).fetchone()["count"]
    search_count = db.execute(
        "SELECT COUNT(*) AS count FROM search_history WHERE user_id = ?",
        (user_id,)
    ).fetchone()["count"]

    return {
        "favorite_count": favorite_count,
        "search_count": search_count
    }
