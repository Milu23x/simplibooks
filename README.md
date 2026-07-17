# SimpliBooks

A web-based bookkeeping and GST-ready invoicing platform for small shopkeepers —
built to match the project report ("SimpliBooks — A Web-Based Self-Accounting &
Invoicing Platform"). Frontend: HTML + Bootstrap + Chart.js (server-rendered via
Jinja2). Backend: Python Flask + SQLAlchemy. Database: MySQL (SQLite also works
for quick local testing).

## Features implemented

**Shopkeeper**
- Register / login, own business profile
- Create GST-calculated invoices (multiple line items, auto tax + total)
- Download invoice as PDF
- Record payments against an invoice (tracks balance due)
- Log expenses against admin-defined categories, with receipt upload
- Dashboard: income / expenses / profit this month, 6-month trend chart, outstanding balance
- Reports: date-range filter, income/expense/profit totals, GST collected, estimated tax liability
- Search/filter invoices by customer

**Admin**
- Separate role, same login page, routed to its own dashboard
- View / suspend / reactivate / delete shopkeeper accounts
- Add / remove expense categories (shared platform-wide)
- Add / activate / deactivate GST tax rate slabs
- Broadcast announcements to all shopkeepers
- Platform-wide stats + recent activity/audit log

Role checks are enforced server-side (`app/decorators.py: role_required`), not
just hidden in the UI — a shopkeeper session gets a 403 on any `/admin/*` route
and vice versa.

## 1. Setup

```bash
cd simplibooks
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **WeasyPrint (PDF export)** also needs a couple of system libraries.
> - Ubuntu/Debian: `sudo apt-get install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev`
> - macOS: `brew install pango`
> If you skip this, everything else still works — the "Download PDF" button
> will just show a friendly error instead of a PDF.

## 2. Configure the database

Copy `.env.example` to `.env` and fill in your MySQL credentials:

```bash
cp .env.example .env
```

```
SECRET_KEY=some-long-random-string
DATABASE_URL=mysql+pymysql://simplibooks_user:your_password@localhost:3306/simplibooks
```

Then create the database and user in MySQL:

```sql
CREATE DATABASE simplibooks CHARACTER SET utf8mb4;
CREATE USER 'simplibooks_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON simplibooks.* TO 'simplibooks_user'@'localhost';
FLUSH PRIVILEGES;
```

Tables are created automatically the first time the app runs (`db.create_all()`
in `app/__init__.py`) — no separate migration step needed to get started.

**Don't have MySQL installed yet and just want to try it first?** Set
`DATABASE_URL=sqlite:///simplibooks.db` in `.env` instead — everything works
identically, it just uses a local file instead of a MySQL server.

## 3. Run

```bash
python run.py
```

Visit **http://127.0.0.1:5000**

## 4. Logging in

- **Shopkeeper:** register a new account at `/auth/register`.
- **Admin:** a default admin account is auto-created the first time the app runs:
  - Email: `admin@simplibooks.com`
  - Password: `Admin@123`

  Change this password (or the seed logic in `_seed_defaults()` in
  `app/__init__.py`) before deploying anywhere real.

## Project structure

```
simplibooks/
  run.py                  # entry point
  config.py                # reads .env, builds SQLALCHEMY_DATABASE_URI
  requirements.txt
  app/
    __init__.py            # app factory, seeds default admin/categories/tax rates
    extensions.py           # db, login_manager instances
    models.py                # all SQLAlchemy models (matches the report's schema)
    decorators.py            # @role_required("shopkeeper" | "admin")
    auth/                    # register, login, logout
    shopkeeper/               # dashboard, invoices, expenses, reports, profile
    admin/                     # dashboard, shopkeepers, categories, tax rates, announcements
    templates/                 # Jinja2 + Bootstrap 5 templates
    static/css, static/js       # styling
    static/uploads/receipts/     # uploaded expense receipts land here
```

## What's next (see report's "Future Scope")

- Direct GST e-filing integration
- Bank statement import
- OCR-based receipt categorization
- Mobile app
- Multi-business support per login

## Notes on the "estimated tax liability" figure

The number shown in Reports is a simple illustrative estimate (a flat
percentage of net profit) meant to give the shopkeeper a rough planning
number — it is **not** a real tax calculation and shouldn't be filed as one.
Swap the logic in `shopkeeper/routes.py: reports()` for real slab-based rules
if you take this further.
