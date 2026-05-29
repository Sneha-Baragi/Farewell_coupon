from flask import Flask, render_template, request, url_for
import sqlite3
import pandas as pd
import uuid
import qrcode
import os
from datetime import datetime

app = Flask(__name__)

# =====================================================
# CONFIG
# =====================================================

DATABASE = "coupons.db"

ADMIN_PASSWORD = "farewell2026"

# =====================================================
# DATABASE
# =====================================================

def init_db():

    conn = sqlite3.connect(DATABASE)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS coupons(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        usn TEXT UNIQUE,

        token TEXT UNIQUE,

        used INTEGER DEFAULT 0,

        generated_at TEXT,

        used_at TEXT

    )
    """)

    conn.commit()
    conn.close()


init_db()

# =====================================================
# LOAD VALID USNS
# =====================================================

valid_usns = set(
    pd.read_csv("usns.csv")["USN"].str.lower()
)

# =====================================================
# HOME PAGE
# =====================================================

@app.route("/")
def home():

    return render_template("home.html")

# =====================================================
# HEALTH CHECK
# =====================================================

@app.route("/health")
def health():

    return "OK"

# =====================================================
# GENERATE QR
# =====================================================

@app.route("/generate", methods=["POST"])
def generate():

    usn = request.form["usn"].strip().lower()

    if usn not in valid_usns:

        return """
        <h2 style='color:red'>
        Invalid USN
        </h2>
        """

    conn = sqlite3.connect(DATABASE)

    c = conn.cursor()

    c.execute(
        "SELECT token FROM coupons WHERE usn=?",
        (usn,)
    )

    row = c.fetchone()

    if row:

        token = row[0]

    else:

        token = str(uuid.uuid4())

        generated_time = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        c.execute(
            """
            INSERT INTO coupons
            (usn, token, generated_at)

            VALUES (?, ?, ?)
            """,
            (
                usn,
                token,
                generated_time
            )
        )

        conn.commit()

    conn.close()

    # Dynamic URL generation
    verify_url = request.host_url.rstrip("/") + url_for(
        "verify",
        token=token
    )

    img = qrcode.make(verify_url)

    os.makedirs("static", exist_ok=True)

    filename = f"{token}.png"

    filepath = os.path.join(
        "static",
        filename
    )

    img.save(filepath)

    return render_template(
        "qr.html",
        image=filename,
        usn=usn
    )

# =====================================================
# VERIFY QR
# =====================================================

@app.route("/verify/<token>")
def verify(token):

    conn = sqlite3.connect(DATABASE)

    c = conn.cursor()

    c.execute(
        """
        SELECT usn, used
        FROM coupons
        WHERE token=?
        """,
        (token,)
    )

    row = c.fetchone()

    if row is None:

        conn.close()

        return """
        <h2 style='color:red'>
        Invalid Coupon
        </h2>
        """

    usn = row[0]
    used = row[1]

    if used == 1:

        conn.close()

        return render_template(
            "verify.html",
            status="USED",
            usn=usn
        )

    used_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    c.execute(
        """
        UPDATE coupons

        SET used=1,
            used_at=?

        WHERE token=?
        """,
        (
            used_time,
            token
        )
    )

    conn.commit()
    conn.close()

    return render_template(
        "verify.html",
        status="VALID",
        usn=usn
    )

# =====================================================
# ADMIN DASHBOARD
# =====================================================

@app.route("/admin")
def admin():

    password = request.args.get("password")

    if password != ADMIN_PASSWORD:

        return """
        <h2 style='color:red'>
        Unauthorized Access
        </h2>
        """

    conn = sqlite3.connect(DATABASE)

    c = conn.cursor()

    total = len(valid_usns)

    c.execute(
        "SELECT COUNT(*) FROM coupons"
    )

    generated = c.fetchone()[0]

    c.execute(
        """
        SELECT COUNT(*)
        FROM coupons
        WHERE used=1
        """
    )

    used = c.fetchone()[0]

    conn.close()

    remaining = total - used

    return render_template(
        "admin.html",
        total=total,
        generated=generated,
        used=used,
        remaining=remaining
    )

# =====================================================
# RUN APP
# =====================================================

if __name__ == "__main__":
    app.run(debug=True)