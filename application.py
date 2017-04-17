# -*- coding: utf-8 -*-

import datetime
from tempfile import gettempdir

from cs50 import SQL
from flask import Flask, redirect, render_template, request, session, url_for
from flask_session import Session
from helpers import *
from passlib.apps import custom_app_context as pwd_context

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# custom filter
app.jinja_env.filters["usd"] = usd

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = gettempdir()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """
    Display the user’s current cash balance along with a grand total,
    stocks the user owns, the numbers of shares owned, the current price of each stock,
    and the total value of each holding.
    :return:
    """

    # get amount of cash and stocks from db
    user_id = session['user_id']
    cash_query = db.execute("SELECT cash FROM users WHERE id = '{id}'".format(id=user_id))
    cash = get_query_with_key(cash_query, "cash")
    stocks = db.execute("SELECT stock, SUM(num_stocks) FROM transactions WHERE user_id = '{id}' GROUP BY stock".format(
        id=user_id))

    # create a list that can be transformed into table on the html page
    table = {}
    values = []
    for stock in stocks:
        name = dict(stock)['stock']
        qty = dict(stock)['SUM(num_stocks)']
        price = lookup(name)["price"]
        value = qty * price
        table[name] = qty, price, value

        for i in table:
            values.append(table[i][2])  # 2 - is the 3-rd place in the list where values should go

    grand_total = cash + sum(values)

    return render_template("index.html",
                           cash="{0:.2f} stock".format(cash),
                           grand_total="{0:.2f} USD".format(grand_total),
                           stocks=table)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock."""
    if request.method == "POST":

        # validate input
        if lookup(request.form.get("stock")) is None:
            return render_template("buy.html", message_stock="Sorry no such stock")
        try:
            if int(request.form.get("shares")) <= 0:
                return render_template("buy.html", message_stock="You should buy at least one stock")
        except ValueError:
            return render_template("buy.html", message_stoc="You should buy at least one stock")

        stock, shares, price, paid, time, cash = get_transaction_param()

        # check cash vs price to pay
        if paid > cash:
            return apology("You don't have enough cash")

        # update cahs in users db
        db.execute(
            "UPDATE users SET cash = '{cash}' WHERE id = '{id}';".format(cash=cash - paid, id=session['user_id']))

        # add transaction 
        db.execute("INSERT INTO transactions (id, user_id, stock, num_stocks, price, time, paid, type) \
                    VALUES (NULL, '{user_id}', '{stock}', '{num_stocks}', '{price}', '{time}', '{paid}', 'BUY')".format(
            user_id=session['user_id'], stock=stock, num_stocks=shares, price=price, time=str(time), paid=paid))

        return render_template("buy.html",
                               message_shares="You bought {paid:.2f} USD worth of {stock} shares {time}"
                               .format(paid=paid, stock=stock, time=str(time)))
    else:
        return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """
    Shows history of transactions. Displays an HTML table summarizing all of a user’s transactions ever,
    listing row by row each and every buy and every sell
    """
    stocks = db.execute("SELECT stock, num_stocks, price, paid, type, time FROM transactions WHERE user_id = '{id}'"
                        .format(id=session['user_id']))
    # create a list that can be transformed into table on the html page
    table = []
    for stock in stocks:
        name = dict(stock)['stock']
        qty = dict(stock)['num_stocks']
        price = dict(stock)['price']
        value = dict(stock)['paid']
        operation = dict(stock)['type']
        time = dict(stock)['time']
        table.append([name, qty, price, value, operation, time])

    return render_template("history.html", stocks=table)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        # ensure username was submitted
        if not username:
            return apology("must provide username")

        # ensure password was submitted
        elif not password:
            return apology("must provide password")

        # query database for users info
        users_info = db.execute("SELECT * FROM users WHERE username = '{username}'".format(username=username))

        # ensure username exists and password is correct
        users_password = get_query_with_key(users_info, "hash")
        if len(users_info) != 1 or not pwd_context.verify(password, users_password):
            return render_template("login.html", message="invalid username and/or password")

        # remember which user has logged in
        users_name = get_query_with_key(users_info, "id")
        session["user_id"] = users_name

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("login"))


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":

        user_input_stock = request.form.get("stock")
        if not user_input_stock:
            return render_template("quote.html", message_error="enter stock symbol")

        else:
            stock = lookup(user_input_stock)
            return render_template("quoted.html",
                                   message="{stock_name} stock price: {price} USD"
                                   .format(stock_name=stock["symbol"], price=stock["price"]))

    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username_input = request.form.get("username")
        password_input = request.form.get("password")
        confirm_password_input = request.form.get("re_password")
        # ensure username was submitted
        if not username_input:
            return render_template("register.html", message_user="enter user name")

        # ensure password was submitted
        elif not password_input:
            return render_template("register.html", message_pas="enter password")

        # ensure password was submitted correctly
        elif password_input != confirm_password_input:
            return render_template("register.html", message_pas="password doesn't mach")

        # check if username in db
        user = db.execute("SELECT username FROM users WHERE username = '{username}'".format(username=username_input))
        if len(user) != 0:
            return render_template("register.html", message_user="user already exist",
                                   message_pas="want to reset the password?")

            # insert user data into the database
        db.execute("INSERT INTO users (id, username, hash) VALUES (NULL,'{username}','{password}')".format(
            username=username_input, password=pwd_context.encrypt(password_input)))

        # redirect user to home page
        return render_template("success.html", action="Register")

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock."""
    # Enables a user to sell shares of a stock.
    if request.method == "POST":

        # validate input
        if lookup(request.form.get("stock")) is None:
            return render_template("sell.html", message_stock="Sorry no such stock")

        try:
            if int(request.form.get("shares")) <= 0:
                return render_template("sell.html", message_stock="You should sell at least one stock")
        except ValueError:
            return render_template("sell.html", message_stock="Please enter valid number of stocks")

        stock, shares, price, paid, time, cash = get_transaction_param()

        # check stocks and shares avalible
        stocks = db.execute("SELECT stock, SUM(num_stocks) FROM transactions WHERE user_id = '{id}' \
                            AND stock = '{stock}' GROUP BY stock".format(id=session['user_id'], stock=stock))
        try:
            shares_owned = get_query_with_key(stocks, 'SUM(num_stocks)')
            if len(stocks) == 0 or shares_owned == 0 or shares > shares_owned:
                return apology("You don't have enough of this stock")
        except IndexError:
            return apology("You don't have this stock")

        # update cash in users db
        db.execute(
            "UPDATE users SET cash = '{cash}' WHERE id = '{id}';".format(cash=cash + paid, id=session['user_id']))

        # add transaction 
        db.execute("INSERT INTO transactions (id, user_id, stock, num_stocks, price, time, paid, type) \
                     VALUES (NULL, '{user_id}', '{stock}', '{num_stocks}', '{price}', '{time}', '{paid}', 'SELL')".format(
            user_id=session['user_id'], stock=stock, num_stocks=-shares, price=price, time=str(time), paid=-paid))

        return render_template("sell.html",
                               message_shares="You sold {paid:.2f} USD worth of {stock} shares {time}"
                               .format(paid=paid, stock=stock, time=str(time)))
    else:
        return render_template("sell.html")


@app.route("/reset_password", methods=["GET", "POST"])
def reset_password():
    """Register user."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        username_input = request.form.get("username")
        password_input = request.form.get("password")
        confirm_password_input = request.form.get("re_password")

        # ensure username was submitted
        if not username_input:
            return render_template("reset_password.html", message_user="enter user name")

        # ensure password was submitted
        elif not password_input:
            return render_template("reset_password.html", message_pas="enter password")

        elif password_input != confirm_password_input:
            return render_template("reset_password.html", message_pas="password doesn't mach")

        # check if user name in db
        user = db.execute("SELECT username FROM users WHERE username = '{username}'".format(
            username=username_input))

        if len(user) == 0:
            return render_template("reset_password.html", message_pas="user doesn't exist")
            # insert user data into the database
        db.execute("UPDATE users SET hash = '{password}' WHERE username = '{username}';".format(
            password=pwd_context.encrypt(password_input), username=username_input))

        return render_template("success.html", action="Password reset")

    else:
        return render_template("reset_password.html")


def get_transaction_param():
    # get transaction parameters
    stock = request.form.get("stock").upper()
    shares = int(request.form.get("shares"))
    price = lookup(request.form.get("stock"))["price"]
    paid = price * shares
    time = datetime.datetime.now()
    cash = get_query_with_key(db.execute("SELECT cash FROM users WHERE id = '{id}'".format(id=session['user_id'])),
                              "cash")
    return stock, shares, price, paid, time, cash


def get_query_with_key(query, key):
    try:
        return dict(query[0])[key]
    except IndexError:
        return "error"

