from flask import Flask, render_template, url_for, jsonify, request
import requests
import json

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def home_page():
    if request.method == 'GET':
        try:
            #FIX THIS JSON SERIALIZATION AREA: 12-20!!!
            response_a = requests.get("https://www.themealdb.com/api/json/v1/1/search.php?f=a")
            response_a.raise_for_status()
            data = json.load(response_a)
            food_name = data["strMeal"]
        except requests.exceptions.HTTPError as http_err:
            return jsonify({'error': f'HTTP error occurred: {http_err}'}), 500
        except Exception as err:
            return jsonify({'error': f'Other error occurred: {err}'}), 500
        return render_template("index.html", data=food_name)
    if request.method == 'POST':
        #Enter functionality form API for search function
        pass

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