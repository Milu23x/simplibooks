from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    """Both shopkeepers and admins live in one table, distinguished by role."""
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="shopkeeper")  # 'shopkeeper', 'admin', or 'buyer'
    status = db.Column(db.String(20), nullable=False, default="active")   # 'active' or 'suspended'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    business = db.relationship("Business", backref="owner", uselist=False, cascade="all, delete-orphan")
    notifications = db.relationship("Notification", backref="user", cascade="all, delete-orphan")
    prebookings = db.relationship("PreBooking", backref="buyer", cascade="all, delete-orphan")

    def set_password(self, raw_password):
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self.password_hash, raw_password)

    def is_admin(self):
        return self.role == "admin"

    def is_buyer(self):
        return self.role == "buyer"


class Business(db.Model):
    __tablename__ = "businesses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    business_name = db.Column(db.String(150), nullable=False)
    gstin = db.Column(db.String(20))
    state = db.Column(db.String(80))
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))

    # Storefront discount banner (shown to shoppers on the public store page)
    banner_enabled = db.Column(db.Boolean, default=False)
    banner_title = db.Column(db.String(150))
    banner_message = db.Column(db.String(255))
    banner_discount_percent = db.Column(db.Float, default=0.0)
    banner_cta_text = db.Column(db.String(60), default="Shop Now")

    invoices = db.relationship("Invoice", backref="business", cascade="all, delete-orphan")
    expenses = db.relationship("Expense", backref="business", cascade="all, delete-orphan")
    products = db.relationship("Product", backref="business", cascade="all, delete-orphan")
    complaints = db.relationship("Complaint", backref="business", cascade="all, delete-orphan")



class ExpenseCategory(db.Model):
    """Admin-managed list of expense categories, shared platform-wide."""
    __tablename__ = "expense_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)

    expenses = db.relationship("Expense", backref="category")


class TaxRate(db.Model):
    """Admin-configured GST slabs used when creating invoices."""
    __tablename__ = "tax_rates"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(50), nullable=False)      # e.g. "GST 18%"
    percentage = db.Column(db.Float, nullable=False)       # e.g. 18.0
    is_active = db.Column(db.Boolean, default=True)


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    invoice_number = db.Column(db.String(30), nullable=False)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_state = db.Column(db.String(80))
    date = db.Column(db.Date, default=date.today)
    subtotal = db.Column(db.Float, default=0.0)
    tax_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default="unpaid")  # unpaid / partially_paid / paid
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship("InvoiceItem", backref="invoice", cascade="all, delete-orphan")
    payments = db.relationship("Payment", backref="invoice", cascade="all, delete-orphan")

    @property
    def amount_paid(self):
        return sum(p.amount_paid for p in self.payments)

    @property
    def balance_due(self):
        return round(self.total_amount - self.amount_paid, 2)


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    item_name = db.Column(db.String(150), nullable=False)
    qty = db.Column(db.Float, nullable=False, default=1)
    rate = db.Column(db.Float, nullable=False, default=0.0)
    tax_rate = db.Column(db.Float, nullable=False, default=0.0)  # percentage
    amount = db.Column(db.Float, nullable=False, default=0.0)    # qty * rate (pre-tax)


class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey("invoices.id"), nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    mode = db.Column(db.String(30), default="cash")  # 'cash' or 'upi'

    @property
    def mode_label(self):
        return {"cash": "Cash", "upi": "UPI"}.get((self.mode or "").lower(), (self.mode or "").title())


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey("expense_categories.id"))
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, default=date.today)
    receipt_image = db.Column(db.String(255))
    notes = db.Column(db.String(255))


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    action = db.Column(db.String(255), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Product(db.Model):
    """A product a shopkeeper advertises on their public storefront page,
    optionally with a discount and/or open for pre-booking."""
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), default="General")
    description = db.Column(db.String(500))
    price = db.Column(db.Float, nullable=False, default=0.0)
    discount_percent = db.Column(db.Float, default=0.0)
    image_url = db.Column(db.String(500))
    allow_prebooking = db.Column(db.Boolean, default=False)
    stock_qty = db.Column(db.Integer, default=0)  # units currently in hand, 0 = coming soon
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    prebookings = db.relationship("PreBooking", backref="product", cascade="all, delete-orphan")

    @property
    def discounted_price(self):
        pct = self.discount_percent or 0
        return round(self.price * (1 - pct / 100), 2)


class PreBooking(db.Model):
    """A shopper reserving a spot in line for a product — first booked,
    first served when new stock/first units arrive."""
    __tablename__ = "prebookings"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    customer_name = db.Column(db.String(120), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    customer_email = db.Column(db.String(150))
    notes = db.Column(db.String(255))
    status = db.Column(db.String(20), default="pending")  # pending / fulfilled / cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Complaint(db.Model):
    """Contact-us / complaint box submissions from shoppers or shopkeepers."""
    __tablename__ = "complaints"

    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey("businesses.id"), nullable=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150))
    phone = db.Column(db.String(20))
    subject = db.Column(db.String(150))
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="open")  # open / resolved
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
