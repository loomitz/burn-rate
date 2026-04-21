from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a local staff user for Burn Rate."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("email")
        parser.add_argument("--password", default="burnrate123")

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]
        if len(password) < 8:
            raise CommandError("Password must be at least 8 characters.")
        user, created = User.objects.get_or_create(username=username, defaults={"email": email})
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{verb} local user {username}"))

