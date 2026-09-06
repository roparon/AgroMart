import os
import uuid

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app import db
from app.forms.homepage import HomepageContentForm
from app.models.homepage_content import HomepageContent


homepage_bp = Blueprint(
    "admin_homepage",
    __name__,
)


ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def admin_required():
    if not current_user.is_authenticated or not current_user.is_admin:
        flash(
            "Administrator privileges are required to access this page.",
            "danger",
        )
        return False

    return True


def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )


def save_homepage_image(image):
    if not image or not image.filename:
        return None

    if not allowed_file(image.filename):
        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP images are allowed."
        )

    image.seek(0, os.SEEK_END)
    file_size = image.tell()
    image.seek(0)

    if file_size > MAX_IMAGE_SIZE:
        raise ValueError("Image must be smaller than 5 MB.")

    original_name = secure_filename(image.filename)

    if not original_name:
        raise ValueError("Invalid image filename.")

    extension = original_name.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{extension}"

    upload_dir = os.path.join(
        current_app.static_folder,
        "uploads",
        "home",
    )

    os.makedirs(upload_dir, exist_ok=True)

    image_path = os.path.join(upload_dir, filename)
    image.save(image_path)

    return f"/static/uploads/home/{filename}"


def delete_homepage_image(image_url):
    if not image_url:
        return

    prefix = "/static/uploads/home/"

    if not image_url.startswith(prefix):
        return

    filename = os.path.basename(image_url)

    if not filename:
        return

    upload_dir = os.path.join(
        current_app.static_folder,
        "uploads",
        "home",
    )

    image_path = os.path.join(upload_dir, filename)

    if os.path.isfile(image_path):
        try:
            os.remove(image_path)
        except OSError:
            current_app.logger.warning(
                "Unable to delete homepage image: %s",
                image_path,
            )


@homepage_bp.route("/")
@login_required
def homepage():
    if not admin_required():
        return redirect(url_for("home.home"))

    content = (
        HomepageContent.query
        .order_by(
            HomepageContent.sort_order.asc(),
            HomepageContent.id.asc(),
        )
        .all()
    )

    return render_template(
        "admin/homepage.html",
        content=content,
    )


@homepage_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_content():
    if not admin_required():
        return redirect(url_for("home.home"))

    form = HomepageContentForm()

    if form.validate_on_submit():

        existing = HomepageContent.query.filter_by(
            key=form.key.data.strip()
        ).first()

        if existing:
            flash(
                f'Content key "{form.key.data}" already exists.',
                "danger",
            )
            return render_template(
                "admin/homepage_form.html",
                form=form,
                content=None,
                page_title="Add Homepage Content",
            )

        image_url = None

        try:
            if form.image.data:
                image_url = save_homepage_image(form.image.data)

            content = HomepageContent(
                key=form.key.data.strip(),
                headline=form.headline.data.strip()
                if form.headline.data
                else None,
                subheadline=form.subheadline.data.strip()
                if form.subheadline.data
                else None,
                button_text=form.button_text.data.strip()
                if form.button_text.data
                else None,
                button_url=form.button_url.data.strip()
                if form.button_url.data
                else None,
                image_url=image_url,
                image_alt=form.image_alt.data.strip()
                if form.image_alt.data
                else None,
                css_class=form.css_class.data.strip()
                if form.css_class.data
                else None,
                is_active=form.is_active.data,
                sort_order=form.sort_order.data or 0,
            )

            db.session.add(content)
            db.session.commit()

            flash(
                "Homepage content created successfully.",
                "success",
            )

            return redirect(
                url_for("admin_homepage.homepage")
            )

        except Exception as exc:
            db.session.rollback()

            if image_url:
                delete_homepage_image(image_url)

            current_app.logger.exception(
                "Failed to create homepage content: %s",
                exc,
            )

            flash(
                "Unable to create homepage content.",
                "danger",
            )

    return render_template(
        "admin/homepage_form.html",
        form=form,
        content=None,
        page_title="Add Homepage Content",
    )


@homepage_bp.route("/<int:content_id>/edit", methods=["GET", "POST"])
@login_required
def edit_content(content_id):
    if not admin_required():
        return redirect(url_for("home.home"))

    content = HomepageContent.query.get_or_404(content_id)

    form = HomepageContentForm(obj=content)

    if form.validate_on_submit():

        new_key = form.key.data.strip()

        duplicate = (
            HomepageContent.query
            .filter(
                HomepageContent.key == new_key,
                HomepageContent.id != content.id,
            )
            .first()
        )

        if duplicate:
            flash(
                f'Content key "{new_key}" already exists.',
                "danger",
            )

            return render_template(
                "admin/homepage_form.html",
                form=form,
                content=content,
                page_title="Edit Homepage Content",
            )

        old_image_url = content.image_url
        new_image_url = old_image_url

        try:
            if form.image.data:
                new_image_url = save_homepage_image(
                    form.image.data
                )

            content.key = new_key

            content.headline = (
                form.headline.data.strip()
                if form.headline.data
                else None
            )

            content.subheadline = (
                form.subheadline.data.strip()
                if form.subheadline.data
                else None
            )

            content.button_text = (
                form.button_text.data.strip()
                if form.button_text.data
                else None
            )

            content.button_url = (
                form.button_url.data.strip()
                if form.button_url.data
                else None
            )

            content.image_url = new_image_url

            content.image_alt = (
                form.image_alt.data.strip()
                if form.image_alt.data
                else None
            )

            content.css_class = (
                form.css_class.data.strip()
                if form.css_class.data
                else None
            )

            content.is_active = form.is_active.data
            content.sort_order = form.sort_order.data or 0

            db.session.commit()

            if (
                new_image_url != old_image_url
                and old_image_url
            ):
                delete_homepage_image(old_image_url)

            flash(
                "Homepage content updated successfully.",
                "success",
            )

            return redirect(
                url_for("admin_homepage.homepage")
            )

        except Exception as exc:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_homepage_image(new_image_url)

            current_app.logger.exception(
                "Failed to update homepage content: %s",
                exc,
            )

            flash(
                "Unable to update homepage content.",
                "danger",
            )

    return render_template(
        "admin/homepage_form.html",
        form=form,
        content=content,
        page_title="Edit Homepage Content",
    )


@homepage_bp.route("/<int:content_id>/toggle", methods=["POST"])
@login_required
def toggle_content(content_id):
    if not admin_required():
        return redirect(url_for("home.home"))

    content = HomepageContent.query.get_or_404(content_id)

    try:
        content.is_active = not content.is_active
        db.session.commit()

        status = (
            "published"
            if content.is_active
            else "hidden"
        )

        flash(
            f'"{content.key}" is now {status}.',
            "success",
        )

    except Exception as exc:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to toggle homepage content: %s",
            exc,
        )

        flash(
            "Unable to change the content status.",
            "danger",
        )

    return redirect(
        url_for("admin_homepage.homepage")
    )


@homepage_bp.route("/<int:content_id>/delete", methods=["POST"])
@login_required
def delete_content(content_id):
    if not admin_required():
        return redirect(url_for("home.home"))

    content = HomepageContent.query.get_or_404(content_id)

    image_url = content.image_url
    content_key = content.key

    try:
        db.session.delete(content)
        db.session.commit()

        if image_url:
            delete_homepage_image(image_url)

        flash(
            f'"{content_key}" was deleted successfully.',
            "success",
        )

    except Exception as exc:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to delete homepage content: %s",
            exc,
        )

        flash(
            "Unable to delete homepage content.",
            "danger",
        )

    return redirect(
        url_for("admin_homepage.homepage")
    )