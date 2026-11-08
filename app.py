import os
import uuid
from datetime import datetime
from functools import wraps

from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    abort, send_from_directory
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user
)
from sqlalchemy import or_
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, Category, Item, Message

app = Flask(__name__)
app.config.from_object(Config)
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access that page."

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def admin_required(view):
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapped

@app.context_processor
def inject_template_globals():
    return {"now_year": datetime.utcnow().year}

@app.context_processor
def inject_unread_count():
    if current_user.is_authenticated:
        count = Message.query.filter_by(
            receiver_id=current_user.user_id, is_read=False
        ).count()
        return {"unread_message_count": count}
    return {"unread_message_count": 0}

@app.route("/")
def index():
    latest_items = Item.query.filter_by(status="active").order_by(
        Item.created_at.desc()
    ).limit(6).all()
    return render_template("index.html", latest_items=latest_items)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        if not all([name, email, password, confirm]):
            flash("Please complete all required fields.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with this email already exists.", "error")
        else:
            user = User(
                name=name, email=email, phone=phone or None,
                password_hash=generate_password_hash(password), role="student"
            )
            db.session.add(user)
            db.session.commit()
            flash("Registration successful. Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            flash("Welcome back!", "success")
            next_page = request.args.get("next")
            if next_page and next_page.startswith("/") and not next_page.startswith("//"):
                return redirect(next_page)
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))

@app.route("/dashboard")
@login_required
def dashboard():
    my_items = Item.query.filter_by(user_id=current_user.user_id).order_by(
        Item.created_at.desc()
    ).limit(5).all()
    total_reports = Item.query.filter_by(user_id=current_user.user_id).count()
    unread_count = Message.query.filter_by(
        receiver_id=current_user.user_id, is_read=False
    ).count()
    return render_template(
        "dashboard.html", my_items=my_items,
        total_reports=total_reports, unread_count=unread_count
    )

@app.route("/report-item", methods=["GET", "POST"])
@login_required
def report_item():
    categories = Category.query.order_by(Category.category_name).all()
    selected_type = request.args.get("type", "").lower()
    if selected_type not in ("lost", "found"):
        selected_type = ""

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        listing_type = request.form.get("listing_type", "").lower()
        category_id = request.form.get("category_id", "")
        location = request.form.get("location", "").strip()
        date_text = request.form.get("date_lost_found", "").strip()
        image = request.files.get("image")
        selected_type = listing_type if listing_type in ("lost", "found") else ""

        try:
            category_id = int(category_id)
            category = db.session.get(Category, category_id)
        except (ValueError, TypeError):
            category = None

        try:
            item_date = datetime.strptime(date_text, "%Y-%m-%d").date()
        except ValueError:
            item_date = None

        if not all([title, description, location, item_date, category]):
            flash("Please complete all required fields with valid values.", "error")
        elif listing_type not in ("lost", "found"):
            flash("Select whether the item was lost or found.", "error")
        elif image and image.filename and not allowed_file(image.filename):
            flash("Unsupported image format.", "error")
        else:
            saved_filename = None
            try:
                if image and image.filename:
                    extension = secure_filename(image.filename).rsplit(".", 1)[1].lower()
                    saved_filename = f"{uuid.uuid4().hex}.{extension}"
                    image.save(os.path.join(app.config["UPLOAD_FOLDER"], saved_filename))

                item = Item(
                    user_id=current_user.user_id,
                    category_id=category.category_id,
                    title=title,
                    description=description,
                    listing_type=listing_type,
                    location=location,
                    date_lost_found=item_date,
                    image_filename=saved_filename,
                    status="active"
                )
                db.session.add(item)
                db.session.commit()
                flash("Your item report has been submitted.", "success")
                return redirect(url_for("my_reports"))
            except Exception:
                db.session.rollback()
                if saved_filename:
                    try:
                        os.remove(os.path.join(app.config["UPLOAD_FOLDER"], saved_filename))
                    except OSError:
                        pass
                app.logger.exception("Could not save item report")
                flash("Unable to submit the report. Please try again.", "error")

    return render_template(
        "report_item.html", categories=categories, selected_type=selected_type
    )

@app.route("/browse-items")
@login_required
def browse_items():
    search = request.args.get("search", "").strip()
    listing_type = request.args.get("listing_type", "").strip().lower()
    category_id = request.args.get("category_id", "").strip()
    location = request.args.get("location", "").strip()

    query = Item.query.filter_by(status="active")
    if search:
        query = query.filter(or_(
            Item.title.ilike(f"%{search}%"),
            Item.description.ilike(f"%{search}%")
        ))
    if listing_type in ("lost", "found"):
        query = query.filter(Item.listing_type == listing_type)
    else:
        listing_type = ""
    if category_id:
        try:
            category_id = int(category_id)
            query = query.filter(Item.category_id == category_id)
        except ValueError:
            category_id = ""
    if location:
        query = query.filter(Item.location.ilike(f"%{location}%"))

    items = query.order_by(Item.created_at.desc()).all()
    categories = Category.query.order_by(Category.category_name).all()
    return render_template(
        "browse_items.html", items=items, categories=categories,
        search=search, listing_type=listing_type,
        category_id=str(category_id) if category_id else "", location=location
    )

@app.route("/item/<int:item_id>", methods=["GET", "POST"])
@login_required
def item_details(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    if item.status != "active" and item.user_id != current_user.user_id:
        flash("This report is no longer active.", "error")
        return redirect(url_for("browse_items"))

    if request.method == "POST":
        message_text = request.form.get("message", "").strip()
        if current_user.user_id == item.user_id:
            flash("You cannot message yourself.", "error")
        elif item.status != "active":
            flash("This report is no longer accepting messages.", "error")
        elif not message_text:
            flash("Please enter a message.", "error")
        elif len(message_text) > 5000:
            flash("Message cannot exceed 5000 characters.", "error")
        else:
            db.session.add(Message(
                item_id=item.item_id, sender_id=current_user.user_id,
                receiver_id=item.user_id, message=message_text
            ))
            db.session.commit()
            flash("Your message has been sent.", "success")
            return redirect(url_for("item_details", item_id=item.item_id))

    return render_template("item_details.html", item=item)

@app.route("/my-reports")
@login_required
def my_reports():
    items = Item.query.filter_by(user_id=current_user.user_id).order_by(
        Item.created_at.desc()
    ).all()
    return render_template("my_reports.html", items=items)

@app.route("/item/<int:item_id>/status", methods=["POST"])
@login_required
def update_item_status(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    if item.user_id != current_user.user_id and current_user.role != "admin":
        abort(403)
    new_status = request.form.get("status", "")
    if new_status not in ("active", "returned", "closed"):
        flash("Invalid status.", "error")
    else:
        item.status = new_status
        db.session.commit()
        flash("Report status updated.", "success")
    return redirect(request.referrer or url_for("my_reports"))

@app.route("/messages")
@login_required
def my_messages():
    messages = Message.query.filter(or_(
        Message.sender_id == current_user.user_id,
        Message.receiver_id == current_user.user_id
    )).order_by(Message.sent_at.desc()).all()
    return render_template("messages.html", messages=messages)

@app.route("/message/<int:message_id>/read", methods=["POST"])
@login_required
def mark_message_read(message_id):
    message = db.session.get(Message, message_id)
    if not message:
        abort(404)
    if message.receiver_id != current_user.user_id:
        abort(403)
    message.is_read = True
    db.session.commit()
    flash("Message marked as read.", "success")
    return redirect(url_for("my_messages"))

@app.route("/admin")
@admin_required
def admin_dashboard():
    return render_template(
        "admin_dashboard.html",
        user_count=User.query.count(),
        item_count=Item.query.count(),
        message_count=Message.query.count(),
        users=User.query.order_by(User.created_at.desc()).all(),
        items=Item.query.order_by(Item.created_at.desc()).all()
    )

@app.route("/admin/user/<int:user_id>/role", methods=["POST"])
@admin_required
def admin_update_role(user_id):
    user = db.session.get(User, user_id)
    if not user:
        abort(404)
    if user.user_id == current_user.user_id:
        flash("You cannot change your own role.", "error")
    else:
        role = request.form.get("role")
        if role in ("student", "admin"):
            user.role = role
            db.session.commit()
            flash("User role updated.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/item/<int:item_id>/delete", methods=["POST"])
@admin_required
def admin_delete_item(item_id):
    item = db.session.get(Item, item_id)
    if not item:
        abort(404)
    if item.image_filename:
        try:
            os.remove(os.path.join(app.config["UPLOAD_FOLDER"], item.image_filename))
        except OSError:
            pass
    db.session.delete(item)
    db.session.commit()
    flash("Item report deleted.", "success")
    return redirect(url_for("admin_dashboard"))

@app.errorhandler(403)
def forbidden(error):
    return render_template("error.html", code=403, message="You do not have permission to access this page."), 403

@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", code=404, message="The page or item you requested could not be found."), 404

@app.errorhandler(413)
def too_large(error):
    flash("The uploaded file is too large. Maximum size is 5 MB.", "error")
    return redirect(request.referrer or url_for("dashboard"))

@app.cli.command("init-db")
def init_db():
    """Create tables and seed default categories."""
    db.create_all()
    defaults = [
        "Electronics", "Documents", "Books", "Accessories",
        "Bags", "Keys", "Wallets", "Clothing", "Others"
    ]
    for name in defaults:
        if not Category.query.filter_by(category_name=name).first():
            db.session.add(Category(category_name=name))
    db.session.commit()
    print("Database tables and categories are ready.")

if __name__ == "__main__":
    app.run(debug=True)
