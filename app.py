from flask import Flask,render_template,request
import sqlite3
import pandas as pd
import uuid
import qrcode
import os

app=Flask(__name__)

DATABASE="coupons.db"

# -----------------------------
# DATABASE
# -----------------------------

def init_db():

    conn=sqlite3.connect(DATABASE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS coupons(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        usn TEXT UNIQUE,

        token TEXT UNIQUE,

        used INTEGER DEFAULT 0

    )
    """)

    conn.commit()
    conn.close()

init_db()

# -----------------------------
# LOAD VALID USNS
# -----------------------------

valid_usns=set(
    pd.read_csv("usns.csv")["USN"].str.lower()
)

# -----------------------------
# HOME
# -----------------------------

@app.route("/")
def home():

    return render_template("home.html")

# -----------------------------
# GENERATE QR
# -----------------------------

@app.route("/generate",methods=["POST"])
def generate():

    usn=request.form["usn"].strip().lower()

    if usn not in valid_usns:

        return "Invalid USN"

    conn=sqlite3.connect(DATABASE)

    c=conn.cursor()

    c.execute(
        "SELECT token FROM coupons WHERE usn=?",
        (usn,)
    )

    row=c.fetchone()

    if row:

        token=row[0]

    else:

        token=str(uuid.uuid4())

        c.execute(
            "INSERT INTO coupons(usn,token) VALUES (?,?)",
            (usn,token)
        )

        conn.commit()

    conn.close()

    verify_url=f"https://YOUR-APP-NAME.onrender.com/verify/{token}"

    img=qrcode.make(verify_url)

    os.makedirs("static",exist_ok=True)

    path=f"static/{token}.png"

    img.save(path)

    return render_template(
        "qr.html",
        image=f"{token}.png",
        usn=usn
    )

# -----------------------------
# VERIFY
# -----------------------------

@app.route("/verify/<token>")
def verify(token):

    conn=sqlite3.connect(DATABASE)

    c=conn.cursor()

    c.execute(
        "SELECT usn,used FROM coupons WHERE token=?",
        (token,)
    )

    row=c.fetchone()

    if row is None:

        return "Invalid Coupon"

    usn=row[0]
    used=row[1]

    if used==1:

        conn.close()

        return render_template(
            "verify.html",
            status="USED",
            usn=usn
        )

    c.execute(
        "UPDATE coupons SET used=1 WHERE token=?",
        (token,)
    )

    conn.commit()
    conn.close()

    return render_template(
        "verify.html",
        status="VALID",
        usn=usn
    )

# -----------------------------
# ADMIN DASHBOARD
# -----------------------------

@app.route("/admin")
def admin():

    conn=sqlite3.connect(DATABASE)

    c=conn.cursor()

    total=len(valid_usns)

    c.execute(
        "SELECT COUNT(*) FROM coupons"
    )

    generated=c.fetchone()[0]

    c.execute(
        "SELECT COUNT(*) FROM coupons WHERE used=1"
    )

    used=c.fetchone()[0]

    conn.close()

    remaining=total-used

    return render_template(
        "admin.html",
        total=total,
        generated=generated,
        used=used,
        remaining=remaining
    )

if __name__=="__main__":
    app.run(debug=True)