"""
Admin panel: login, password change/reset (via email OTP), and PDF uploads
for the Parts Price section.

All admin state (login email, hashed password) is kept in
instance/admin_config.json, created automatically the first time you visit
/admin (first-time setup). This file is created on YOUR machine when you
run the app — it is not something you need to create by hand, and it is
never sent anywhere.
"""

import json
import os
import random
import smtplib
import string
import time
from email.mime.text import MIMEText
from functools import wraps

from flask import (
    Blueprint, current_app, flash, redirect, render_template,
    request, session, url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

INSTANCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
CONFIG_PATH = os.path.join(INSTANCE_DIR, "admin_config.json")
OTP_PATH = os.path.join(INSTANCE_DIR, "otp.json")
OTP_VALID_SECONDS = 10 * 60  # 10 minutes


# ---------------------------------------------------------------------------
# Fill in your Gmail App Password below (Google Account > Security >
# 2-Step Verification > App Passwords). This is NOT your normal Gmail
# password. Keep this file private — do not upload it publicly.
# ---------------------------------------------------------------------------
SMTP_CONFIG = {
    "host": "smtp.gmail.com",
    "port": 587,
    "sender_email": "mdmhfooz7105@gmail.com",
    "app_password": "sqqtjcnvlkyalukg",
}


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------
def _ensure_instance_dir():
    os.makedirs(INSTANCE_DIR, exist_ok=True)


def load_admin_config():
    _ensure_instance_dir()
    if not os.path.exists(CONFIG_PATH):
        return None
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_admin_config(email, password):
    _ensure_instance_dir()
    data = {"email": email, "password_hash": generate_password_hash(password)}
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def update_password(new_password):
    config = load_admin_config()
    config["password_hash"] = generate_password_hash(new_password)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f)


def save_otp(email, otp):
    _ensure_instance_dir()
    data = {"email": email, "otp": otp, "created_at": time.time()}
    with open(OTP_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_otp():
    if not os.path.exists(OTP_PATH):
        return None
    with open(OTP_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_otp():
    if os.path.exists(OTP_PATH):
        os.remove(OTP_PATH)


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------
def send_otp_email(to_email, otp):
    msg = MIMEText(
        f"Your Alam Telecom admin password reset code is: {otp}\n\n"
        f"This code expires in 10 minutes. If you didn't request this, ignore this email."
    )
    msg["Subject"] = "Alam Telecom Admin - Password Reset Code"
    msg["From"] = SMTP_CONFIG["sender_email"]
    msg["To"] = to_email

    with smtplib.SMTP(SMTP_CONFIG["host"], SMTP_CONFIG["port"]) as server:
        server.starttls()
        server.login(SMTP_CONFIG["sender_email"], SMTP_CONFIG["app_password"])
        server.sendmail(SMTP_CONFIG["sender_email"], [to_email], msg.as_string())


# ---------------------------------------------------------------------------
# Auth guard
# ---------------------------------------------------------------------------
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin.login"))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@admin_bp.route("/", methods=["GET"])
def index():
    config = load_admin_config()
    if config is None:
        return redirect(url_for("admin.setup"))
    if session.get("admin_logged_in"):
        return redirect(url_for("admin.dashboard"))
    return redirect(url_for("admin.login"))


@admin_bp.route("/setup", methods=["GET", "POST"])
def setup():
    """First-time setup: only reachable if no admin account exists yet."""
    if load_admin_config() is not None:
        return redirect(url_for("admin.login"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")
        if not email or "@" not in email:
            flash("Enter a valid email address.")
        elif len(password) < 6:
            flash("Password must be at least 6 characters.")
        elif password != confirm:
            flash("Passwords do not match.")
        else:
            save_admin_config(email, password)
            flash("Admin account created. Please log in.")
            return redirect(url_for("admin.login"))

    return render_template("admin/setup.html")


@admin_bp.route("/login", methods=["GET", "POST"])
def login():
    config = load_admin_config()
    if config is None:
        return redirect(url_for("admin.setup"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        if email == config["email"] and check_password_hash(config["password_hash"], password):
            session["admin_logged_in"] = True
            return redirect(url_for("admin.dashboard"))
        flash("Incorrect email or password.")

    return render_template("admin/login.html")


@admin_bp.route("/logout")
def logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin.login"))


@admin_bp.route("/dashboard")
@login_required
def dashboard():
    price_categories = current_app.config["PRICE_CATEGORIES"]
    brand_groups = current_app.config["BRAND_GROUPS"]
    pdf_root = os.path.join(current_app.static_folder, "pdfs")

    grid = []
    for cat in price_categories:
        row = {"category": cat, "brands": []}
        for group in brand_groups:
            pdf_path = os.path.join(pdf_root, cat["slug"], group["slug"] + ".pdf")
            row["brands"].append({
                "group": group,
                "exists": os.path.exists(pdf_path),
                "url": url_for("static", filename=f"pdfs/{cat['slug']}/{group['slug']}.pdf"),
            })
        grid.append(row)

    return render_template("admin/dashboard.html", grid=grid)


@admin_bp.route("/upload/<category_slug>/<brand_slug>", methods=["POST"])
@login_required
def upload_pdf(category_slug, brand_slug):
    price_categories = current_app.config["PRICE_CATEGORIES"]
    brand_groups = current_app.config["BRAND_GROUPS"]

    valid_category = any(c["slug"] == category_slug for c in price_categories)
    valid_brand = any(g["slug"] == brand_slug for g in brand_groups)
    if not valid_category or not valid_brand:
        flash("Unknown category or brand.")
        return redirect(url_for("admin.dashboard"))

    file = request.files.get("pdf_file")
    if not file or file.filename == "":
        flash("Choose a PDF file first.")
        return redirect(url_for("admin.dashboard"))

    filename = secure_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        flash("Only PDF files are allowed.")
        return redirect(url_for("admin.dashboard"))

    folder = os.path.join(current_app.static_folder, "pdfs", category_slug)
    os.makedirs(folder, exist_ok=True)
    target_path = os.path.join(folder, brand_slug + ".pdf")

    # Delete the old PDF first (if any), then save the new one under the
    # same fixed name so the public price page keeps working automatically.
    if os.path.exists(target_path):
        os.remove(target_path)
    file.save(target_path)

    flash(f"Updated PDF for {brand_slug} in {category_slug}.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    if request.method == "POST":
        config = load_admin_config()
        current = request.form.get("current_password", "")
        new = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        if not check_password_hash(config["password_hash"], current):
            flash("Current password is incorrect.")
        elif len(new) < 6:
            flash("New password must be at least 6 characters.")
        elif new != confirm:
            flash("New passwords do not match.")
        else:
            update_password(new)
            flash("Password changed successfully.")
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/change_password.html")


@admin_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    config = load_admin_config()
    if config is None:
        return redirect(url_for("admin.setup"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        if email != config["email"]:
            flash("No admin account uses that email.")
        else:
            otp = "".join(random.choices(string.digits, k=6))
            save_otp(email, otp)
            try:
                send_otp_email(email, otp)
                flash("A verification code has been sent to your email.")
                return redirect(url_for("admin.reset_password"))
            except Exception as e:
                flash(f"Could not send email. Check the SMTP settings in admin.py. ({e})")

    return render_template("admin/forgot_password.html")


@admin_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    config = load_admin_config()
    if config is None:
        return redirect(url_for("admin.setup"))

    if request.method == "POST":
        otp_input = request.form.get("otp", "").strip()
        new_password = request.form.get("new_password", "")
        confirm = request.form.get("confirm_password", "")

        stored = load_otp()
        if stored is None:
            flash("No reset code was requested. Start again.")
            return redirect(url_for("admin.forgot_password"))

        expired = (time.time() - stored["created_at"]) > OTP_VALID_SECONDS
        if expired:
            clear_otp()
            flash("That code has expired. Request a new one.")
            return redirect(url_for("admin.forgot_password"))

        if otp_input != stored["otp"]:
            flash("Incorrect code.")
        elif len(new_password) < 6:
            flash("Password must be at least 6 characters.")
        elif new_password != confirm:
            flash("Passwords do not match.")
        else:
            update_password(new_password)
            clear_otp()
            flash("Password reset. Please log in.")
            return redirect(url_for("admin.login"))

    return render_template("admin/reset_password.html")