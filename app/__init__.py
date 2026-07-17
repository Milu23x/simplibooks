import os
from datetime import datetime, timezone, timedelta
from flask import Flask, redirect, url_for
from config import Config
from app.extensions import db, login_manager

IST_OFFSET = timezone(timedelta(hours=5, minutes=30))

def format_datetime_ist(value, fmt="%d %b %Y, %H:%M"):
    if value is None:
        return ""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.astimezone(IST_OFFSET).strftime(fmt)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app.auth.routes import auth_bp
    from app.shopkeeper.routes import shopkeeper_bp
    from app.admin.routes import admin_bp
    from app.public.routes import public_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shopkeeper_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(public_bp)

    @app.route("/")
    def index():
        return redirect(url_for("public.marketplace"))

    # convenience redirects: allow visiting /login and /register without the /auth prefix
    @app.route("/login")
    def login_short():
        return redirect(url_for("auth.login"))

    @app.route("/register")
    def register_short():
        return redirect(url_for("auth.register"))

    @app.context_processor
    def inject_globals():
        from datetime import datetime
        return {
            "current_year": datetime.utcnow().year,
            "format_datetime_ist": format_datetime_ist,
        }

    app.add_template_filter(format_datetime_ist, "ist_datetime")

    with app.app_context():
        db.create_all()
        _seed_defaults()

    return app


def _seed_defaults():
    """Create a default admin account and a few starter categories/tax rates
    the first time the app runs, so the platform isn't empty on first login."""
    from app.models import User, ExpenseCategory, TaxRate

    if not User.query.filter_by(role="admin").first():
        admin = User(name="Platform Admin", email="admin@simplibooks.com", role="admin", status="active")
        admin.set_password("Admin@123")
        db.session.add(admin)

    if ExpenseCategory.query.count() == 0:
        for name in ["Rent", "Salary", "Inventory/Stock Purchase", "Utilities", "Transport", "Miscellaneous"]:
            db.session.add(ExpenseCategory(name=name))

    if TaxRate.query.count() == 0:
        for label, pct in [("GST 0%", 0), ("GST 5%", 5), ("GST 12%", 12), ("GST 18%", 18), ("GST 28%", 28)]:
            db.session.add(TaxRate(label=label, percentage=pct, is_active=True))

    db.session.commit()
