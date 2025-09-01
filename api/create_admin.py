import os
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import AdminUser


class Command(BaseCommand):
    help = 'Create an admin user'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, help='Admin username', required=True)
        parser.add_argument('--email', type=str, help='Admin email', required=True)
        parser.add_argument('--password', type=str, help='Admin password (optional)')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options.get('password')

        if not password:
            password = self.get_password()

        # Check if admin already exists
        if AdminUser.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.ERROR(f'Admin user "{username}" already exists!')
            )
            return

        if AdminUser.objects.filter(email=email).exists():
            self.stdout.write(
                self.style.ERROR(f'Admin with email "{email}" already exists!')
            )
            return

        # Create admin user
        try:
            admin = AdminUser.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_admin=True,
                is_staff=True,
                is_superuser=True  # Make them superuser for Django admin access
            )
            
            self.stdout.write(
                self.style.SUCCESS(f'Admin user "{username}" created successfully!')
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating admin: {e}')
            )

    def get_password(self):
        """Get password from user input"""
        import getpass
        password = getpass.getpass('Enter admin password: ')
        password_confirm = getpass.getpass('Confirm password: ')
        
        if password != password_confirm:
            self.stdout.write(self.style.ERROR('Passwords do not match!'))
            return self.get_password()
        
        if len(password) < 8:
            self.stdout.write(self.style.ERROR('Password must be at least 8 characters!'))
            return self.get_password()
            
        return password
