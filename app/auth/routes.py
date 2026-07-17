from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import User, Business, AuditLog
from app.auth.forms import RegisterForm, LoginForm, BuyerRegisterForm

auth_bp = Blueprint("auth", __name__, url_prefix="/auth", template_folder="../templates/auth")


def _log(user_id, action):
    db.session.add(AuditLog(user_id=user_id, action=action))
    db.session.commit()


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for("admin.dashboard"))
        if current_user.is_buyer():
            return redirect(url_for("public.marketplace"))
        return redirect(url_for("shopkeeper.dashboard"))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", form=form)

        user = User(name=form.name.data.strip(), email=email, role="shopkeeper", status="active")
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        business = Business(user_id=user.id, business_name=form.business_name.data.strip())
        db.session.add(business)
        db.session.commit()

        _log(user.id, "Account registered")
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/register/buyer", methods=["GET", "POST"])
def register_buyer():
    if current_user.is_authenticated:
        return redirect(url_for("public.marketplace"))

    form = BuyerRegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        if User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register_buyer.html", form=form)

        user = User(
            name=form.name.data.strip(), email=email, phone=form.phone.data.strip(),
            role="buyer", status="active",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        _log(user.id, "Buyer account registered")
        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register_buyer.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for("admin.dashboard"))
        if current_user.is_buyer():
            return redirect(url_for("public.marketplace"))
        return redirect(url_for("shopkeeper.dashboard"))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter_by(email=email).first()
        if user is not None and user.check_password(form.password.data):
            if user.status == "suspended":
                flash("This account has been suspended. Contact the platform admin.", "danger")
                return render_template("auth/login.html", form=form)
            login_user(user)
            _log(user.id, "Logged in")
            next_page = request.args.get("next")
            if user.is_admin():
                return redirect(next_page or url_for("admin.dashboard"))
            if user.is_buyer():
                return redirect(next_page or url_for("public.marketplace"))
            return redirect(next_page or url_for("shopkeeper.dashboard"))
        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    _log(current_user.id, "Logged out")
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
