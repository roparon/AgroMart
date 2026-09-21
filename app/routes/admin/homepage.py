import json
import os
import uuid

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from vercel.blob import BlobClient

from app import db
from app.forms.homepage import HomepageContentForm
from app.forms.homepage_section import HomepageSectionForm
from app.forms.homepage_settings import HomepageSettingsForm
from app.models.homepage_content import HomepageContent
from app.models.homepage_section import HomepageSection
from app.models.homepage_setting import HomepageSetting


homepage_bp = Blueprint(
    "admin_homepage",
    __name__,
)


ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "webp",
}

MAX_IMAGE_SIZE = 4 * 1024 * 1024
MAX_HERO_SLIDES = 10

BLOB_FOLDER_CONTENT = "homepage/content"
BLOB_FOLDER_SECTIONS = "homepage/sections"


# ----------------------------------------------------------------------
# ADMIN ACCESS
# ----------------------------------------------------------------------

def admin_required():
    """
    Check whether the current user has administrator privileges.
    """

    if not current_user.is_authenticated or not current_user.is_admin:
        flash(
            "Administrator privileges are required to access this page.",
            "danger",
        )
        return False

    return True


# ----------------------------------------------------------------------
# FORM ERROR HELPERS
# ----------------------------------------------------------------------

def flash_form_errors(form):
    """
    Show useful validation errors when a form submission fails.
    """

    shown = set()

    for field_name, errors in form.errors.items():
        for error in errors:
            message = str(error).strip()

            if not message:
                continue

            if message in shown:
                continue

            shown.add(message)

            field = getattr(form, field_name, None)

            label = (
                field.label.text
                if field is not None
                else field_name.replace("_", " ").title()
            )

            flash(
                f"{label}: {message}",
                "danger",
            )


# ----------------------------------------------------------------------
# IMAGE HELPERS
# ----------------------------------------------------------------------

def allowed_file(filename):
    """
    Return True when the uploaded filename has an allowed extension.
    """

    if not filename:
        return False

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def _get_blob_client():
    """
    Create a Vercel Blob client.

    The client reads BLOB_READ_WRITE_TOKEN from the Vercel
    production environment when deployed.
    """

    try:
        return BlobClient()
    except Exception as exc:
        current_app.logger.exception(
            "Unable to initialize Vercel Blob client: %s",
            exc,
        )

        raise RuntimeError(
            "Vercel Blob storage is not available. "
            "Please verify that the Blob store is connected "
            "to the production project."
        ) from exc


def save_homepage_image(image, folder="content"):
    """
    Upload a homepage image to Vercel Blob.

    Returns the permanent public Blob URL.

    No image is written to the Vercel function filesystem.
    """

    if not image or not image.filename:
        return None

    if not allowed_file(image.filename):
        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP images are allowed."
        )

    # --------------------------------------------------------------
    # Validate file size without loading the entire file first.
    # --------------------------------------------------------------

    try:
        image.seek(0, os.SEEK_END)
        file_size = image.tell()
        image.seek(0)
    except (OSError, ValueError):
        raise ValueError(
            "Unable to read the uploaded image."
        )

    if file_size <= 0:
        raise ValueError(
            "The uploaded image is empty."
        )

    if file_size > MAX_IMAGE_SIZE:
        raise ValueError(
            "Image must be smaller than 5 MB."
        )

    # --------------------------------------------------------------
    # Sanitize filename and determine extension.
    # --------------------------------------------------------------

    original_name = secure_filename(
        image.filename
    )

    if not original_name:
        raise ValueError(
            "Invalid image filename."
        )

    if "." not in original_name:
        raise ValueError(
            "The uploaded image has no valid file extension."
        )

    extension = original_name.rsplit(
        ".",
        1,
    )[1].lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise ValueError(
            "Only JPG, JPEG, PNG and WEBP images are allowed."
        )

    # --------------------------------------------------------------
    # Determine content type.
    # --------------------------------------------------------------

    content_types = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }

    content_type = content_types.get(
        extension,
        "application/octet-stream",
    )

    # --------------------------------------------------------------
    # Generate a collision-safe filename.
    # --------------------------------------------------------------

    filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    blob_folder = (
        BLOB_FOLDER_CONTENT
        if folder == "home"
        else BLOB_FOLDER_SECTIONS
    )

    blob_path = (
        f"{blob_folder}/{filename}"
    )

    # --------------------------------------------------------------
    # Read the uploaded file into memory.
    #
    # The file is limited to 5 MB above, which keeps memory usage
    # controlled for this server-side upload approach.
    # --------------------------------------------------------------

    try:
        image.seek(0)
        image_data = image.read()
    except (OSError, ValueError):
        raise ValueError(
            "Unable to read the uploaded image."
        )

    if not image_data:
        raise ValueError(
            "The uploaded image is empty."
        )

    # --------------------------------------------------------------
    # Upload to Vercel Blob.
    # --------------------------------------------------------------

    try:
        client = _get_blob_client()

        uploaded = client.put(
            blob_path,
            image_data,
            access="public",
            content_type=content_type,
            add_random_suffix=False,
        )

    except Exception as exc:
        current_app.logger.exception(
            "Vercel Blob upload failed for %s: %s",
            blob_path,
            exc,
        )

        raise RuntimeError(
            "The image could not be uploaded to cloud storage. "
            "Please try again."
        ) from exc

    # --------------------------------------------------------------
    # Extract the permanent Blob URL.
    # --------------------------------------------------------------

    image_url = getattr(
        uploaded,
        "url",
        None,
    )

    if not image_url and isinstance(
        uploaded,
        dict,
    ):
        image_url = uploaded.get("url")

    if not image_url:
        current_app.logger.error(
            "Vercel Blob returned no URL for %s",
            blob_path,
        )

        raise RuntimeError(
            "The image was uploaded but no image URL was returned."
        )

    return image_url


def delete_homepage_image(image_url, folder=None):
    """
    Delete a homepage image from Vercel Blob.

    Existing old /static/uploads/... images are deliberately
    ignored so historical data is not damaged.
    """

    if not image_url:
        return

    # --------------------------------------------------------------
    # Only delete actual Vercel Blob URLs.
    #
    # This protects your existing SQLite-era/local image records.
    # --------------------------------------------------------------

    if (
        "blob.vercel-storage.com" not in image_url
        and ".blob.vercel-storage.com" not in image_url
    ):
        return

    try:
        client = _get_blob_client()

        client.delete(
            image_url
        )

    except Exception as exc:
        # Image deletion should never cause a successful database
        # operation to become a failed request.
        current_app.logger.warning(
            "Unable to delete Vercel Blob image %s: %s",
            image_url,
            exc,
        )


# ----------------------------------------------------------------------
# JSON CONFIG HELPERS
# ----------------------------------------------------------------------

def parse_config(value):
    """
    Convert configuration textarea into a Python dictionary.

    Empty configuration becomes {}.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return value

    if not isinstance(value, str):
        raise ValueError(
            "Section configuration must contain valid JSON."
        )

    value = value.strip()

    if not value:
        return {}

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        raise ValueError(
            "Section configuration must contain valid JSON."
        )

    if not isinstance(parsed, dict):
        raise ValueError(
            "Section configuration must be a JSON object."
        )

    return parsed


def normalize_text(value):
    """
    Safely normalize optional text form fields.
    """

    if value is None:
        return None

    if not isinstance(value, str):
        value = str(value)

    value = value.strip()

    return value if value else None


# ----------------------------------------------------------------------
# HOMEPAGE CMS DASHBOARD
# ----------------------------------------------------------------------

@homepage_bp.route("/")
@login_required
def homepage():
    """
    Main Homepage CMS dashboard.
    """

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    content = (
        HomepageContent.query
        .order_by(
            HomepageContent.sort_order.asc(),
            HomepageContent.id.asc(),
        )
        .all()
    )

    sections = (
        HomepageSection.query
        .order_by(
            HomepageSection.sort_order.asc(),
            HomepageSection.id.asc(),
        )
        .all()
    )

    settings = HomepageSetting.query.first()

    hero_count = sum(
        1
        for section in sections
        if section.section_type == "hero"
    )

    return render_template(
        "admin/homepage.html",
        content=content,
        sections=sections,
        settings=settings,
        hero_count=hero_count,
        hero_limit=MAX_HERO_SLIDES,
    )


# ----------------------------------------------------------------------
# HOMEPAGE CONTENT
# ----------------------------------------------------------------------

@homepage_bp.route(
    "/content/add",
    methods=["GET", "POST"],
)
@login_required
def add_content():

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    form = HomepageContentForm()

    if form.validate_on_submit():

        key = normalize_text(form.key.data)

        existing = (
            HomepageContent.query
            .filter_by(key=key)
            .first()
        )

        if existing:
            flash(
                f'Content key "{key}" already exists. '
                "Please choose another key.",
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
                image_url = save_homepage_image(
                    form.image.data,
                    "home",
                )

            content = HomepageContent(
                key=key,
                headline=normalize_text(
                    form.headline.data
                ),
                subheadline=normalize_text(
                    form.subheadline.data
                ),
                button_text=normalize_text(
                    form.button_text.data
                ),
                button_url=normalize_text(
                    form.button_url.data
                ),
                image_url=image_url,
                image_alt=normalize_text(
                    form.image_alt.data
                ),
                css_class=normalize_text(
                    form.css_class.data
                ),
                is_active=bool(
                    form.is_active.data
                ),
                sort_order=(
                    form.sort_order.data or 0
                ),
            )

            db.session.add(content)
            db.session.commit()

            flash(
                "Homepage content created successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "admin_homepage.homepage"
                )
            )

        except IntegrityError:
            db.session.rollback()

            if image_url:
                delete_homepage_image(
                    image_url,
                    "home",
                )

            current_app.logger.exception(
                "Duplicate or invalid database value "
                "while creating homepage content."
            )

            flash(
                "The content could not be saved because "
                "the content key may already exist. "
                "Please choose a different key.",
                "danger",
            )

        except (ValueError, RuntimeError) as exc:
            db.session.rollback()

            if image_url:
                delete_homepage_image(
                    image_url,
                    "home",
                )

            flash(
                str(exc),
                "danger",
            )

        except Exception as exc:
            db.session.rollback()

            if image_url:
                delete_homepage_image(
                    image_url,
                    "home",
                )

            current_app.logger.exception(
                "Failed to create homepage content: %s",
                exc,
            )

            flash(
                "Unable to create homepage content right now. "
                "Please try again.",
                "danger",
            )

    elif request.method == "POST":
        flash_form_errors(form)

    return render_template(
        "admin/homepage_form.html",
        form=form,
        content=None,
        page_title="Add Homepage Content",
    )


@homepage_bp.route(
    "/content/<int:content_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_content(content_id):

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    content = (
        HomepageContent.query
        .get_or_404(content_id)
    )

    form = HomepageContentForm(
        obj=content
    )

    if form.validate_on_submit():

        new_key = normalize_text(
            form.key.data
        )

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
                f'Content key "{new_key}" already exists. '
                "Please choose another key.",
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
                    form.image.data,
                    "home",
                )

            content.key = new_key
            content.headline = normalize_text(
                form.headline.data
            )
            content.subheadline = normalize_text(
                form.subheadline.data
            )
            content.button_text = normalize_text(
                form.button_text.data
            )
            content.button_url = normalize_text(
                form.button_url.data
            )
            content.image_url = new_image_url
            content.image_alt = normalize_text(
                form.image_alt.data
            )
            content.css_class = normalize_text(
                form.css_class.data
            )
            content.is_active = bool(
                form.is_active.data
            )
            content.sort_order = (
                form.sort_order.data or 0
            )

            db.session.commit()

            if (
                new_image_url != old_image_url
                and old_image_url
            ):
                delete_homepage_image(
                    old_image_url,
                    "home",
                )

            flash(
                "Homepage content updated successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "admin_homepage.homepage"
                )
            )

        except IntegrityError:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_homepage_image(
                    new_image_url,
                    "home",
                )

            current_app.logger.exception(
                "Duplicate or invalid database value "
                "while updating homepage content."
            )

            flash(
                "The content could not be updated because "
                "the content key may already exist. "
                "Please choose a different key.",
                "danger",
            )

        except (ValueError, RuntimeError) as exc:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_homepage_image(
                    new_image_url,
                    "home",
                )

            flash(
                str(exc),
                "danger",
            )

        except Exception as exc:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_homepage_image(
                    new_image_url,
                    "home",
                )

            current_app.logger.exception(
                "Failed to update homepage content: %s",
                exc,
            )

            flash(
                "Unable to update homepage content right now. "
                "Please try again.",
                "danger",
            )

    elif request.method == "POST":
        flash_form_errors(form)

    return render_template(
        "admin/homepage_form.html",
        form=form,
        content=content,
        page_title="Edit Homepage Content",
    )


@homepage_bp.route(
    "/content/<int:content_id>/toggle",
    methods=["POST"],
)
@login_required
def toggle_content(content_id):

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    content = (
        HomepageContent.query
        .get_or_404(content_id)
    )

    try:
        content.is_active = not bool(
            content.is_active
        )

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
            "Unable to change the content status. "
            "Please try again.",
            "danger",
        )

    return redirect(
        url_for(
            "admin_homepage.homepage"
        )
    )


@homepage_bp.route(
    "/content/<int:content_id>/delete",
    methods=["POST"],
)
@login_required
def delete_content(content_id):

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    content = (
        HomepageContent.query
        .get_or_404(content_id)
    )

    image_url = content.image_url
    content_key = content.key

    try:
        db.session.delete(content)
        db.session.commit()

        if image_url:
            delete_homepage_image(
                image_url,
                "home",
            )

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
            "Unable to delete homepage content. "
            "Please try again.",
            "danger",
        )

    return redirect(
        url_for(
            "admin_homepage.homepage"
        )
    )


# ----------------------------------------------------------------------
# HOMEPAGE SECTIONS
# ----------------------------------------------------------------------

@homepage_bp.route(
    "/sections/add",
    methods=["GET", "POST"],
)
@login_required
def add_section():

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    form = HomepageSectionForm()

    if (
        request.method == "GET"
        and request.args.get("section_type") == "hero"
    ):
        form.section_type.data = "hero"

    if form.validate_on_submit():

        key = normalize_text(
            form.key.data
        )

        existing = (
            HomepageSection.query
            .filter_by(key=key)
            .first()
        )

        if existing:
            flash(
                f'Section key "{key}" already exists. '
                "Please choose another key.",
                "danger",
            )

            return render_template(
                "admin/homepage_section_form.html",
                form=form,
                section=None,
                page_title="Add Homepage Section",
            )

        if form.section_type.data == "hero":
            hero_count = (
                HomepageSection.query
                .filter_by(section_type="hero")
                .count()
            )

            if hero_count >= MAX_HERO_SLIDES:
                flash(
                    f"The maximum of {MAX_HERO_SLIDES} "
                    "hero slides has been reached.",
                    "danger",
                )

                return render_template(
                    "admin/homepage_section_form.html",
                    form=form,
                    section=None,
                    page_title="Add Hero Slide",
                )

        image_url = None

        try:
            config = parse_config(
                form.config.data
            )

            if form.image.data:
                image_url = save_homepage_image(
                    form.image.data,
                    "homepage",
                )

            section = HomepageSection(
                key=key,
                section_type=form.section_type.data,
                title=normalize_text(
                    form.title.data
                ),
                subtitle=normalize_text(
                    form.subtitle.data
                ),
                content=normalize_text(
                    form.content.data
                ),
                image_url=image_url,
                image_alt=normalize_text(
                    form.image_alt.data
                ),
                button_text=normalize_text(
                    form.button_text.data
                ),
                button_url=normalize_text(
                    form.button_url.data
                ),
                config=config,
                css_class=normalize_text(
                    form.css_class.data
                ),
                is_active=bool(
                    form.is_active.data
                ),
                sort_order=(
                    form.sort_order.data or 0
                ),
            )

            db.session.add(section)
            db.session.commit()

            flash(
                "Homepage section created successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "admin_homepage.homepage"
                )
            )

        except IntegrityError:
            db.session.rollback()

            if image_url:
                delete_homepage_image(
                    image_url,
                    "homepage",
                )

            current_app.logger.exception(
                "Duplicate or invalid database value "
                "while creating homepage section."
            )

            flash(
                "The section could not be saved because "
                "the section key may already exist. "
                "Please choose a different key.",
                "danger",
            )

        except (ValueError, RuntimeError) as exc:
            db.session.rollback()

            if image_url:
                delete_homepage_image(
                    image_url,
                    "homepage",
                )

            flash(
                str(exc),
                "danger",
            )

        except Exception as exc:
            db.session.rollback()

            if image_url:
                delete_homepage_image(
                    image_url,
                    "homepage",
                )

            current_app.logger.exception(
                "Failed to create homepage section: %s",
                exc,
            )

            flash(
                "Unable to create homepage section right now. "
                "Please try again.",
                "danger",
            )

    elif request.method == "POST":
        flash_form_errors(form)

    return render_template(
        "admin/homepage_section_form.html",
        form=form,
        section=None,
        page_title="Add Homepage Section",
    )


@homepage_bp.route(
    "/sections/<int:section_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_section(section_id):

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    section = (
        HomepageSection.query
        .get_or_404(section_id)
    )

    form = HomepageSectionForm(
        obj=section
    )

    if request.method == "GET":
        form.config.data = json.dumps(
            section.config or {},
            indent=2,
        )

    if form.validate_on_submit():

        new_key = normalize_text(
            form.key.data
        )

        duplicate = (
            HomepageSection.query
            .filter(
                HomepageSection.key == new_key,
                HomepageSection.id != section.id,
            )
            .first()
        )

        if duplicate:
            flash(
                f'Section key "{new_key}" already exists. '
                "Please choose another key.",
                "danger",
            )

            return render_template(
                "admin/homepage_section_form.html",
                form=form,
                section=section,
                page_title="Edit Homepage Section",
            )

        if (
            form.section_type.data == "hero"
            and section.section_type != "hero"
        ):
            hero_count = (
                HomepageSection.query
                .filter_by(section_type="hero")
                .count()
            )

            if hero_count >= MAX_HERO_SLIDES:
                flash(
                    f"The maximum of {MAX_HERO_SLIDES} "
                    "hero slides has been reached.",
                    "danger",
                )

                return render_template(
                    "admin/homepage_section_form.html",
                    form=form,
                    section=section,
                    page_title="Edit Homepage Section",
                )

        old_image_url = section.image_url
        new_image_url = old_image_url

        try:
            config = parse_config(
                form.config.data
            )

            if form.image.data:
                new_image_url = save_homepage_image(
                    form.image.data,
                    "homepage",
                )

            section.key = new_key
            section.section_type = (
                form.section_type.data
            )
            section.title = normalize_text(
                form.title.data
            )
            section.subtitle = normalize_text(
                form.subtitle.data
            )
            section.content = normalize_text(
                form.content.data
            )
            section.image_url = new_image_url
            section.image_alt = normalize_text(
                form.image_alt.data
            )
            section.button_text = normalize_text(
                form.button_text.data
            )
            section.button_url = normalize_text(
                form.button_url.data
            )
            section.config = config
            section.css_class = normalize_text(
                form.css_class.data
            )
            section.is_active = bool(
                form.is_active.data
            )
            section.sort_order = (
                form.sort_order.data or 0
            )

            db.session.commit()

            if (
                new_image_url != old_image_url
                and old_image_url
            ):
                delete_homepage_image(
                    old_image_url,
                    "homepage",
                )

            flash(
                "Homepage section updated successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "admin_homepage.homepage"
                )
            )

        except IntegrityError:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_homepage_image(
                    new_image_url,
                    "homepage",
                )

            current_app.logger.exception(
                "Duplicate or invalid database value "
                "while updating homepage section."
            )

            flash(
                "The section could not be updated because "
                "the section key may already exist. "
                "Please choose a different key.",
                "danger",
            )

        except (ValueError, RuntimeError) as exc:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_homepage_image(
                    new_image_url,
                    "homepage",
                )

            flash(
                str(exc),
                "danger",
            )

        except Exception as exc:
            db.session.rollback()

            if (
                new_image_url
                and new_image_url != old_image_url
            ):
                delete_homepage_image(
                    new_image_url,
                    "homepage",
                )

            current_app.logger.exception(
                "Failed to update homepage section: %s",
                exc,
            )

            flash(
                "Unable to update homepage section right now. "
                "Please try again.",
                "danger",
            )

    elif request.method == "POST":
        flash_form_errors(form)

    return render_template(
        "admin/homepage_section_form.html",
        form=form,
        section=section,
        page_title="Edit Homepage Section",
    )


@homepage_bp.route(
    "/sections/<int:section_id>/toggle",
    methods=["POST"],
)
@login_required
def toggle_section(section_id):

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    section = (
        HomepageSection.query
        .get_or_404(section_id)
    )

    try:
        section.is_active = not bool(
            section.is_active
        )

        db.session.commit()

        status = (
            "published"
            if section.is_active
            else "hidden"
        )

        flash(
            f'"{section.title or section.key}" '
            f"is now {status}.",
            "success",
        )

    except Exception as exc:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to toggle homepage section: %s",
            exc,
        )

        flash(
            "Unable to change the section status. "
            "Please try again.",
            "danger",
        )

    return redirect(
        url_for(
            "admin_homepage.homepage"
        )
    )


@homepage_bp.route(
    "/sections/<int:section_id>/delete",
    methods=["POST"],
)
@login_required
def delete_section(section_id):

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    section = (
        HomepageSection.query
        .get_or_404(section_id)
    )

    image_url = section.image_url
    section_name = (
        section.title
        or section.key
    )

    try:
        db.session.delete(section)
        db.session.commit()

        if image_url:
            delete_homepage_image(
                image_url,
                "homepage",
            )

        flash(
            f'"{section_name}" was deleted successfully.',
            "success",
        )

    except Exception as exc:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to delete homepage section: %s",
            exc,
        )

        flash(
            "Unable to delete homepage section. "
            "Please try again.",
            "danger",
        )

    return redirect(
        url_for(
            "admin_homepage.homepage"
        )
    )


# ----------------------------------------------------------------------
# SECTION REORDERING
# ----------------------------------------------------------------------

@homepage_bp.route(
    "/sections/reorder",
    methods=["POST"],
)
@login_required
def reorder_sections():

    if not admin_required():
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Unauthorized.",
                }
            ),
            403,
        )

    data = request.get_json(
        silent=True
    )

    if not isinstance(data, dict):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid request data.",
                }
            ),
            400,
        )

    section_ids = data.get("section_ids")

    if not isinstance(section_ids, list):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid section order.",
                }
            ),
            400,
        )

    if not section_ids:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "No sections were provided.",
                }
            ),
            400,
        )

    try:
        cleaned_ids = []

        for section_id in section_ids:

            try:
                section_id = int(section_id)
            except (TypeError, ValueError):
                return (
                    jsonify(
                        {
                            "success": False,
                            "message": (
                                "One or more section IDs "
                                "are invalid."
                            ),
                        }
                    ),
                    400,
                )

            if section_id not in cleaned_ids:
                cleaned_ids.append(section_id)

        sections = (
            HomepageSection.query
            .filter(
                HomepageSection.id.in_(cleaned_ids)
            )
            .all()
        )

        sections_by_id = {
            section.id: section
            for section in sections
        }

        for index, section_id in enumerate(
            cleaned_ids
        ):
            section = sections_by_id.get(
                section_id
            )

            if section:
                section.sort_order = index

        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Homepage order updated.",
            }
        )

    except Exception as exc:
        db.session.rollback()

        current_app.logger.exception(
            "Failed to reorder homepage sections: %s",
            exc,
        )

        return (
            jsonify(
                {
                    "success": False,
                    "message": (
                        "Unable to save section order. "
                        "Please try again."
                    ),
                }
            ),
            500,
        )


# ----------------------------------------------------------------------
# HOMEPAGE SETTINGS
# ----------------------------------------------------------------------

@homepage_bp.route(
    "/settings",
    methods=["GET", "POST"],
)
@login_required
def settings():

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    homepage_settings = (
        HomepageSetting.query.first()
    )

    if homepage_settings is None:
        homepage_settings = HomepageSetting(
            site_title=None,
            meta_description=None,
            meta_keywords=None,
            og_image_url=None,
            announcement_text=None,
            announcement_url=None,
            announcement_active=False,
            is_active=True,
        )

    form = HomepageSettingsForm(
        obj=homepage_settings
    )

    if form.validate_on_submit():

        announcement_text = normalize_text(
            form.announcement_text.data
        )

        if (
            form.announcement_active.data
            and not announcement_text
        ):
            flash(
                "Please enter announcement text before "
                "enabling the announcement bar.",
                "danger",
            )

            return render_template(
                "admin/homepage_settings.html",
                form=form,
                settings=homepage_settings,
            )

        try:
            if HomepageSetting.query.first() is None:
                db.session.add(
                    homepage_settings
                )

            homepage_settings.site_title = (
                normalize_text(
                    form.site_title.data
                )
            )

            homepage_settings.meta_description = (
                normalize_text(
                    form.meta_description.data
                )
            )

            homepage_settings.meta_keywords = (
                normalize_text(
                    form.meta_keywords.data
                )
            )

            homepage_settings.og_image_url = (
                normalize_text(
                    form.og_image_url.data
                )
            )

            homepage_settings.announcement_text = (
                announcement_text
            )

            homepage_settings.announcement_url = (
                normalize_text(
                    form.announcement_url.data
                )
            )

            homepage_settings.announcement_active = (
                bool(
                    form.announcement_active.data
                )
            )

            homepage_settings.is_active = bool(
                form.is_active.data
            )

            db.session.commit()

            flash(
                "Homepage settings updated successfully.",
                "success",
            )

            return redirect(
                url_for(
                    "admin_homepage.settings"
                )
            )

        except IntegrityError:
            db.session.rollback()

            current_app.logger.exception(
                "Database integrity error while "
                "saving homepage settings."
            )

            flash(
                "Homepage settings could not be saved "
                "because of a database conflict. "
                "Please try again.",
                "danger",
            )

        except Exception as exc:
            db.session.rollback()

            current_app.logger.exception(
                "Failed to update homepage settings: %s",
                exc,
            )

            flash(
                "Unable to save homepage settings right now. "
                "Please try again.",
                "danger",
            )

    elif request.method == "POST":
        flash_form_errors(form)

    return render_template(
        "admin/homepage_settings.html",
        form=form,
        settings=homepage_settings,
    )


# ----------------------------------------------------------------------
# HOMEPAGE PREVIEW
# ----------------------------------------------------------------------

@homepage_bp.route(
    "/preview"
)
@login_required
def preview():

    if not admin_required():
        return redirect(
            url_for("home.home")
        )

    return redirect(
        url_for(
            "home.home",
            preview="1",
        )
    )