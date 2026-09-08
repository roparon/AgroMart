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
from werkzeug.utils import secure_filename

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

MAX_IMAGE_SIZE = 5 * 1024 * 1024


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
# IMAGE HELPERS
# ----------------------------------------------------------------------

def allowed_file(filename):
    """
    Return True when the uploaded filename has an allowed extension.
    """

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def save_homepage_image(image, folder="home"):
    """
    Save a homepage image safely using a UUID filename.

    Returns the public URL of the saved image.
    """

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
        raise ValueError(
            "Image must be smaller than 5 MB."
        )

    original_name = secure_filename(
        image.filename
    )

    if not original_name:
        raise ValueError(
            "Invalid image filename."
        )

    extension = original_name.rsplit(
        ".",
        1,
    )[1].lower()

    filename = (
        f"{uuid.uuid4().hex}.{extension}"
    )

    upload_dir = os.path.join(
        current_app.static_folder,
        "uploads",
        folder,
    )

    os.makedirs(
        upload_dir,
        exist_ok=True,
    )

    image_path = os.path.join(
        upload_dir,
        filename,
    )

    image.save(image_path)

    return (
        f"/static/uploads/{folder}/{filename}"
    )


def delete_homepage_image(
    image_url,
    folder="home",
):
    """
    Delete an image only when it belongs to our
    managed homepage upload directory.
    """

    if not image_url:
        return

    prefix = (
        f"/static/uploads/{folder}/"
    )

    if not image_url.startswith(prefix):
        return

    filename = os.path.basename(
        image_url
    )

    if not filename:
        return

    upload_dir = os.path.join(
        current_app.static_folder,
        "uploads",
        folder,
    )

    image_path = os.path.join(
        upload_dir,
        filename,
    )

    if os.path.isfile(image_path):
        try:
            os.remove(image_path)
        except OSError:
            current_app.logger.warning(
                "Unable to delete homepage image: %s",
                image_path,
            )


# ----------------------------------------------------------------------
# JSON CONFIG HELPERS
# ----------------------------------------------------------------------

def parse_config(value):
    """
    Convert the configuration textarea into a Python dictionary.

    Empty configuration becomes {}.
    """

    if not value:
        return {}

    if isinstance(value, dict):
        return value

    try:
        parsed = json.loads(value)

        if not isinstance(parsed, dict):
            raise ValueError(
                "Configuration must be a JSON object."
            )

        return parsed

    except (TypeError, json.JSONDecodeError):
        raise ValueError(
            "Section configuration must contain valid JSON."
        )


def normalize_text(value):
    """
    Safely normalize optional text form fields.
    """

    if value is None:
        return None

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

    settings = (
        HomepageSetting.query
        .first()
    )

    return render_template(
        "admin/homepage.html",
        content=content,
        sections=sections,
        settings=settings,
    )


# ----------------------------------------------------------------------
# HOMEPAGE CONTENT
# Existing system — preserved
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

        key = normalize_text(
            form.key.data
        )

        existing = (
            HomepageContent.query
            .filter_by(key=key)
            .first()
        )

        if existing:
            flash(
                f'Content key "{key}" already exists.',
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

                is_active=form.is_active.data,

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
                "Unable to create homepage content.",
                "danger",
            )

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
                f'Content key "{new_key}" already exists.',
                "danger",
            )

            return render_template(
                "admin/homepage_form.html",
                form=form,
                content=content,
                page_title="Edit Homepage Content",
            )

        old_image_url = (
            content.image_url
        )

        new_image_url = (
            old_image_url
        )

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

            content.image_url = (
                new_image_url
            )

            content.image_alt = normalize_text(
                form.image_alt.data
            )

            content.css_class = normalize_text(
                form.css_class.data
            )

            content.is_active = (
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
                "Unable to update homepage content.",
                "danger",
            )

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

        content.is_active = (
            not content.is_active
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
            "Unable to change the content status.",
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
            "Unable to delete homepage content.",
            "danger",
        )

    return redirect(
        url_for(
            "admin_homepage.homepage"
        )
    )


# ----------------------------------------------------------------------
# HOMEPAGE SECTIONS
# New CMS system
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
                f'Section key "{key}" already exists.',
                "danger",
            )

            return render_template(
                "admin/homepage_section_form.html",
                form=form,
                section=None,
                page_title="Add Homepage Section",
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

                section_type=(
                    form.section_type.data
                ),

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

                is_active=(
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

        except ValueError as exc:

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
                "Unable to create homepage section.",
                "danger",
            )

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

    # Convert database JSON into textarea JSON.
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
                f'Section key "{new_key}" already exists.',
                "danger",
            )

            return render_template(
                "admin/homepage_section_form.html",
                form=form,
                section=section,
                page_title="Edit Homepage Section",
            )

        old_image_url = (
            section.image_url
        )

        new_image_url = (
            old_image_url
        )

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

            section.image_url = (
                new_image_url
            )

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

            section.is_active = (
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

        except ValueError as exc:

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
                "Unable to update homepage section.",
                "danger",
            )

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

        section.is_active = (
            not section.is_active
        )

        db.session.commit()

        status = (
            "published"
            if section.is_active
            else "hidden"
        )

        flash(
            f'"{section.title or section.key}" is now {status}.',
            "success",
        )

    except Exception as exc:

        db.session.rollback()

        current_app.logger.exception(
            "Failed to toggle homepage section: %s",
            exc,
        )

        flash(
            "Unable to change the section status.",
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
            "Unable to delete homepage section.",
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

    if not data:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid request.",
                }
            ),
            400,
        )

    section_ids = data.get(
        "section_ids"
    )

    if not isinstance(
        section_ids,
        list,
    ):
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Invalid section order.",
                }
            ),
            400,
        )

    try:

        for index, section_id in enumerate(
            section_ids
        ):

            try:
                section_id = int(
                    section_id
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            section = (
                HomepageSection.query
                .get(section_id)
            )

            if section:
                section.sort_order = (
                    index
                )

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
                    "message": "Unable to save section order.",
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
        HomepageSetting.query
        .first()
    )

    if homepage_settings is None:

        homepage_settings = HomepageSetting(
            site_title="Bomet Machineries Ltd.",
            is_active=True,
            announcement_active=False,
        )

        db.session.add(
            homepage_settings
        )

        db.session.commit()

    form = HomepageSettingsForm(
        obj=homepage_settings
    )

    if form.validate_on_submit():

        try:

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
                normalize_text(
                    form.announcement_text.data
                )
            )

            homepage_settings.announcement_url = (
                normalize_text(
                    form.announcement_url.data
                )
            )

            homepage_settings.announcement_active = (
                form.announcement_active.data
            )

            homepage_settings.is_active = (
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

        except Exception as exc:

            db.session.rollback()

            current_app.logger.exception(
                "Failed to update homepage settings: %s",
                exc,
            )

            flash(
                "Unable to update homepage settings.",
                "danger",
            )

    return render_template(
        "admin/homepage_settings.html",
        form=form,
        settings=homepage_settings,
    )


# ----------------------------------------------------------------------
# HOMEPAGE PREVIEW
# ----------------------------------------------------------------------

@homepage_bp.route("/preview")
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