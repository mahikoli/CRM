#!/usr/bin/env python3
"""
Bootstrap / promote a user to Super Admin.
Can be executed locally or inside Render's web shell:

Usage:
  python create_admin.py --email admin@example.com --password YourSecretPassword --name "Admin User"
  python create_admin.py  (interactive prompts)
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

# Ensure backend root is in python path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.database import Base, engine, SessionLocal
from app.models import User, Role, AuditLog
from app.security import hash_password

DEFAULT_ROLES = [
    "Super Admin", "Management", "Sales / Business Development",
    "Internship Coordinator", "Training Coordinator", "Finance / Accounts",
    "Marketing Executive", "Project / Team Manager", "Employee / Intern"
]

def bootstrap_admin(email: str, password: str, full_name: str = "Super Administrator"):
    email = email.strip().lower()
    if not email or "@" not in email:
        print("[ERROR] Please provide a valid email address.")
        sys.exit(1)
    if not password or len(password) < 6:
        print("[ERROR] Password must be at least 6 characters.")
        sys.exit(1)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        # Ensure default roles exist
        for role_name in DEFAULT_ROLES:
            if not db.query(Role).filter(Role.name == role_name).first():
                db.add(Role(name=role_name))
        db.commit()

        super_admin_role = db.query(Role).filter(Role.name == "Super Admin").first()
        if not super_admin_role:
            print("[ERROR] Failed to locate or create 'Super Admin' role.")
            sys.exit(1)

        user = db.query(User).filter(User.email == email).first()
        if user:
            # User already exists - promote and update password if provided
            user.full_name = full_name or user.full_name
            user.password_hash = hash_password(password)
            user.is_active = True
            if super_admin_role not in user.roles:
                user.roles.append(super_admin_role)
            db.add(AuditLog(user_id=user.id, action="user.promoted_admin", entity_type="user", entity_id=str(user.id)))
            db.commit()
            print(f"[SUCCESS] Existing user '{email}' was updated and promoted to Super Admin!")
        else:
            # Create brand new Super Admin user
            user = User(
                full_name=full_name,
                email=email,
                password_hash=hash_password(password),
                is_active=True,
            )
            user.roles.append(super_admin_role)
            db.add(user)
            db.flush()
            db.add(AuditLog(user_id=user.id, action="user.created_admin", entity_type="user", entity_id=str(user.id)))
            db.commit()
            print(f"[SUCCESS] New Super Admin user '{email}' created successfully (ID: {user.id})!")

def main():
    parser = argparse.ArgumentParser(description="Create or promote a Super Admin user.")
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL"), help="Admin email address")
    parser.add_argument("--password", default=os.getenv("ADMIN_PASSWORD"), help="Admin password")
    parser.add_argument("--name", default=os.getenv("ADMIN_NAME", "Super Administrator"), help="Admin full name")

    args = parser.parse_args()

    email = args.email
    password = args.password
    name = args.name

    if not email:
        try:
            email = input("Admin Email: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if not password:
        try:
            password = getpass.getpass("Admin Password: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            sys.exit(0)

    if not name:
        try:
            name_input = input("Admin Full Name [Super Administrator]: ").strip()
            name = name_input or "Super Administrator"
        except (KeyboardInterrupt, EOFError):
            name = "Super Administrator"

    bootstrap_admin(email, password, name)

if __name__ == "__main__":
    main()
