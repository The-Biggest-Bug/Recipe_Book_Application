import pytest
import requests

import mealdb


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")

    def json(self):
        return self._payload


@pytest.fixture(autouse=True)
def clear_cache():
    mealdb._response_cache.clear()
    yield
    mealdb._response_cache.clear()


def test_fetch_mealdb_caches_identical_requests(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse({"meals": [{"idMeal": "1"}]})

    monkeypatch.setattr(mealdb._session, "get", fake_get)

    first = mealdb.fetch_mealdb("search.php", {"s": "chicken"})
    second = mealdb.fetch_mealdb("search.php", {"s": "chicken"})

    assert first == second
    assert len(calls) == 1


def test_fetch_mealdb_skips_cache_when_not_cacheable(monkeypatch):
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params)
        return FakeResponse({"meals": [{"idMeal": "1"}]})

    monkeypatch.setattr(mealdb._session, "get", fake_get)

    mealdb.fetch_mealdb("random.php", cacheable=False)
    mealdb.fetch_mealdb("random.php", cacheable=False)

    assert len(calls) == 2


def test_fetch_mealdb_raises_mealdb_error_on_network_failure(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        raise requests.ConnectionError("network down")

    monkeypatch.setattr(mealdb._session, "get", fake_get)

    with pytest.raises(mealdb.MealDBError):
        mealdb.fetch_mealdb("search.php", {"s": "chicken"})


def test_fetch_mealdb_raises_mealdb_error_on_bad_status(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({}, status_code=500)

    monkeypatch.setattr(mealdb._session, "get", fake_get)

    with pytest.raises(mealdb.MealDBError):
        mealdb.fetch_mealdb("search.php", {"s": "chicken"})


def test_get_categories_returns_sorted_names(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"meals": [{"strCategory": "Seafood"}, {"strCategory": "Beef"}]})

    monkeypatch.setattr(mealdb._session, "get", fake_get)

    assert mealdb.get_categories() == ["Beef", "Seafood"]


def test_search_recipes_by_ingredients_deduplicates_by_id(monkeypatch):
    def fake_get(url, params=None, timeout=None):
        return FakeResponse({"meals": [{"idMeal": "1"}, {"idMeal": "2"}]})

    monkeypatch.setattr(mealdb._session, "get", fake_get)

    results = mealdb.search_recipes_by_ingredients("chicken, chicken")

    assert [meal["idMeal"] for meal in results] == ["1", "2"]
