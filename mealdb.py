import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


BASE_URL = "https://www.themealdb.com/api/json/v1/1"
REQUEST_TIMEOUT = 8
CACHE_TTL_SECONDS = 300

_session = requests.Session()
_retries = Retry(
    total=2,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"]
)
_session.mount("https://", HTTPAdapter(max_retries=_retries))
_session.mount("http://", HTTPAdapter(max_retries=_retries))

_response_cache = {}


class MealDBError(Exception):
    """Raised when TheMealDB API cannot be reached or returns an invalid response."""


def _cache_key(endpoint, params):
    return (endpoint, tuple(sorted((params or {}).items())))


def _cache_get(key):
    entry = _response_cache.get(key)

    if entry is None:
        return None

    expires_at, value = entry

    if time.time() >= expires_at:
        del _response_cache[key]
        return None

    return value


def _cache_set(key, value):
    _response_cache[key] = (time.time() + CACHE_TTL_SECONDS, value)


def fetch_mealdb(endpoint, params=None, cacheable=True):
    key = _cache_key(endpoint, params)

    if cacheable:
        cached = _cache_get(key)
        if cached is not None:
            return cached

    try:
        response = _session.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise MealDBError(f"TheMealDB request failed: {exc}") from exc

    if cacheable:
        _cache_set(key, data)

    return data


def get_recipe_ingredients(recipe):
    ingredients = []

    for number in range(1, 21):
        ingredient = recipe.get(f"strIngredient{number}")
        measurement = recipe.get(f"strMeasure{number}")

        if ingredient and ingredient.strip():
            ingredients.append({
                "name": ingredient.strip(),
                "measurement": measurement.strip() if measurement else ""
            })

    return ingredients


def get_default_recipes():
    recipes = []

    for letter in ["a", "b", "c"]:
        data = fetch_mealdb("search.php", {"f": letter})
        recipes.extend((data or {}).get("meals") or [])

    return recipes


def search_recipes_by_ingredients(search_text):
    ingredients = [
        ingredient.strip().replace(" ", "_")
        for ingredient in search_text.split(",")
        if ingredient.strip()
    ]
    recipes_by_id = {}

    for ingredient in ingredients:
        data = fetch_mealdb("filter.php", {"i": ingredient})
        meals = (data or {}).get("meals") or []

        for meal in meals:
            recipes_by_id[meal["idMeal"]] = meal

    return list(recipes_by_id.values())


def search_recipes_by_name(search_text):
    data = fetch_mealdb("search.php", {"s": search_text.strip()})
    return (data or {}).get("meals") or []


def get_recipe_by_id(recipe_id):
    data = fetch_mealdb("lookup.php", {"i": recipe_id})
    meals = (data or {}).get("meals") or []

    return meals[0] if meals else None


def get_random_recipes(count=8):
    recipes_by_id = {}

    for _ in range(count):
        data = fetch_mealdb("random.php", cacheable=False)
        meals = (data or {}).get("meals") or []

        if meals:
            recipes_by_id[meals[0]["idMeal"]] = meals[0]

    return list(recipes_by_id.values())


def get_categories():
    data = fetch_mealdb("list.php", {"c": "list"})
    categories = (data or {}).get("meals") or []
    return sorted(category["strCategory"] for category in categories if category.get("strCategory"))


def get_areas():
    data = fetch_mealdb("list.php", {"a": "list"})
    areas = (data or {}).get("meals") or []
    return sorted(area["strArea"] for area in areas if area.get("strArea"))


def get_recipes_by_category(category):
    data = fetch_mealdb("filter.php", {"c": category})
    return (data or {}).get("meals") or []


def get_recipes_by_area(area):
    data = fetch_mealdb("filter.php", {"a": area})
    return (data or {}).get("meals") or []
