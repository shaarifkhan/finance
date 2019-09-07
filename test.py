import os
import time

from cs50 import SQL

# Configure application

db = SQL("sqlite:///test.db")

# rows=db.execute("SELECT companyName FROM portfolio WHERE id = :user_id", user_id=session["user_id"])

# print(rows)