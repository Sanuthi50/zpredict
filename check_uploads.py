#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(r'c:\Sanuthi BSC\Sem 3\Zpredict\zpredict')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'zpredict.settings')
django.setup()

from api.models import AdminUpload, User

def check_upload_status():
    """Check all uploads and their statuses"""
    print("=== Upload Status Check ===\n")
    
    # Get admin user
    admin_user = User.objects.filter(user_type='admin').first()
    if not admin_user:
        print("No admin user found!")
        return
    
    print(f"Admin user: {admin_user.email}")
    print(f"Admin ID: {admin_user.id}")
    
    # Get all uploads
    all_uploads = AdminUpload.objects.all()
    print(f"\nTotal uploads in database: {all_uploads.count()}")
    
    if all_uploads.count() == 0:
        print("No uploads found in database!")
        return
    
    print("\nAll uploads:")
    for upload in all_uploads:
        print(f"  ID: {upload.id}")
        print(f"  Filename: {upload.original_filename}")
        print(f"  Admin: {upload.admin.email} (ID: {upload.admin.id})")
        print(f"  Status: {upload.processing_status}")
        print(f"  Active: {upload.active}")
        print(f"  Uploaded: {upload.uploaded_at}")
        print("  ---")
    
    # Check uploads for the specific admin user
    admin_uploads = AdminUpload.objects.filter(admin=admin_user)
    print(f"\nUploads for admin {admin_user.email}: {admin_uploads.count()}")
    
    active_admin_uploads = AdminUpload.objects.filter(admin=admin_user, active=True)
    print(f"Active uploads for admin {admin_user.email}: {active_admin_uploads.count()}")
    
    # Check by status
    pending_uploads = AdminUpload.objects.filter(admin=admin_user, processing_status='pending')
    completed_uploads = AdminUpload.objects.filter(admin=admin_user, processing_status='completed')
    processing_uploads = AdminUpload.objects.filter(admin=admin_user, processing_status='processing')
    failed_uploads = AdminUpload.objects.filter(admin=admin_user, processing_status='failed')
    
    print(f"\nStatus breakdown for admin {admin_user.email}:")
    print(f"  Pending: {pending_uploads.count()}")
    print(f"  Processing: {processing_uploads.count()}")
    print(f"  Completed: {completed_uploads.count()}")
    print(f"  Failed: {failed_uploads.count()}")
    
    # Check if uploads have no admin assigned
    orphaned_uploads = AdminUpload.objects.filter(admin__isnull=True)
    print(f"\nOrphaned uploads (no admin): {orphaned_uploads.count()}")
    
    # Check uploads by different admin users
    all_admin_users = User.objects.filter(user_type='admin')
    print(f"\nAll admin users: {all_admin_users.count()}")
    for admin in all_admin_users:
        user_uploads = AdminUpload.objects.filter(admin=admin)
        print(f"  {admin.email}: {user_uploads.count()} uploads")

if __name__ == '__main__':
    check_upload_status()
