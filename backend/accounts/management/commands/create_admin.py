import getpass

from django.core.management.base import BaseCommand, CommandError
from pymongo.errors import DuplicateKeyError

from accounts.security import hash_password, utc_now
from accounts.serializers import RegistrationSerializer
from accounts.mongo import get_auth_database


class Command(BaseCommand):
    help = "Create a verified administrator account in MongoDB."

    def add_arguments(self, parser):
        parser.add_argument("--promote-email", help="Explicitly promote an existing active, verified account after confirmation.")

    def handle(self, *args, **options):
        if options.get("promote_email"):
            email = options["promote_email"].strip().casefold()
            db = get_auth_database()
            user = db.users.find_one({"email": email})
            if not user or not user.get("is_active") or not user.get("is_verified"):
                raise CommandError("Only an existing active, verified account can be promoted.")
            if user.get("role") == "admin":
                raise CommandError("That account is already an administrator.")
            confirmation = input(f"Promote verified account {email} to administrator? Type PROMOTE to continue: ").strip()
            if confirmation != "PROMOTE":
                raise CommandError("Administrator promotion was not confirmed.")
            result = db.users.update_one({"_id": user["_id"], "role": user.get("role"), "is_active": True, "is_verified": True},
                                         {"$set": {"role": "admin", "updated_at": utc_now()}})
            if result.modified_count != 1:
                raise CommandError("Account changed during promotion; reload and try again.")
            self.stdout.write(self.style.SUCCESS(f"Verified account {email} promoted to administrator."))
            return
        username = input("Username: ").strip()
        email = input("Email: ").strip()
        password = getpass.getpass("Password: ")
        password_confirmation = getpass.getpass("Confirm password: ")

        serializer = RegistrationSerializer(data={
            "username": username,
            "email": email,
            "password": password,
            "password_confirmation": password_confirmation,
        })
        if not serializer.is_valid():
            errors = "; ".join(
                f"{field}: {', '.join(messages)}"
                for field, messages in serializer.errors.items()
            )
            raise CommandError(errors)

        user_data = serializer.validated_data
        now = utc_now()
        admin = {
            "username": user_data["username"],
            "email": user_data["email"],
            "password_hash": hash_password(user_data["password"]),
            "role": "admin",
            "is_active": True,
            "is_verified": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "full_name": "",
            "avatar": "",
            "bio": "",
        }

        try:
            get_auth_database().users.insert_one(admin)
        except DuplicateKeyError as exc:
            raise CommandError("An account already uses that username or email.") from exc

        self.stdout.write(self.style.SUCCESS(f"Administrator account created for {admin['email']}."))
