from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user

from app.extensions import db
from app.models import User, Business, Invoice, Expense, ExpenseCategory, TaxRate, AuditLog, Notification, Complaint
from app.decorators import role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin", template_folder="../templates/admin")


def _log(action):
    db.session.add(AuditLog(user_id=current_user.id, action=action))
    db.session.commit()


@admin_bp.route("/dashboard")
@login_required
@role_required("admin")
def dashboard():
    total_shopkeepers = User.query.filter_by(role="shopkeeper").count()
    active_shopkeepers = User.query.filter_by(role="shopkeeper", status="active").count()
    total_invoices = Invoice.query.count()
    total_expenses = Expense.query.count()
    recent_activity = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(15).all()

    return render_template(
        "admin/dashboard.html",
        total_shopkeepers=total_shopkeepers,
        active_shopkeepers=active_shopkeepers,
        total_invoices=total_invoices,
        total_expenses=total_expenses,
        recent_activity=recent_activity,
    )


# ------------------------------------------------------------ shopkeepers
@admin_bp.route("/shopkeepers")
@login_required
@role_required("admin")
def shopkeepers():
    search = request.args.get("q", "").strip()
    q = User.query.filter_by(role="shopkeeper")
    if search:
        q = q.filter(User.name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    users = q.order_by(User.created_at.desc()).all()
    return render_template("admin/shopkeepers.html", users=users, search=search)


@admin_bp.route("/shopkeepers/<int:user_id>/toggle-status", methods=["POST"])
@login_required
@role_required("admin")
def toggle_shopkeeper_status(user_id):
    user = User.query.filter_by(id=user_id, role="shopkeeper").first_or_404()
    user.status = "suspended" if user.status == "active" else "active"
    db.session.commit()
    _log(f"{'Suspended' if user.status == 'suspended' else 'Reactivated'} shopkeeper {user.email}")
    flash(f"{user.name}'s account is now {user.status}.", "info")
    return redirect(url_for("admin.shopkeepers"))


@admin_bp.route("/shopkeepers/<int:user_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_shopkeeper(user_id):
    user = User.query.filter_by(id=user_id, role="shopkeeper").first_or_404()
    email = user.email
    db.session.delete(user)
    db.session.commit()
    _log(f"Deleted shopkeeper {email}")
    flash("Shopkeeper account removed.", "info")
    return redirect(url_for("admin.shopkeepers"))


# ------------------------------------------------------------ categories
@admin_bp.route("/categories", methods=["GET", "POST"])
@login_required
@role_required("admin")
def categories():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if name and not ExpenseCategory.query.filter_by(name=name).first():
            db.session.add(ExpenseCategory(name=name))
            db.session.commit()
            _log(f"Added expense category '{name}'")
            flash("Category added.", "success")
        else:
            flash("Category name is empty or already exists.", "danger")
        return redirect(url_for("admin.categories"))

    cats = ExpenseCategory.query.order_by(ExpenseCategory.name).all()
    return render_template("admin/categories.html", categories=cats)


@admin_bp.route("/categories/<int:cat_id>/delete", methods=["POST"])
@login_required
@role_required("admin")
def delete_category(cat_id):
    cat = ExpenseCategory.query.get_or_404(cat_id)
    db.session.delete(cat)
    db.session.commit()
    flash("Category removed.", "info")
    return redirect(url_for("admin.categories"))


# ------------------------------------------------------------ tax rates
@admin_bp.route("/tax-rates", methods=["GET", "POST"])
@login_required
@role_required("admin")
def tax_rates():
    if request.method == "POST":
        label = request.form.get("label", "").strip()
        percentage = request.form.get("percentage", "")
        try:
            percentage = float(percentage)
        except ValueError:
            flash("Percentage must be a number.", "danger")
            return redirect(url_for("admin.tax_rates"))

        if label:
            db.session.add(TaxRate(label=label, percentage=percentage, is_active=True))
            db.session.commit()
            _log(f"Added tax rate '{label}' ({percentage}%)")
            flash("Tax rate added.", "success")
        return redirect(url_for("admin.tax_rates"))

    rates = TaxRate.query.order_by(TaxRate.percentage).all()
    return render_template("admin/tax_rates.html", tax_rates=rates)


@admin_bp.route("/tax-rates/<int:rate_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def toggle_tax_rate(rate_id):
    rate = TaxRate.query.get_or_404(rate_id)
    rate.is_active = not rate.is_active
    db.session.commit()
    return redirect(url_for("admin.tax_rates"))


# ------------------------------------------------------------ complaints
@admin_bp.route("/complaints")
@login_required
@role_required("admin")
def complaints():
    rows = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template("admin/complaints.html", complaints=rows)


@admin_bp.route("/complaints/<int:complaint_id>/toggle", methods=["POST"])
@login_required
@role_required("admin")
def toggle_complaint(complaint_id):
    c = Complaint.query.get_or_404(complaint_id)
    c.status = "resolved" if c.status == "open" else "open"
    db.session.commit()
    flash("Complaint marked as " + c.status + ".", "info")
    return redirect(url_for("admin.complaints"))


# ------------------------------------------------------------ announcements
@admin_bp.route("/announcements", methods=["GET", "POST"])
@login_required
@role_required("admin")
def announcements():
    if request.method == "POST":
        message = request.form.get("message", "").strip()
        if message:
            shopkeepers_list = User.query.filter_by(role="shopkeeper").all()
            for sk in shopkeepers_list:
                db.session.add(Notification(user_id=sk.id, message=message))
            db.session.commit()
            _log(f"Broadcast announcement: {message[:60]}")
            flash(f"Announcement sent to {len(shopkeepers_list)} shopkeeper(s).", "success")
        return redirect(url_for("admin.announcements"))

    past = Notification.query.order_by(Notification.date.desc()).limit(20).all()
    return render_template("admin/announcements.html", past=past)
