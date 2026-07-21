import argparse
import os
from getpass import getpass

from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select

from .db import SessionLocal
from .models import User, utc_now
from .security import hash_password


def _normalized_email(value: str) -> str:
    try:
        return validate_email(value, check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise SystemExit(f"Invalid email: {exc}") from exc


def create_admin(email: str, display_name: str) -> None:
    normalized_email = _normalized_email(email)
    password = os.getenv("ADMIN_PASSWORD")
    with SessionLocal() as db:
        user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
        if user is None:
            password = password or getpass("New administrator password: ")
            if len(password) < 8 or len(password) > 128:
                raise SystemExit("Password must contain between 8 and 128 characters")
            user = User(
                email=normalized_email,
                password_hash=hash_password(password),
                display_name=display_name.strip() or "Administrator",
                role="admin",
                is_active=True,
                updated_at=utc_now(),
            )
            db.add(user)
            action = "created"
        else:
            user.role = "admin"
            user.is_active = True
            user.display_name = display_name.strip() or user.display_name
            user.updated_at = utc_now()
            if password:
                if len(password) < 8 or len(password) > 128:
                    raise SystemExit("Password must contain between 8 and 128 characters")
                user.password_hash = hash_password(password)
            action = "promoted"
        db.commit()
        print(f"Administrator {action}: {normalized_email}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LearnMate AI administration commands")
    subparsers = parser.add_subparsers(dest="command", required=True)
    create = subparsers.add_parser("create-admin", help="Create or promote an administrator")
    create.add_argument("--email", required=True)
    create.add_argument("--display-name", default="Administrator")
    args = parser.parse_args()
    if args.command == "create-admin":
        create_admin(args.email, args.display_name)


if __name__ == "__main__":
    main()
