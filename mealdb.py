import requests


BASE_URL = "https://www.themealdb.com/api/json/v1/1"
REQUEST_TIMEOUT = 8


def fetch_mealdb(endpoint, params=None):
    try:
        response = requests.get(
            f"{BASE_URL}/{endpoint}",
            params=params,
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError):
        return None


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
        data = fetch_mealdb("random.php")
        meals = (data or {}).get("meals") or []

        if meals:
            recipes_by_id[meals[0]["idMeal"]] = meals[0]

    return list(recipes_by_id.values())
