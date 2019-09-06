import os
import time

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")



@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    stocks = db.execute("SELECT * FROM portfolio WHERE user_id = :user_id",user_id = session['user_id'])

    print(stocks)
    #total of all shares
    total = db.execute("SELECT SUM(total) from portfolio WHERE user_id = :user_id",user_id= session['user_id'])
   
    # converting list of dictionary into float
    total=total[0]['SUM(total)']

    cash_remaining = db.execute("SELECT cash from users WHERE id=:user_id",user_id= session['user_id'])
    
    
    # converting list of dictionary into float i.e [{'cash': .....}]
    cash_remaining=cash_remaining[0]['cash']
    #if user hasnt buy anything yet
    if not stocks:
        return render_template("index.html",cash_remaining=cash_remaining,total_balance=cash_remaining+0)

    return render_template("index.html",stocks=stocks,cash_remaining=cash_remaining,total_balance=cash_remaining+total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        if not request.form.get("symbol") or not request.form.get("share"):
            return apology("must enter symbol and no of shares",403)

        stock= lookup(request.form.get("symbol"))
        noOfshares = int(request.form.get("share"))
        if noOfshares < 0:
            return apology("enter any positive no of shares",403)
        price = stock['price']
        total = price * noOfshares
        rows = db.execute("SELECT cash FROM users WHERE id=:user_id",user_id=session["user_id"])
        cash = rows[0]['cash']
        if cash < total:
            return apology("not enough cash")
        new_cash = cash-total
        db.execute("UPDATE users SET cash=:cash WHERE id= :user_id",cash=new_cash,user_id=session["user_id"])

        # to check if the share of particular company is already present
        row = db.execute("SELECT symbol FROM portfolio WHERE user_id=:user_id AND symbol=:symbol ",user_id = session["user_id"],symbol=stock['symbol'])
        if row and (row[0]['symbol'] == stock['symbol']):
            db.execute("UPDATE portfolio SET shares=shares+ :noOfshares,price=:price,total= total+ :total WHERE user_id = :user_id AND symbol=:symbol",noOfshares=noOfshares,price=price,total=total,user_id = session['user_id'],symbol=stock['symbol'])
        # if bought share of a particular company for the first time
        else:
            index = db.execute("INSERT INTO portfolio(user_id,companyName,shares,price,total,symbol) VALUES(:id,:companyName,:shares,:price,:total,:symbol)",id=session["user_id"],companyName=stock['name'],shares=noOfshares,price=stock['price'],total=total,symbol=stock['symbol'])
        
        db.execute("INSERT INTO history (user_id,time,status,shares) VALUES(:user_id,DATETIME('now','localtime'),'bought',:noOfshares)",user_id=session['user_id'],noOfshares=noOfshares)


        return redirect('/')
    
    else:
        return render_template("buy.html") 




@app.route("/check", methods=["GET"])
def check():
    """Return true if username available, else false, in JSON format"""
    return jsonify("TODO")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")




@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == 'POST':

        symbol=request.form.get("symbol")
        if not symbol:
            return apology("please enter the symbol",403)
        quote = lookup(symbol)    
        cost=usd(quote['price'])
        return render_template('quoted.html',companyName=quote['name'],cost=cost,symbol=quote['symbol'])
    
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        if not request.form.get("username") or not request.form.get("password"):
            return apology("must provide username and password",403)
        if request.form.get("password") != request.form.get("re_password"):
            return apology("password does not match")


        index=db.execute("INSERT INTO users (username,hash) VALUES(:username,:hash)",username=request.form.get("username"),hash=generate_password_hash(request.form.get("password"),method="plain"))

        return render_template('login.html',register="you are registered")


    else:
        return render_template("register.html")
    # return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    #names of shares user owns
    share_names=db.execute("SELECT symbol FROM portfolio")
    if request.method == "POST":
        symbol=request.form.get("symbol")

        if not symbol:
            return apology("please select the symbol",403)
            #no of shares user has entered to sell
        no_of_shares=request.form.get("shares")
        #current price of share in market that user want to sell
        price=lookup(symbol)
        price=price['price']


        db.execute("UPDATE portfolio SET shares= shares - :no_of_shares,total=total-(:price* :no_of_shares) WHERE user_id=:user_id AND symbol=:symbol",price=price,no_of_shares=no_of_shares,user_id=session['user_id'],symbol=symbol)
        db.execute("UPDATE users SET cash= cash+ :price * :no_of_shares WHERE id=:user_id",price=price,no_of_shares=no_of_shares,user_id=session['user_id'])
        return redirect("/")
    else:
        print(share_names)
        return render_template("sell.html",share_names=share_names)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
