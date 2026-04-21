from __future__ import annotations

from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_name(value: str) -> str:
    return " ".join(value.strip().split())


def apply_user_names(user: User, full_name: str) -> None:
    normalized = normalize_name(full_name)
    first, _, last = normalized.partition(" ")
    user.first_name = first[:150]
    user.last_name = last[:150]


def unique_username_for_email(email: str) -> str:
    normalized = normalize_email(email)
    base = normalized if len(normalized) <= 150 else normalized.split("@", 1)[0]
    base = base[:150] or "user"
    candidate = base
    suffix = 1
    while User.objects.filter(username__iexact=candidate).exists():
        marker = f"-{suffix}"
        candidate = f"{base[:150 - len(marker)]}{marker}"
        suffix += 1
    return candidate


def build_invitation_accept_url(token: str, request=None) -> str:
    template = getattr(settings, "BURN_RATE_INVITATION_ACCEPT_URL", "")
    if template:
        if "{token}" in template:
            return template.format(token=token)
        separator = "&" if "?" in template else "?"
        return f"{template}{separator}{urlencode({'token': token})}"

    frontend_base = getattr(settings, "BURN_RATE_FRONTEND_URL", "").rstrip("/")
    if frontend_base:
        return f"{frontend_base}/invite/{token}"

    path = f"/invite/{token}"
    if request is not None:
        return request.build_absolute_uri(path)
    return path


def send_invitation_email(invitation, token: str, accept_url: str) -> bool:
    if not getattr(settings, "BURN_RATE_SEND_INVITATION_EMAIL", False):
        return False

    subject = getattr(settings, "BURN_RATE_INVITATION_EMAIL_SUBJECT", "Invitacion a Burn Rate")
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
    custom_message = f"\n{invitation.message}\n" if invitation.message else ""
    body = (
        f"Hola {invitation.display_name},\n\n"
        "Te invitaron a Burn Rate."
        f"{custom_message}\n"
        "Abre este enlace para crear tu acceso:\n\n"
        f"{accept_url}\n\n"
        "Si no esperabas esta invitacion, puedes ignorar este correo."
    )
    send_mail(subject, body, from_email, [invitation.email], fail_silently=False)
    return True
