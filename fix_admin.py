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

def fix_admin_permissions():
    """Check and fix admin user permissions"""
    print("=== Admin User Permission Checker ===\n")
    
    # Get all users with admin user_type
    admin_users = User.objects.filter(user_type='admin')
    
    if not admin_users.exists():
        print("❌ No admin users found with user_type='admin'")
        print("Creating a test admin user...")
        
        # Create a test admin user
        admin = User.objects.create_user(
            email='admin@test.com',
            password='admin123',
            first_name='Test',
            last_name='Admin',
            user_type='admin',
            is_staff=True,
            is_superuser=True
        )
        print(f"✅ Created test admin: {admin.email}")
        print("   Password: admin123")
        print("   is_staff: True")
        print("   is_superuser: True")
        return
    
    print(f"Found {admin_users.count()} admin user(s):\n")
    
    for user in admin_users:
        print(f"User: {user.email}")
        print(f"  - user_type: {user.user_type}")
        print(f"  - is_staff: {user.is_staff}")
        print(f"  - is_superuser: {user.is_superuser}")
        print(f"  - is_admin (property): {user.is_admin}")
        print(f"  - is_active: {user.is_active}")
        
        # Fix permissions if needed
        needs_update = False
        if not user.is_staff:
            user.is_staff = True
            needs_update = True
            print("  ✅ Fixed: Set is_staff = True")
            
        if not user.is_active:
            user.is_active = True
            needs_update = True
            print("  ✅ Fixed: Set is_active = True")
            
        if needs_update:
            user.save()
            print("  💾 User updated!")
        else:
            print("  ✅ User permissions are correct!")
        
        print()

if __name__ == '__main__':
    fix_admin_permissions()
