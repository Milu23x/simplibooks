from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import current_user, login_required

from app.extensions import db
from app.models import Business, Product, PreBooking, Complaint
from app.decorators import role_required

public_bp = Blueprint(
    "public", __name__, url_prefix="", template_folder="../templates/public"
)


# ---------------------------------------------------------------- marketplace (buyer discovery)
@public_bp.route("/marketplace")
def marketplace():
    query = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()

    products_q = Product.query.join(Business).filter(Product.is_active.is_(True))
    if query:
        like = f"%{query}%"
        products_q = products_q.filter(db.or_(Product.name.ilike(like), Product.description.ilike(like)))
    if category:
        products_q = products_q.filter(Product.category == category)

    products = products_q.order_by(Product.created_at.desc()).all()

    categories = sorted({
        row[0] for row in db.session.query(Product.category)
        .filter(Product.is_active.is_(True), Product.category.isnot(None)).distinct()
    })

    banners = (
        Business.query.filter_by(banner_enabled=True)
        .filter(Business.banner_title.isnot(None), Business.banner_title != "")
        .all()
    )

    return render_template(
        "public/marketplace.html", products=products, categories=categories,
        banners=banners, query=query, active_category=category,
    )


# ---------------------------------------------------------------- storefront
@public_bp.route("/store/<int:business_id>")
def storefront(business_id):
    biz = Business.query.get_or_404(business_id)
    products = (
        Product.query.filter_by(business_id=biz.id, is_active=True)
        .order_by(Product.created_at.desc())
        .all()
    )
    return render_template("public/storefront.html", biz=biz, products=products)


@public_bp.route("/store/<int:business_id>/prebook/<int:product_id>", methods=["POST"])
def prebook(business_id, product_id):
    biz = Business.query.get_or_404(business_id)
    product = Product.query.filter_by(id=product_id, business_id=biz.id).first_or_404()

    if not product.allow_prebooking:
        abort(404)

    name = request.form.get("customer_name", "").strip()
    phone = request.form.get("customer_phone", "").strip()
    email = request.form.get("customer_email", "").strip()
    notes = request.form.get("notes", "").strip()

    # If a logged-in buyer is booking, use their account details as the source of truth
    buyer_id = None
    if current_user.is_authenticated and current_user.is_buyer():
        buyer_id = current_user.id
        name = name or current_user.name
        phone = phone or current_user.phone or ""
        email = email or current_user.email

    if not name or not phone:
        flash("Name and phone number are required to pre-book.", "danger")
        return redirect(request.referrer or url_for("public.storefront", business_id=biz.id))

    existing_ahead = PreBooking.query.filter_by(product_id=product.id).count()
    db.session.add(PreBooking(
        product_id=product.id, buyer_id=buyer_id, customer_name=name, customer_phone=phone,
        customer_email=email, notes=notes, status="pending",
    ))
    db.session.commit()

    flash(
        f"You're pre-booked! You are number {existing_ahead + 1} in line for "
        f"\"{product.name}\" — we'll contact you the moment stock arrives.",
        "success",
    )
    return redirect(request.referrer or url_for("public.storefront", business_id=biz.id))


# ---------------------------------------------------------------- buyer account pages
@public_bp.route("/my-prebookings")
@login_required
@role_required("buyer")
def my_prebookings():
    rows = (
        PreBooking.query.filter_by(buyer_id=current_user.id)
        .order_by(PreBooking.created_at.desc()).all()
    )
    return render_template("public/my_prebookings.html", prebookings=rows)


# ---------------------------------------------------------------- contact / complaints
@public_bp.route("/contact", methods=["GET", "POST"])
def contact():
    business_id = request.args.get("business_id", type=int)
    businesses = Business.query.order_by(Business.business_name).all()

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        subject = request.form.get("subject", "").strip()
        message = request.form.get("message", "").strip()
        biz_id = request.form.get("business_id") or None

        if not name or not message:
            flash("Please enter your name and a message.", "danger")
            return render_template("public/contact.html", businesses=businesses, business_id=business_id)

        db.session.add(Complaint(
            business_id=int(biz_id) if biz_id else None,
            name=name, email=email, phone=phone, subject=subject, message=message,
        ))
        db.session.commit()
        flash("Thanks — your message has been received. We'll get back to you soon.", "success")
        return redirect(url_for("public.contact"))

    return render_template("public/contact.html", businesses=businesses, business_id=business_id)
