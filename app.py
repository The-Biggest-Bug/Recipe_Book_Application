from flask import Flask, render_template, url_for, request, jsonify, request, response

app = Flask(__name__)

@app.route("/", methods=['GET', 'POST'])
def home_page():
    if request.method == 'GET':
        return render_template("index.html")
    if request.method == 'POST':
        #Enter functionality form API for search function
        pass

@app.route("/favorites")
def favorites_page():
    return render_template("favorites.html")

@app.route("/new-recipes")
def new_arrivals_page():
    return render_template("new_recipes.html")

@app.route("/suggestions")
def suggestions_page():
    return render_template("suggested_recipes.html")


if __name__ == "__main__":
    app.run(debug=True)