# Alam Telecom — Website (Python / Flask)

Mobile spare-parts + repair shop website with an admin panel to manage
price-list PDFs.

## Folder structure

```
alam_telecom/
├── app.py                      # Main Flask app (public routes + config)
├── admin.py                    # Admin panel (login, OTP reset, PDF upload)
├── requirements.txt
├── templates/
│   ├── base.html               # shared header, nav, footer
│   ├── index.html              # Home page
│   ├── contact.html            # Contact page
│   ├── prices.html             # Parts Price - category list
│   ├── price_category.html     # Parts Price - brand buttons for a category
│   └── admin/                  # Admin panel pages
│       ├── setup.html
│       ├── login.html
│       ├── forgot_password.html
│       ├── reset_password.html
│       ├── change_password.html
│       └── dashboard.html
└── static/
    ├── css/style.css           # black/orange site theme
    ├── css/admin.css           # admin panel theme
    ├── js/script.js
    ├── images/logo.jpeg
    ├── images/brands/          # brand logo PNGs
    └── pdfs/
        ├── display/            # display.pdf per brand goes here
        └── battery/            # battery.pdf per brand goes here
```

## How to run

1. Install Python 3.9+ if you don't have it.
2. Open a terminal in this folder and run:
   ```
   pip install -r requirements.txt
   python app.py
   ```
3. Open `http://127.0.0.1:8080/` in your browser.

## Where to edit things

- **Shop name, phone, WhatsApp, address, hours, experience** → top of `app.py`, `STORE_INFO`.
- **Services / categories / brand list on Home** → `SERVICES`, `CATEGORIES`, `BRANDS` in `app.py`.
- **Parts Price categories & brand groupings** → `PRICE_CATEGORIES` and `BRAND_GROUPS` in `app.py`.
- **Colors / fonts** → CSS variables at the top of `static/css/style.css`.

## Admin Panel (Manage Price PDFs)

Visit `http://127.0.0.1:8080/admin` in your browser.

**First time:** you'll be asked to create an admin account (email + password
of your choice — this is a separate login, not your Gmail password).

**After that:** log in at `/admin/login` to reach the dashboard, where you
can upload/replace the price PDF for every brand button. Uploading a new
PDF automatically deletes the old one first — no manual cleanup needed.

**Forgot password:** click "Forgot password?" on the login page. A 6-digit
code is emailed to the admin address, valid for 10 minutes.

**Change password:** while logged in, use "Change Password" in the top nav.

### One-time setup for the "forgot password" email

The reset code is emailed from `mdmhfooz7105@gmail.com` via Gmail's SMTP.
Gmail requires an **App Password** (not your normal Gmail password):

1. Go to your Google Account → Security → 2-Step Verification (already ON).
2. Scroll to **App Passwords**, create one (name it anything, e.g. "Alam
   Telecom Site"), and copy the 16-character code Google shows you.
3. Open `admin.py`, find `SMTP_CONFIG` near the top, and paste that code in
   place of `PASTE_YOUR_16_CHAR_GMAIL_APP_PASSWORD_HERE`.
4. Save and restart the server.

Everything else (login, dashboard, PDF uploads, change password while
logged in) works without this — only "forgot password" needs it.

### Where admin data is stored

- `instance/admin_config.json` — admin email + password (hashed, never
  plain text). Created automatically the first time you visit `/admin`.
- `instance/secret_key.txt` — random key for login sessions, auto-created.
- Neither file is something you create by hand, and neither is included in
  what's delivered to you — they appear on your machine the first time you
  run the app.
- **Do not share these files or upload them publicly** (e.g. to GitHub) —
  they protect the admin login.

## Notes

- The map on the Contact page is a placeholder — swap it for a Google Maps
  embed `<iframe>` with your shop's real address.
- Deploy anywhere that runs Flask (PythonAnywhere, Render, Railway, a VPS
  with gunicorn, etc.) — the admin login and PDF storage work the same way
  there too.