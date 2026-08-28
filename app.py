import os
import secrets

from flask import Flask, render_template

from admin import admin_bp

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Secret key: needed for admin login sessions. Auto-generated once and saved
# to instance/secret_key.txt so it stays the same across restarts (if it
# changed every restart, everyone would get logged out each time you run
# the app).
# ---------------------------------------------------------------------------
_instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "instance")
os.makedirs(_instance_dir, exist_ok=True)
_secret_key_path = os.path.join(_instance_dir, "secret_key.txt")
if not os.path.exists(_secret_key_path):
    with open(_secret_key_path, "w") as f:
        f.write(secrets.token_hex(32))
with open(_secret_key_path, "r") as f:
    app.secret_key = f.read().strip()

# ---------------------------------------------------------------------------
# Store info - edit these values to update contact details site-wide
# ---------------------------------------------------------------------------
STORE_INFO = {
    "name": "Alam Telecom",
    "tagline": "A to Z Mobile Parts & Repairing",
    "phone": "9910732766",
    "whatsapp": "919910732766",  # country code + number, no + or spaces
    "address_line1": "Opposite Metro Station Gate No. 2, NK Complex, Shop No. 2",
    "address_line2": "Najafgarh, New Delhi",
    "hours_main": "10:00 AM - 9:30 PM (All days)",
    "hours_note": "Wednesday: Half day, 10:00 AM - 2:00 PM only",
    "experience_years": "11",
}

SERVICES = [
    {
        "name": "Genuine Spare Parts",
        "desc": "Displays, batteries, charging ports, camera modules, speakers, motherboard parts and more \u2014 for every major brand. Charging cables are genuine and sold as new, not repaired.",
    },
    {
        "name": "Mobile Repairing",
        "desc": "In-house repairing service for all phone brands, done by experienced technicians at the shop.",
    },
]

CATEGORIES = [
    {"name": "Displays & Touch Screens", "icon": "display"},
    {"name": "Batteries", "icon": "battery"},
    {"name": "Charging Ports & Flex Cables", "icon": "charging"},
    {"name": "Camera Modules", "icon": "camera"},
    {"name": "Speakers & Ringers", "icon": "speaker"},
    {"name": "Motherboard Parts", "icon": "board"},
    {"name": "Back Panels & Housing", "icon": "panel"},
    {"name": "Charging Cables & Adapters (Genuine, Sold New)", "icon": "cable"},
]

# filename (without extension) must match an image in static/images/brands/
# e.g. BRANDS entry "Vivo" looks for static/images/brands/vivo.png
BRANDS = [
    "iPhone", "Samsung", "Pixel", "Nothing", "OnePlus", "Oppo", "Vivo",
    "Realme", "iQOO", "Tecno", "Infinix", "Moto", "Itel", "Lava",
]

# ---------------------------------------------------------------------------
# Price list PDFs.
#
# Two levels:
#   1. Parts Price page shows categories (Display, Battery, ...)
#   2. Clicking a category shows brand buttons; clicking a brand opens its PDF.
#
# Put PDFs in static/pdfs/<category-slug>/<brand-slug>.pdf using the exact
# slugs below. To add a new category: add an entry to PRICE_CATEGORIES and
# create the matching static/pdfs/<slug>/ folder with one PDF per brand group.
# ---------------------------------------------------------------------------
PRICE_CATEGORIES = [
    {"name": "Display", "icon": "display", "slug": "display"},
    {"name": "Battery", "icon": "battery", "slug": "battery"},
]

# Brand buttons shown inside every category. logos list = filenames (without
# .png) from static/images/brands/ used to show the logo(s) on the button.
BRAND_GROUPS = [
    {"name": "iPhone", "slug": "iphone", "logos": ["iphone"]},
    {"name": "Samsung", "slug": "samsung", "logos": ["samsung"]},
    {"name": "Nothing", "slug": "nothing", "logos": ["nothing"]},
    {"name": "Pixel", "slug": "pixel", "logos": ["pixel"]},
    {"name": "Vivo & iQOO", "slug": "vivo-iqoo", "logos": ["vivo", "iqoo"]},
    {"name": "Oppo, Realme & OnePlus", "slug": "oppo-realme-oneplus", "logos": ["oppo", "realme", "oneplus"]},
    {"name": "Motorola", "slug": "motorola", "logos": ["moto"]},
    {"name": "Infinix, Tecno & Itel", "slug": "infinix-tecno-itel", "logos": ["infinix", "tecno", "itel"]},
    {"name": "Lava", "slug": "lava", "logos": ["lava"]},
]


app.config["PRICE_CATEGORIES"] = PRICE_CATEGORIES
app.config["BRAND_GROUPS"] = BRAND_GROUPS
app.register_blueprint(admin_bp)


@app.route("/")
def index():
    return render_template(
        "index.html",
        store=STORE_INFO,
        services=SERVICES,
        categories=CATEGORIES,
        brands=BRANDS,
        active_page="home",
    )


@app.route("/contact")
def contact():
    return render_template(
        "contact.html",
        store=STORE_INFO,
        active_page="contact",
    )


@app.route("/prices")
def prices():
    return render_template(
        "prices.html",
        store=STORE_INFO,
        price_categories=PRICE_CATEGORIES,
        active_page="prices",
    )


@app.route("/prices/<slug>")
def price_category(slug):
    category = next((c for c in PRICE_CATEGORIES if c["slug"] == slug), None)
    if category is None:
        return render_template(
            "prices.html",
            store=STORE_INFO,
            price_categories=PRICE_CATEGORIES,
            active_page="prices",
        ), 404
    return render_template(
        "price_category.html",
        store=STORE_INFO,
        category=category,
        brand_groups=BRAND_GROUPS,
        active_page="prices",
    )


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False, use_reloader=False)