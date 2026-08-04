import sqlite3

import pytest

import database


SAMPLE_RECIPE = {
    "idMeal": "52772",
    "strMeal": "Teriyaki Chicken Casserole",
    "strMealThumb": "https://example.com/thumb.jpg",
    "strCategory": "Chicken",
    "strArea": "Japanese",
    "strSource": "https://example.com/source",
    "strYoutube": "https://example.com/video",
}


def test_create_user_and_login_lookup(client):
    database.create_user("chef", "chef@example.com", "hashed-password")

    by_username = database.get_user_for_login("chef")
    by_email = database.get_user_for_login("chef@example.com")

    assert by_username["email"] == "chef@example.com"
    assert by_email["username"] == "chef"


def test_create_user_rejects_duplicate_username(client):
    database.create_user("chef", "chef@example.com", "hashed-password")

    with pytest.raises(sqlite3.IntegrityError):
        database.create_user("chef", "other@example.com", "hashed-password")


def test_update_user_password(client):
    database.create_user("chef", "chef@example.com", "old-hash")
    user = database.get_user_for_login("chef")

    database.update_user_password(user["id"], "new-hash")

    updated = database.get_user_for_login("chef")
    assert updated["password_hash"] == "new-hash"


def test_favorites_add_remove_and_lookup(client):
    database.create_user("chef", "chef@example.com", "hash")
    user = database.get_user_for_login("chef")

    assert database.is_recipe_favorite(user["id"], SAMPLE_RECIPE["idMeal"]) is False

    database.add_favorite(user["id"], SAMPLE_RECIPE)

    assert database.is_recipe_favorite(user["id"], SAMPLE_RECIPE["idMeal"]) is True
    assert database.get_user_favorite_ids(user["id"]) == {SAMPLE_RECIPE["idMeal"]}

    favorites = database.get_user_favorites(user["id"])
    assert len(favorites) == 1
    assert favorites[0]["recipe_name"] == SAMPLE_RECIPE["strMeal"]

    database.remove_favorite(user["id"], SAMPLE_RECIPE["idMeal"])

    assert database.is_recipe_favorite(user["id"], SAMPLE_RECIPE["idMeal"]) is False
    assert database.get_user_favorite_ids(user["id"]) == set()


def test_add_favorite_twice_is_idempotent(client):
    database.create_user("chef", "chef@example.com", "hash")
    user = database.get_user_for_login("chef")

    database.add_favorite(user["id"], SAMPLE_RECIPE)
    database.add_favorite(user["id"], SAMPLE_RECIPE)

    assert len(database.get_user_favorites(user["id"])) == 1


def test_search_history_add_get_and_clear(client):
    database.create_user("chef", "chef@example.com", "hash")
    user = database.get_user_for_login("chef")

    database.add_search_history(user["id"], "chicken", "name")
    database.add_search_history(user["id"], "  ", "name")

    history = database.get_user_search_history(user["id"])
    assert len(history) == 1
    assert history[0]["search_text"] == "chicken"

    database.clear_user_search_history(user["id"])
    assert database.get_user_search_history(user["id"]) == []


def test_profile_counts(client):
    database.create_user("chef", "chef@example.com", "hash")
    user = database.get_user_for_login("chef")

    database.add_favorite(user["id"], SAMPLE_RECIPE)
    database.add_search_history(user["id"], "chicken", "name")

    counts = database.get_profile_counts(user["id"])
    assert counts == {"favorite_count": 1, "search_count": 1}
