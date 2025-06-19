
from flask import (
    abort,
    request,
    send_from_directory,
    session,
    render_template,
    redirect,
    url_for,
    flash,
)

from models import User 
import sys


from flask_babel import _, lazy_gettext
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from markdown import markdown
from datetime import datetime, timedelta
from humanize import naturaltime
from uuid import uuid4
from os import path

from models import *

from twilio.rest import Client
import os
# ✅ Replace these with your actual Twilio credentials
TWILIO_ACCOUNT_SID =  os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN =  os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER =os.getenv("TWILIO_PHONE_NUMBER")

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def get_locale():
    return request.accept_languages.best_match(["en", "hi"])
    """
    Get the locale based on various sources.

    Checks if the language query parameter is set and valid.
    If set, it returns the language from the query parameter.
    If not set via query, checks if the language is stored in the session.
    If found, returns the stored language. Otherwise, it uses the browser's preferred language.

    Returns:
        str: The selected locale.
    """

    # Check if the language query parameter is set and valid
    if "lang" in request.args:
        lang = request.args.get("lang")
        if lang in ["en", "hi"]:
            session["lang"] = lang
            return session["lang"]
    # If not set via query, check if we have it stored in the session
    elif "lang" in session:
        return session.get("lang")
    # Otherwise, use the browser's preferred language
    return request.accept_languages.best_match(["en", "hi"])


# babel = Babel(app, locale_selector=get_locale)


@app.context_processor
def inject_babel():
    return dict(_=lazy_gettext)


@app.context_processor
def inject_locale():
    return {"get_locale": get_locale}


@app.context_processor
def inject_current_locale():
    return {"current_locale": get_locale()}


@app.before_request
def clear_trailing():
    """
    Remove trailing slashes from URL paths before processing.

    If a URL path ends with a '/', this function redirects to the same URL without the trailing '/'.

    Returns:
        redirect: A redirect to the URL without the trailing slash.
    """

    rp = request.path
    if rp != "/" and rp.endswith("/"):
        return redirect(rp[:-1])


@app.route("/setlang")
def setlang():
    """
    Set the language for the session.

    Gets the language from the query parameters and sets it as the session language.

    Returns:
        redirect: A redirect to the referrer page.
    """

    lang = request.args.get("lang", "en")
    session["lang"] = lang
    return redirect(request.referrer)


@app.route("/files/<path:filename>")
def serve_file(filename):
    """
    Serve files from the upload directory.

    Args:
        filename (str): The name of the file to be served.

    Returns:
        send_from_directory: Sends the file from the upload directory.
    """

    return send_from_directory(app.config["UPLOAD_DIRECTORY"], filename)


@app.route("/")
def index():
    """
    Render the index page with relevant data.

    Returns:
        render_template: Renders the index.html template with relevant data.
    """

    most_ordered_services = (
        db.session.query(Service)
        .join(Order, Service.id == Order.service_id)
        .group_by(Service.id)
        .order_by(func.count(Order.id).desc())
        .limit(6)
        .all()
    )

    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)

    total_orders = Order.query.count()
    orders_last_week = Order.query.filter(
        Order.start_date
        >= start_date.replace(hour=0, minute=0, second=0, microsecond=0),
        Order.start_date < end_date.replace(hour=0, minute=0, second=0, microsecond=0),
    ).count()
    total_users = User.query.count()
    total_services = Service.query.count()
    total_department = Department.query.count()

    return render_template(
        "index.html",
        services=most_ordered_services,
        Department=Department,
        total_orders=total_orders,
        orders_yesterday=orders_last_week,
        total_users=total_users,
        total_services=total_services,
        total_department=total_department,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    """
    Handle user registration and account creation.

    Returns:
        render_template: Renders the register.html template with relevant data.
    """

    logout()

    msg = ""

    if (
        request.method == "POST"
        and "id" in request.form
        and "password" in request.form
        and "confirm-password" in request.form
        and "name" in request.form
        and "phone" in request.form
        and "email" in request.form
        and "address" in request.form
    ):
        id = request.form["id"]
        password = request.form["password"]
        confirm_password = request.form["confirm-password"]
        name = request.form["name"]
        phone = request.form["phone"]
        email = request.form["email"]
        address = request.form["address"]

        user = User.query.filter_by(id=id).first()

        if user:
            msg = _("UserAlreadyExists")
        elif len(id) != 14 or not id.isdigit():
            msg = _("IncorrectIDFormat")
        elif len(password) < 6 or len(password) > 28:
            msg = _("InvalidPasswordLength")
        elif confirm_password != password:
            msg = _("PasswordsDoNotMatch")
        elif (
            not id
            or not password
            or not confirm_password
            or not name
            or not phone
            or not email
            or not address
        ):
            msg = _("EmptyFields")
        else:
            hashed_password = generate_password_hash(password)
            new_user = User(
                id=id,
                password=hashed_password,
                name=name,
                phone=phone,
                email=email,
                address=address,
                is_admin=0,
            )

            db.session.add(new_user)
            db.session.commit()
            user = User.query.filter_by(id=id).first()
            session["loggedin"] = True
            session["id"] = user.id
            session["is_admin"] = user.is_admin
            msg = _("AccountCreated")

            return redirect(url_for("index"))
    elif request.method == "POST":
        msg = _("FillForm")

    return render_template("register.html", msg=msg)


@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Handle user login and session creation.

    Returns:
        render_template: Renders the login.html template with relevant data.
    """

    logout()

    msg = ""

    if request.method == "POST" and "id" in request.form and "password" in request.form:
        id = request.form["id"]
        password = request.form["password"]

        user = User.query.filter_by(id=id).first()
        if not user:
            msg = _("AccountNotFound")
        elif not id or not password:
            msg = _("EmptyFields")
        elif user:
            if check_password_hash(user.password, password):
                session["loggedin"] = True
                session["id"] = user.id
                session["is_admin"] = user.is_admin
                msg = _("LoginSuccess")

                return redirect(url_for("index"))
            else:
                msg = _("IncorrectPassword")

    elif request.method == "POST":
        msg = _("FillForm")

    return render_template("login.html", msg=msg)


@app.route("/logout")
def logout():
    """
    Log out the current user and clear their session.

    Returns:
        redirect: Redirects to the index page after logging out.
    """

    session.pop("loggedin", None)
    session.pop("id", None)
    session.pop("is_admin", None)

    return redirect(url_for("index"))


@app.route("/profile/<id>", methods=["GET", "POST"])
def profile(id):
    """
    Render user profile page.

    Args:
        id (str): The ID of the user.

    Returns:
        render_template: Renders the profile.html template with relevant data.
    """

    if "loggedin" not in session:
        abort(403)
    elif id == session["id"] or session["is_admin"] == True:
        viewer = "current_user" if session["id"] == id else "admin"
        user = User.query.filter_by(id=id).first()

        if request.method == "POST" and request.form["action"] == "logout":
            return logout()

        return render_template("profile.html", user=user, viewer=viewer)
    else:
        abort(403)


@app.route("/account", methods=["GET", "POST"])
def account():
    """
    Handle user account information management.

    This function handles updating user information and password, as well as deleting user account.

    Returns:
        render_template: Renders the account.html template with relevant data.
    """

    if "loggedin" not in session:
        abort(401)

    user = User.query.filter_by(id=session["id"]).first()
    msg = ""

    if (
        request.method == "POST"
        and "fullname" in request.form
        and "phone" in request.form
        and "email" in request.form
        and "address" in request.form
        and request.form["action"] == "update_info"
    ):
        user.name = request.form["fullname"]
        user.phone = request.form["phone"]
        user.email = request.form["email"]
        user.address = request.form["address"]
        db.session.commit()

        msg = _("AccountInfoUpdated")
    elif (
        request.method == "POST"
        and "old_password" in request.form
        and "new_password" in request.form
        and "confirm_password" in request.form
        and request.form["action"] == "update_password"
    ):
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        if check_password_hash(user.password, old_password):
            if len(new_password) < 6 or len(new_password) > 28:
                msg = _("PasswordLengthError")
            elif confirm_password != new_password:
                msg = _("PasswordsDoNotMatchError")
            elif new_password == old_password:
                msg = _("SamePasswordError")
            else:
                hashed_password = generate_password_hash(new_password)
                user.password = hashed_password
                db.session.commit()

                msg = _("PasswordUpdated")
        else:
            msg = _("IncorrectPasswordError")
    elif (
        request.method == "POST"
        and "password" in request.form
        and request.form["action"] == "delete_account"
    ):
        if check_password_hash(user.password, request.form["password"]):
            db.session.delete(user)
            db.session.commit()

            return logout()
        else:
            msg = _("IncorrectPasswordError")

    elif request.method == "POST":
        msg = _("FillFormError")

    return render_template("account.html", user=user, msg=msg)


@app.route("/new", methods=["GET", "POST"])
def new():
    """
    Handle creation of new departments or services.

    This function handles the creation of new departments or services by admin users.

    Returns:
        render_template: Renders the new.html template with relevant data.
    """

    
    if "loggedin" not in session or session["is_admin"] == False:
        abort(403)

    departments = Department.query.all()
    recommend = request.args.get("recommend")
    msg = ""

    if (
        request.method == "POST"
        and "title" in request.form
        and "description" in request.form
        and "type" in request.form
        and "associated" in request.form
    ):
        title = request.form["title"]
        description = request.form["description"]
        readme = request.form["readme"] if "readme" in request.form else None
        type_of = request.form["type"]
        associated_with = (
            request.form["associated"] if request.form["associated"] != "none" else None
        )

        existing = (
            Department.query.filter_by(title=title).first()
            or Service.query.filter_by(title=title).first()
        )
        if existing:
            msg = _("DuplicateNameError")
        elif type_of == "Department":
            new = Department(
                title=title,
                description=description,
                readme=readme,
            )
            db.session.add(new)
            db.session.commit()

            flash(_("DepartmentCreated"), "success")
            return redirect(url_for("department", id=new.id))
        elif type_of == "Service":
            department = Department.query.filter_by(id=associated_with).first()
            if department:
                new = Service(
                    title=title,
                    description=description,
                    readme=readme,
                    department_id=department.id,
                )
            else:
                new = Service(
                    title=title,
                    description=description,
                    readme=readme,
                )

            db.session.add(new)
            db.session.commit()

            flash(_("ServiceCreated"), "success")
            return redirect(url_for("service", id=new.id))
    elif request.method == "POST":
        msg = _("FillFormError")

    users = User.query.all()
    for user in users:
        print(user.phone)
        if user.phone and request.method=="GET":  # assuming 'phone_number' is a field in User
            try:
                client.messages.create (
                    body="A new department or service has been added. get time",
                    from_=TWILIO_PHONE_NUMBER,
                    to="+91"+user.phone,
                )
                
            except Exception as e:
                print(f"Failed to send SMS to {user.phone}: {e}", file=sys.stdout)

    return render_template(
        "new.html", departments=departments, recommend=recommend, msg=msg
    )

@app.route("/edit", methods=["GET", "POST"])
def edit():
    """
    Handle editing of existing departments or services.

    This function handles editing existing departments or services by admin users.

    Returns:
        render_template: Renders the edit.html template with relevant data.
    """

    if "loggedin" not in session or session["is_admin"] == False:
        abort(403)

    item_type = request.args.get("item")
    item_id = request.args.get("id")

    if item_type == "service":
        item = Service.query.filter_by(id=item_id).first()
    elif item_type == "department":
        item = Department.query.filter_by(id=item_id).first()
    else:
        item = None

    if (
        request.method == "POST"
        and "title" in request.form
        and "description" in request.form
        and "readme" in request.form
        and request.form["action"] == "update_item"
    ):
        item.title = request.form["title"]
        item.description = request.form["description"]
        item.readme = request.form["readme"]
        db.session.commit()

        flash(_("ItemUpdatedSuccess").format(item_type.capitalize()), "success")
        return redirect(url_for("edit", item=item_type, id=item_id))
    elif request.method == "POST" and request.form["action"] == "delete_item":
        db.session.delete(item)
        db.session.commit()

        return redirect(url_for("index"))
    elif request.method == "POST":
        flash(_("FillFormError"), "failure")

    return render_template("edit.html", item_type=item_type, item=item)


@app.route("/departments")
def departments():
    """
    Render the departments page with a list of all departments.

    Returns:
        render_template: Renders the list.html template with relevant data.
    """

    departments = Department.query.all()
    return render_template(
        "list.html",
        list_title=_("Departments"),
        list_description=_("DepartmentsListDescription"),
        path="department",
        items=departments,
    )


@app.route("/departments/<id>")
def department(id):
    """
    Render the details of a specific department.

    Args:
        id (str): The ID of the department to be rendered.

    Returns:
        render_template: Renders the listing.html template with relevant data.
    """

    department = Department.query.filter_by(id=id).first()
    if not department:
        abort(404)

    all_services_url = url_for("department_services", id=department.id)
    return render_template(
        "listing.html",
        type="department",
        item=department,
        markdown=markdown,
        all_services_url=all_services_url,
    )


@app.route("/departments/<id>/services")
def department_services(id):
    """
    Render the services of a specific department.

    Args:
        id (str): The ID of the department.

    Returns:
        render_template: Renders the list.html template with relevant data.
    """

    department = Department.query.filter_by(id=id).first()
    if not department:
        abort(404)

    services = Service.query.filter_by(department_id=id).all()
    return render_template(
        "list.html",
        list_title=(
            department.title + " " + _("Services")
            if get_locale() == "en"
            else _("DeptServices") + " " + department.title
        ),
        list_description=_("ServicesListDescription"),
        path="service",
        items=services,
    )


@app.route("/services")
def services():
    """
    Render the services page with a list of all services.

    Returns:
        render_template: Renders the list.html template with relevant data.
    """

    services = Service.query.all()
    return render_template(
        "list.html",
        list_title=_("Services"),
        list_description=_("ServicesListDescription"),
        item_type="all_services",
        path="service",
        items=services,
        Department=Department,
    )


@app.route("/services/<id>")
def service(id):
    """
    Render the details of a specific service.

    Args:
        id (str): The ID of the service to be rendered.

    Returns:
        render_template: Renders the listing.html template with relevant data.
    """

    service = Service.query.filter_by(id=id).first()
    if not service:
        abort(404)

    return render_template(
        "listing.html",
        type="service",
        item=service,
        Department=Department,
        markdown=markdown,
    )


@app.route("/search")
def search():
    """
    Handle search functionality for departments and services.

    Returns:
        render_template: Renders the search.html template with relevant data.
    """

    search_query = request.args.get("query")
    item = request.args.get("item") if request.args.get("item") else "all"
    msg = ""
    search_title = _("SearchTitle")
    search_placeholder = _("SearchPlaceholder")
    departments = None
    services = None

    if search_query:
        if item == "department" or item == "service":
            search_title = _("SearchTitleItem").format(item.capitalize())
            search_placeholder = _("SearchPlaceholderItem").format(item.capitalize())

        if item == "department" or item == "all":
            departments = Department.query.filter(
                Department.title.ilike(f"%{search_query}%")
            ).all()

            if not departments and item != "all":
                msg = _("NoDepartmentsFound")

        if item == "service" or item == "all":
            services = Service.query.filter(
                Service.title.ilike(f"%{search_query}%")
            ).all()

            if not services and item != "all":
                msg = _("NoServicesFound")

        if item == "all" and not departments and not services:
            msg = _("NoItemsFound")

    return render_template(
        "search.html",
        search_title=search_title,
        search_placeholder=search_placeholder,
        search_query=search_query,
        msg=msg,
        departments=departments,
        services=services,
        Department=Department,
    )


@app.route("/new_order", methods=["GET", "POST"])
def new_order():
    """
    Handle creation of a new order.

    Returns:
        render_template: Renders the new_order.html template with relevant data.
    """

    if "loggedin" not in session:
        abort(401)
    if session["is_admin"] == True:
        abort(403)

    services = Service.query.all()
    recommend = request.args.get("recommend")
    msg = ""

    if request.method == "POST" and "service" in request.form:
        service = request.form["service"]
        details = request.form["details"] if "details" in request.form else None

        files = request.files.getlist("file")
        file_paths = []
        if not all(file.filename == "" for file in files):
            for file in files:
                filename = str(uuid4()) + "_" + secure_filename(file.filename)
                file.save(path.join(app.config["UPLOAD_DIRECTORY"], filename))
                file_paths.append(filename)

        new_order = Order(
            details=details,
            start_date=datetime.now(),
            service_id=int(service),
            user_id=session["id"],
            file_paths=",".join(file_paths) if file_paths else None,
            is_done=False,
        )
        db.session.add(new_order)
        db.session.commit()

        flash(_("OrderCreatedSuccess"), "success")
        return redirect(url_for("order", id=new_order.id))

    elif request.method == "POST":
        msg = _("FillFormError")

    return render_template(
        "new_order.html",
        services=services,
        recommend=recommend,
        int=int,
        msg=msg,
    )


@app.route("/my_orders")
def my_orders():
    """
    Render the orders page with a list of user's orders.

    Returns:
        render_template: Renders the my_orders.html template with relevant data.
    """

    if "loggedin" not in session:
        abort(401)
    elif session["is_admin"] == True:
        abort(403)

    orders = Order.query.filter_by(user_id=session["id"], is_done=False).all()
    done_orders = Order.query.filter_by(user_id=session["id"], is_done=True).all()

    return render_template(
        "my_orders.html",
        orders=orders,
        done_orders=done_orders,
        Service=Service,
        Department=Department,
        naturaltime=naturaltime,
        strptime=datetime.strptime,
        str=str,
    )


@app.route("/my_orders/<id>", methods=["GET", "POST"])
def order(id):
    """
    Render the details of a specific order.

    Args:
        id (str): The ID of the order to be rendered.

    Returns:
        render_template: Renders the order.html template with relevant data.
    """

    order = Order.query.filter_by(id=id).first()
    if not order:
        abort(404)
    elif order.user_id != session["id"]:
        abort(403)

    if request.method == "POST" and request.form["action"] == "delete_order":
        db.session.delete(order)
        db.session.commit()

        return redirect(url_for("my_orders"))

    return render_template(
        "order.html",
        order=order,
        Service=Service,
        Department=Department,
        naturaltime=naturaltime,
        strptime=datetime.strptime,
        str=str,
    )


@app.route("/orders")
def orders():
    """
    Render the orders page with a list of all active orders.

    Returns:
        render_template: Renders the orders.html template with relevant data.
    """

    if "loggedin" not in session or session["is_admin"] == False:
        abort(403)

    orders = Order.query.filter_by(is_done=False).all()
    return render_template(
        "orders.html",
        orders=orders,
        Service=Service,
        Department=Department,
        naturaltime=naturaltime,
        strptime=datetime.strptime,
        str=str,
    )


@app.route("/orders/<id>", methods=["GET", "POST"])
def user_order(id):
    """
    Render the details of a specific user order.

    Args:
        id (str): The ID of the order to be rendered.

    Returns:
        render_template: Renders the user_order.html template with relevant data.
    """

    order = Order.query.filter_by(id=id).first()
    if not order:
        abort(404)
    elif "loggedin" not in session or session["is_admin"] == False:
        abort(403)

    if request.method == "POST" and request.form["action"] == "finish_order":
        order.end_date = datetime.now()
        order.is_done = True
        db.session.commit()

        flash(_("OrderFinishedSuccess"), "success")
    elif request.method == "POST" and request.form["action"] == "delete_order":
        db.session.delete(order)
        db.session.commit()

        flash(
            _("OrderDeletedSuccess").format(order_id=order.id),
            "success",
        )
        return redirect(url_for("orders"))

    return render_template(
        "user_order.html",
        order=order,
        Service=Service,
        Department=Department,
        naturaltime=naturaltime,
        strptime=datetime.strptime,
        str=str,
    )


@app.route("/contact_us", methods=["GET", "POST"])
def contact():
    """
    Handle the contact us page.

    Returns:
        render_template: Renders the contact.html template with relevant data.
    """

    msg = ""

    if (
        request.method == "POST"
        and "subject" in request.form
        and "message" in request.form
    ):
        if "loggedin" in session:
            user = User.query.filter_by(id=session["id"]).first()

            name = user.name
            email = user.email
            phone = user.phone
        elif (
            "loggedin" not in session
            and "name" in request.form
            and "email" in request.form
            and "phone" in request.form
        ):
            name = request.form["name"]
            email = request.form["email"]
            phone = request.form["phone"]

        subject = request.form["subject"]
        message = request.form["message"]

        if name and email and phone and subject and message:
            # Logic for sending user feedback through email to feedback staff involves

            msg = _("FeedbackReceivedSuccess")
        else:
            msg = _("FillFormError")
    elif request.method == "POST":
        msg = _("FillFormError")

    return render_template("contact.html", msg=msg)


@app.errorhandler(401)
def unauthorized(e):
    """
    Handle an unauthorized (401) error.

    Args:
        e: The error object.

    Returns:
        redirect: Redirects to the login page for an unauthorized user.
    """

    return redirect(url_for("login"))


@app.errorhandler(403)
def forbidden(e):
    """
    Handle an unauthorized (403) error.

    Args:
        e: The error object.

    Returns:
        redirect: Redirects to the index page for an unauthorized user.
    """

    return redirect(url_for("index"))


@app.errorhandler(404)
def page_not_found(e):
    """
    Handle a 404 Page Not Found error.

    Args:
        e: The error object.

    Returns:
        render_template: Renders the 404.html template for a 404 error.
    """

    return render_template("404.html"), 404
