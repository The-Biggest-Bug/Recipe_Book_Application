from flask import Flask, render_template, url_for, jsonify, request
import requests

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def home_page():
    if request.method == 'GET':
        return render_template("index.html")
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