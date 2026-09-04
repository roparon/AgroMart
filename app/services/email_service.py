from flask import render_template
from flask_mail import Message

from app import mail


def send_email(
    subject,
    recipients,
    template,
    **kwargs
):
    """
    Send an HTML email using a Jinja template.
    """

    try:

        msg = Message(
            subject=subject,
            recipients=recipients,
        )

        msg.html = render_template(
            template,
            **kwargs
        )

        mail.send(msg)

        print(
            f"EMAIL SENT SUCCESSFULLY TO: {recipients}"
        )

        return True

    except Exception as e:

        print(
            f"EMAIL SENDING FAILED: {type(e).__name__}: {e}"
        )

        return False