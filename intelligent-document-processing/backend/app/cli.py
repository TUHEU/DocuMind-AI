"""Command line helpers. Run from the backend folder:

    .\\.venv\\Scripts\\python.exe -m app.cli create-admin --email you@example.com --name "Your Name"

The password is typed at a hidden prompt, so it never appears in your history or in any file.
"""
import argparse
import getpass
import sys

from sqlalchemy import select

from app.core.security import hash_password
from app.database.connection import get_sessionmaker
from app.models import User
from app.services.audit import record_audit


def create_admin(email: str, name: str, password: str | None = None) -> int:
    email = email.strip().lower()
    if password is None:
        password = getpass.getpass("Password (min 8 characters): ")
        if password != getpass.getpass("Repeat password: "):
            print("The two passwords are different.")
            return 1
    if len(password) < 8:
        print("The password must have at least 8 characters.")
        return 1
    with get_sessionmaker()() as db:
        if db.scalar(select(User.user_id).where(User.email == email)):
            print(f"A user with e-mail {email} already exists.")
            return 1
        user = User(email=email, full_name=name, password_hash=hash_password(password), role="ADMIN")
        db.add(user)
        db.flush()
        record_audit(db, "USER_CREATE", actor_id=None, entity_type="user", entity_id=user.user_id, after={"role": "ADMIN", "via": "cli"})
        db.commit()
    print(f"Administrator {email} created.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create-admin", help="create the first administrator")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    args = parser.parse_args(argv)
    if args.cmd == "create-admin":
        return create_admin(args.email, args.name)
    return 1


if __name__ == "__main__":
    sys.exit(main())
