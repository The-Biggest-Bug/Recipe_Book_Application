from flask import Flask, render_template, url_for, jsonify, request
import requests
import json

app = Flask(__name__)

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

@app.route("/", methods=['GET', 'POST'])
def home_page():
    if request.method == 'GET':
        response_a = requests.get("https://www.themealdb.com/api/json/v1/1/search.php?f=a")
        recipes_A= response_a.json().get('meals', [])
        response_b = requests.get("https://www.themealdb.com/api/json/v1/1/search.php?f=b")
        recipes_B = response_b.json().get('meals', [])
        response_c = requests.get("https://www.themealdb.com/api/json/v1/1/search.php?f=c")
        recipes_C = response_c.json().get('meals', [])
        return render_template('index.html', recipes_a=recipes_A, recipes_b=recipes_B, recipes_c=recipes_C)
    if request.method == 'POST':
        #Enter functionality form API for search function
        pass

@app.route("/recipe/<recipe_id>", methods=['GET'])
def recipe_detail_page(recipe_id):
    response = requests.get(f"https://www.themealdb.com/api/json/v1/1/lookup.php?i={recipe_id}")
    meals = response.json().get('meals') or []
    recipe = meals[0] if meals else None

    if recipe is None:
        return render_template("recipe_detail.html", recipe=None, ingredients=[])

    ingredients = get_recipe_ingredients(recipe)
    return render_template("recipe_detail.html", recipe=recipe, ingredients=ingredients)

@app.route("/favorites", methods=['GET', 'POST', 'DELETE'])
def favorites_page():
    if request.method == 'GET':
        return render_template("favorites.html")
    if request.method == 'POST':
        #Enter functionality form API for search function
        pass
    if request.method == 'DELETE':
        #Enter functionality form API for search function
        pass

@app.route("/new-recipes", methods=['GET', 'POST'])
def new_arrivals_page():
    if request.method == 'GET':
        return render_template("new_recipes.html")
    if request.method == 'POST':
        #Enter functionality form API for search function
        pass

@app.route("/history", methods=['GET'])
def history_page():
    if request.method == 'GET':
        return render_template("history.html")


if __name__ == "__main__":
    app.run(debug=True)
