"""Password hashing (PBKDF2-SHA256, standard library only), login, password change and roles."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets

from rfp import db

ITERATIONS = 200_000
ROLE_LABELS = {"evaluator": "Evaluator", "senior_reviewer": "Senior Reviewer"}
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return digest.hex(), salt


def _check(user: dict, password: str) -> bool:
    candidate, _ = hash_password(password or "", user["salt"])
    return hmac.compare_digest(candidate, user["password_hash"])


def authenticate(username: str, password: str) -> dict | None:
    """Return the user dict (without secrets) on success, else None. Every attempt is logged."""
    username = (username or "").strip().lower()
    user = db.get_user(username)
    ok = bool(user) and _check(user, password)
    db.log_event(username or "<blank>", "login", ok)
    if not ok:
        return None
    return {k: user[k] for k in ("user_id", "username", "full_name", "role", "password_set_by",
                                 "password_changed_at")}


def password_problems(new_password: str, username: str) -> list[str]:
    """Password policy. Returns the rules the new password breaks."""
    problems = []
    if len(new_password) < MIN_PASSWORD_LENGTH:
        problems.append(f"at least {MIN_PASSWORD_LENGTH} characters")
    if not re.search(r"[A-Za-z]", new_password) or not re.search(r"\d", new_password):
        problems.append("at least one letter and one number")
    if username and username.lower() in new_password.lower():
        problems.append("must not contain your username")
    return problems


def change_password(username: str, current: str, new: str, confirm: str) -> tuple[bool, str]:
    user = db.get_user(username)
    if not user or not _check(user, current):
        db.log_event(username, "password_change", False, "current password incorrect")
        return False, "Your current password is incorrect."
    if new != confirm:
        return False, "The new passwords don't match."
    if new == current:
        return False, "Choose a password you haven't just used."
    problems = password_problems(new, username)
    if problems:
        return False, "The new password needs " + ", ".join(problems) + "."
    pw_hash, salt = hash_password(new)
    db.set_password(username, pw_hash, salt)
    db.log_event(username, "password_change", True)
    return True, "Password changed."


def can_edit_criteria(user: dict | None) -> bool:
    return bool(user) and user.get("role") == "senior_reviewer"
