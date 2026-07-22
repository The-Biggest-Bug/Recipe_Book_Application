import pytest

import app as app_module
from mealdb import MealDBError


SAMPLE_RECIPE = {
    "idMeal": "52772",
    "strMeal": "Teriyaki Chicken Casserole",
    "strMealThumb": "https://example.com/thumb.jpg",
    "strCategory": "Chicken",
    "strArea": "Japanese",
    "strInstructions": "Cook it.",
}


@pytest.fixture(autouse=True)
def fake_mealdb(monkeypatch):
    monkeypatch.setattr(app_module, "get_recipe_by_id", lambda recipe_id: SAMPLE_RECIPE)


def test_recipe_detail_shows_recipe(logged_in_client):
    response = logged_in_client.get(f"/recipe/{SAMPLE_RECIPE['idMeal']}")

    assert response.status_code == 200
    assert b"Teriyaki Chicken Casserole" in response.data
    assert b"Save to Favorites" in response.data


def test_add_and_remove_favorite(logged_in_client):
    add_response = logged_in_client.post(
        f"/favorites/add/{SAMPLE_RECIPE['idMeal']}",
        follow_redirects=True,
    )
    assert b"Recipe saved to your favorites" in add_response.data
    assert b"Remove from Favorites" in add_response.data

    favorites_response = logged_in_client.get("/favorites")
    assert b"Teriyaki Chicken Casserole" in favorites_response.data

    remove_response = logged_in_client.post(
        f"/favorites/remove/{SAMPLE_RECIPE['idMeal']}",
        follow_redirects=True,
    )
    assert b"Recipe removed from your favorites" in remove_response.data

    favorites_response = logged_in_client.get("/favorites")
    assert b"Your saved recipes will appear here" in favorites_response.data


def test_add_favorite_honors_next_redirect(logged_in_client):
    response = logged_in_client.post(
        f"/favorites/add/{SAMPLE_RECIPE['idMeal']}",
        data={"next": "/browse"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/browse"


def test_add_favorite_requires_login(client):
    response = client.post(
        f"/favorites/add/{SAMPLE_RECIPE['idMeal']}",
        follow_redirects=True,
    )

    assert b"Please log in to view this page" in response.data


def test_add_favorite_when_service_unavailable(monkeypatch, logged_in_client):
    def raise_error(recipe_id):
        raise MealDBError("boom")

    monkeypatch.setattr(app_module, "get_recipe_by_id", raise_error)

    response = logged_in_client.post(
        f"/favorites/add/{SAMPLE_RECIPE['idMeal']}",
        follow_redirects=True,
    )

    assert b"unavailable" in response.data.lower()
