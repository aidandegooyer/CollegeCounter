#!/usr/bin/env python3
"""
One-time script to set a Firebase custom claim for a user.

Usage examples:
  # using explicit service account file
  python3 set_user_role.py --uid USER_UID --role admin --service-account /path/to/serviceAccount.json

  # or use GOOGLE_APPLICATION_CREDENTIALS env var
  export GOOGLE_APPLICATION_CREDENTIALS="/path/to/serviceAccount.json"
  python3 set_user_role.py --uid USER_UID --privilege-level 2
"""

import argparse
import sys
import firebase_admin
from firebase_admin import credentials, auth


def init_app(service_account_path=None):
    if firebase_admin._apps:
        return
    if service_account_path:
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
    else:
        # will use GOOGLE_APPLICATION_CREDENTIALS if set
        firebase_admin.initialize_app()


def main():
    parser = argparse.ArgumentParser(
        description="Set Firebase user custom claims (role / privilege_level)."
    )
    parser.add_argument("--uid", required=True, help="Firebase user UID")
    parser.add_argument(
        "--role", choices=["none", "base", "admin", "owner"], help="Role string to set"
    )
    parser.add_argument(
        "--privilege-level",
        type=int,
        choices=[0, 1, 2, 3],
        help="Numeric privilege level (0..3)",
    )
    parser.add_argument(
        "--service-account", help="Path to service account JSON (optional)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show current claims and intended changes without applying",
    )
    args = parser.parse_args()

    try:
        init_app(args.service_account)
    except Exception as e:
        print("Failed to initialize Firebase Admin SDK:", e, file=sys.stderr)
        sys.exit(2)

    try:
        user = auth.get_user(args.uid)
    except auth.UserNotFoundError:
        print("User not found:", args.uid, file=sys.stderr)
        sys.exit(3)
    except Exception as e:
        print("Error fetching user:", e, file=sys.stderr)
        sys.exit(4)

    current = user.custom_claims or {}
    print("Current claims for", args.uid, ":", current)

    new_claims = dict(current)  # start from existing claims
    if args.role is not None:
        if args.role == "none":
            # remove role claim if present
            new_claims.pop("role", None)
        else:
            new_claims["role"] = args.role
    if args.privilege_level is not None:
        new_claims["privilege_level"] = args.privilege_level

    # If nothing to change:
    if new_claims == current:
        print("No changes to apply.")
        return

    print("New claims to apply:", new_claims)
    if args.dry_run:
        print("Dry run; not applying changes.")
        return

    try:
        auth.set_custom_user_claims(args.uid, new_claims)
        print("Successfully updated claims for", args.uid)
    except Exception as e:
        print("Failed to set claims:", e, file=sys.stderr)
        sys.exit(5)


if __name__ == "__main__":
    main()
