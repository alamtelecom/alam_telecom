# admin.py

"""
Admin panel: login, password change/reset (via Resend API), PDF uploads
for the Parts Price section, partner management, and admin email change.

All admin state (login email, hashed password) is kept in
instance/admin_config.json, created automatically the first time you visit
/admin (first-time setup).
"""

import json
import os
import random
import string
import time
from functools import wraps

from dotenv import load_dotenv
from flask import (
    Blueprint, current_app, flash, redirect, render_template,
    request, session, url_for,
)
import resend
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# Load environment variables from .env file
load_dotenv()

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

INSTANCE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
CONFIG_PATH = os.path.join(INSTANCE_DIR, "admin_config.json")
OTP_PATH = os.path.join(INSTANCE_DIR, "otp.json")
OTP_VALID_SECONDS = 10 * 60  # 10 minutes

# ---------------------------------------------------------------------------
# Resend API Configuration (Loaded securely from .env or system environment)
# ---------------------------------------------------------------------------
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
resend.api_key = RESEND_API_KEY


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


def update_email(new_email):
    config = load_admin_config()
    config["email"] = new_email
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
# Email sending via Resend HTTP API (Verified Domain)
# ---------------------------------------------------------------------------
def send_otp_email(to_email, otp):
    params = {
        "from": "Alam Telecom <admin@alamtelecom.shop>",
        "to": [to_email],
        "subject": "Alam Telecom Admin - Verification Code",
        "text": (
            f"Your Alam Telecom verification code is: {otp}\n\n"
            f"This code expires in 10 minutes. If you didn't request this, ignore this email."
        ),
    }
    resend.Emails.send(params)


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
        if email.lower() == config["email"].lower() and check_password_hash(config["password_hash"], password):
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
        if not config or email.lower() != config.get("email", "").lower():
            flash("No admin account uses that email.")
        else:
            try:
                otp = "".join(random.choices(string.digits, k=6))
                save_otp(email, otp)
                send_otp_email(email, otp)
                flash("A verification code has been sent to your email.")
                return redirect(url_for("admin.reset_password"))
            except Exception as e:
                flash(f"Could not send email: {e}")

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


# ---------------------------------------------------------------------------
# Change Admin Email (with OTP Verification)
# ---------------------------------------------------------------------------
@admin_bp.route("/change-email", methods=["GET", "POST"])
@login_required
def change_email():
    config = load_admin_config()
    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_email = request.form.get("new_email", "").strip().lower()

        if not check_password_hash(config["password_hash"], current_password):
            flash("Current password is incorrect.")
        elif not new_email or "@" not in new_email:
            flash("Please enter a valid new email address.")
        elif new_email == config["email"].lower():
            flash("New email must be different from the current email.")
        else:
            try:
                otp = "".join(random.choices(string.digits, k=6))
                save_otp(config["email"], otp)
                session["pending_new_email"] = new_email
                send_otp_email(config["email"], otp)
                flash(f"Verification code sent to your current email ({config['email']}).")
                return redirect(url_for("admin.verify_change_email"))
            except Exception as e:
                flash(f"Could not send email: {e}")

    return render_template("admin/change_email.html", current_email=config["email"])


@admin_bp.route("/verify-change-email", methods=["GET", "POST"])
@login_required
def verify_change_email():
    new_email = session.get("pending_new_email")
    if not new_email:
        flash("No email change in progress. Please start again.")
        return redirect(url_for("admin.change_email"))

    if request.method == "POST":
        otp_input = request.form.get("otp", "").strip()
        stored = load_otp()

        if stored is None:
            flash("No verification code found. Request a new one.")
            return redirect(url_for("admin.change_email"))

        if (time.time() - stored["created_at"]) > OTP_VALID_SECONDS:
            clear_otp()
            session.pop("pending_new_email", None)
            flash("Verification code expired. Please start again.")
            return redirect(url_for("admin.change_email"))

        if otp_input != stored["otp"]:
            flash("Incorrect verification code.")
        else:
            update_email(new_email)
            clear_otp()
            session.pop("pending_new_email", None)
            flash(f"Admin email updated successfully to {new_email}.")
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/verify_change_email.html", new_email=new_email)


# ---------------------------------------------------------------------------
# Partners (Collaborations) Management
# ---------------------------------------------------------------------------
PARTNERS_PATH = os.path.join(INSTANCE_DIR, "partners.json")
ALLOWED_LOGO_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".svg"}


def load_partners():
    _ensure_instance_dir()
    if not os.path.exists(PARTNERS_PATH):
        return [
            {
                "id": "mobicrown",
                "name": "MOBICROWN",
                "logo": "images/brands/mobicrown.png",
                "desc": "We've officially collaborated with MOBICROWN to bring you genuine batteries, earbuds and chargers.",
                "desc_hi": "हमने MOBICROWN के साथ आधिकारिक सहयोग किया है ताकि आपको असली बैटरी, ईयरबड्स और चार्जर मिल सकें।",
                "badge_en": "Authorized Partner",
                "badge_hi": "अधिकृत पार्टनर",
                "tags": ["Battery", "Earbuds", "Charger"],
            },
            {
                "id": "am-plus",
                "name": "AM PLUS",
                "logo": "images/brands/am_plus.png",
                "desc": "We work with AM Plus for display work — quality screens sourced and fitted through them.",
                "desc_hi": "हम डिस्प्ले के काम के लिए AM Plus के साथ काम करते हैं — अच्छी क्वालिटी की स्क्रीन इन्हीं के ज़रिए मंगवाते और फिट करते हैं।",
                "badge_en": "Display Associate",
                "badge_hi": "डिस्प्ले एसोसिएट",
                "tags": ["Display"],
            }
        ]
    with open(PARTNERS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_partners(partners):
    _ensure_instance_dir()
    with open(PARTNERS_PATH, "w", encoding="utf-8") as f:
        json.dump(partners, f, ensure_ascii=False, indent=2)


def _unique_partner_id(name, existing_partners):
    base = "".join(c if c.isalnum() else "_" for c in name.lower()).strip("_") or "partner"
    existing_ids = {p.get("id") for p in existing_partners}
    slug = base
    n = 1
    while slug in existing_ids:
        slug = f"{base}_{n}"
        n += 1
    return slug


@admin_bp.route("/partners", methods=["GET"])
@login_required
def partners():
    partners_list = load_partners()
    return render_template("admin/partners.html", partners=partners_list)


@admin_bp.route("/partners/add", methods=["POST"])
@login_required
def add_partner():
    name = request.form.get("name", "").strip()
    desc = request.form.get("desc", "").strip()
    desc_hi = request.form.get("desc_hi", "").strip()
    badge_en = request.form.get("badge_en", "").strip() or "Authorized Partner"
    badge_hi = request.form.get("badge_hi", "").strip() or "अधिकृत पार्टनर"
    tags_raw = request.form.get("tags", "").strip()
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

    if not name:
        flash("Partner name is required.")
        return redirect(url_for("admin.partners"))
    if not desc:
        flash("Description (English) is required.")
        return redirect(url_for("admin.partners"))

    logo_file = request.files.get("logo_file")
    if not logo_file or logo_file.filename == "":
        flash("Please choose a logo image.")
        return redirect(url_for("admin.partners"))

    _, ext = os.path.splitext(logo_file.filename.lower())
    if ext not in ALLOWED_LOGO_EXTS:
        flash("Logo must be PNG, JPG, WEBP or SVG.")
        return redirect(url_for("admin.partners"))

    all_partners = load_partners()
    partner_id = _unique_partner_id(name, all_partners)

    target_dir = os.path.join(current_app.static_folder, "images", "partners")
    os.makedirs(target_dir, exist_ok=True)
    filename = secure_filename(f"{partner_id}{ext}")
    target_path = os.path.join(target_dir, filename)
    logo_file.save(target_path)

    new_p = {
        "id": partner_id,
        "name": name,
        "logo": f"images/partners/{filename}",
        "desc": desc,
        "desc_hi": desc_hi or desc,
        "badge_en": badge_en,
        "badge_hi": badge_hi,
        "tags": tags,
    }
    all_partners.append(new_p)
    save_partners(all_partners)

    flash(f"Partner '{name}' added successfully.")
    return redirect(url_for("admin.partners"))


@admin_bp.route("/partners/<partner_id>/delete", methods=["POST"])
@login_required
def delete_partner(partner_id):
    all_partners = load_partners()
    target = next((p for p in all_partners if p.get("id") == partner_id), None)
    if not target:
        flash("Partner not found.")
        return redirect(url_for("admin.partners"))

    logo = target.get("logo", "")
    if logo.startswith("images/partners/"):
        img_path = os.path.join(current_app.static_folder, logo)
        if os.path.exists(img_path):
            os.remove(img_path)

    all_partners = [p for p in all_partners if p.get("id") != partner_id]
    save_partners(all_partners)

    flash(f"Partner '{target.get('name')}' removed.")
    return redirect(url_for("admin.partners"))