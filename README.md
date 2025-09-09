# Ficore Labs (DIICE) - Full Stack Business Management Platform

## Overview
Ficore Labs (DIICE) is a modern, modular, and habit-forming business management platform designed for African entrepreneurs and traders. It provides daily-use incentives, actionable insights, and a robust set of tools to help users manage finances, inventory, compliance, and growth—all in a secure, mobile-friendly, and extensible environment. The platform now features a single streamlined user experience for entrepreneurs/traders, with a dedicated admin account for system management.

---

## Features
- **Smart Reminders**: Daily log reminders, streak tracking, and engagement banners.
- **Quick Log Buttons**: Fast entry for sales, expenses, and inventory.
- **Visual Progress & Charts**: Dashboard with profit/loss, streaks, and financial health charts (Chart.js).
- **Streaks & Gamification**: Track daily usage streaks and reward consistency.
- **Profit Summary PDF**: Downloadable profit/loss reports (PDF via ReportLab).
- **Debt Tracker**: Alerts for unpaid debts/credits, with quick links to manage.
- **Tax Prep Mode**: Toggle to show only true profit for tax purposes.
- **Inventory Loss Detector**: Alerts when inventory cost exceeds expected margins.
- **Inventory Management**: Full CRUD for inventory items, with dedicated module and UI.
- **Modular Blueprints**: Each business area (dashboard, creditors, debtors, inventory, etc.) is a Flask blueprint for maintainability.
- **User Management**: Secure authentication, trial/subscription logic, and a dedicated admin account for management and monitoring.
- **Notifications**: In-app notifications for key events and reminders.
- **Internationalization**: Multi-language support (English, Hausa).
- **PWA Support**: Installable, offline-capable web app with manifest and service worker.
- **Responsive UI**: Mobile-first, Bootstrap-based design.

---

## Tech Stack
- **Backend**: Python 3, Flask, Flask-Login, Flask-Session, Flask-Babel, Flask-Limiter, Flask-CORS, Flask-WTF, Flask-Compress
- **Database**: MongoDB (via PyMongo)
- **Frontend**: Jinja2 templates, Bootstrap 5, Chart.js, custom CSS/JS
- **PDF Generation**: ReportLab
- **Internationalization**: Flask-Babel, translation files
- **PWA**: Manifest.json, Service Worker (sw.js)
- **Deployment**: WSGI (wsgi.py), Render.com/Heroku/Cloud
- **Other**: dotenv for config, logging, CSRF protection, CORS, session management

---

## Main App Sections
- **Dashboard**: Central hub for reminders, charts, streaks, and alerts.
- **Inventory**: Add, view, and manage inventory items. Loss detection and margin tracking.
- **Debtors & Creditors**: Track who owes you and whom you owe. Alerts for unpaid items.
- **Receipts & Payments**: Record and manage all cashflows.
- **Reports**: Generate and download profit/loss summaries.
- **Settings**: User profile, preferences, and language selection.
- **Admin**: (Management only) User monitoring, KYC and subscription management, and system settings. Admin account is auto-created for system management (see below).
- **Notifications**: In-app alerts and reminders.
- **KYC & Compliance**: Upload and manage compliance documents.
- **Subscribe**: Manage trial, subscription, and plan upgrades.

---

## Directory Structure (Key Folders)
- `ficore_labs/` - Main app package
  - `app.py` - App factory, blueprint registration
  - `models.py` - Data models and initialization
  - `utils.py` - Utility functions (DB, logging, etc.)
  - `helpers/` - Custom business logic (reminders, streaks, inventory loss, etc.)
  - `templates/` - Jinja2 templates (modular by section)
  - `static/` - CSS, JS, images, manifest, service worker
  - `blueprints/` - All Flask blueprints for business areas (e.g., `blueprints/admin/routes.py`, `blueprints/dashboard/routes.py`, etc.)

---

## Getting Started
1. **Clone the repo**
2. `pip install -r requirements.txt`
3. Set up `.env` with `SECRET_KEY` and `MONGO_URI`
4. Run with `python -m ficore_labs.app` or `flask run`
5. Access at `http://localhost:5000`

### Default Admin Account
- Username: `admin`
- Password: `Admin123!`
This account is auto-created for management purposes (user monitoring, KYC, subscriptions, and record corrections). All other users are entrepreneurs/traders by default.

---

## Contributing
- PRs welcome! Please follow PEP8 and keep features modular.
- For translations, update the relevant files in `translations/`.
- For new blueprints, add them under `blueprints/` and import as `from blueprints.<name>.routes import <name>_bp` in `app.py`.

---

## License
MIT (c) Ficore Labs, 2025
