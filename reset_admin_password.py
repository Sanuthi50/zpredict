#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(r'c:\Sanuthi BSC\Sem 3\Zpredict\zpredict')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
django.setup()

from api.models import User

def reset_admin_password():
    """Reset admin password to a known value"""
    print("=== Admin Password Reset ===\n")
    
    # Find admin user
    admin_user = User.objects.filter(user_type='admin').first()
    if not admin_user:
        print("No admin user found!")
        return
    
    print(f"Found admin user: {admin_user.email}")
    
    # Reset password to 'admin123'
    new_password = 'admin123'
    admin_user.set_password(new_password)
    admin_user.save()
    
    print(f"Password reset successfully!")
    print(f"Email: {admin_user.email}")
    print(f"New Password: {new_password}")
    print(f"User permissions: is_staff={admin_user.is_staff}, is_superuser={admin_user.is_superuser}")

if __name__ == '__main__':
    reset_admin_password()
