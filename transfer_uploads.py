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

def transfer_uploads():
    """Transfer all uploads to the current admin user"""
    print("=== Upload Transfer ===\n")
    
    # Get current admin user (the one you're using)
    current_admin = User.objects.filter(email='Admin@gmail.com').first()
    if not current_admin:
        print("Current admin user not found!")
        return
    
    # Get the admin user who owns the uploads
    old_admin = User.objects.filter(email='Hello@gmail.com').first()
    if not old_admin:
        print("Old admin user not found!")
        return
    
    print(f"Current admin: {current_admin.email}")
    print(f"Old admin: {old_admin.email}")
    
    # Get all uploads from the old admin
    uploads_to_transfer = AdminUpload.objects.filter(admin=old_admin)
    print(f"\nUploads to transfer: {uploads_to_transfer.count()}")
    
    if uploads_to_transfer.count() == 0:
        print("No uploads to transfer!")
        return
    
    # Transfer uploads and activate them
    transferred_count = 0
    for upload in uploads_to_transfer:
        print(f"Transferring: {upload.original_filename} (Status: {upload.processing_status})")
        upload.admin = current_admin
        upload.active = True  # Make sure they're active
        upload.save()
        transferred_count += 1
    
    print(f"\n✅ Successfully transferred {transferred_count} uploads!")
    print(f"All uploads are now associated with {current_admin.email}")
    
    # Show final status
    current_admin_uploads = AdminUpload.objects.filter(admin=current_admin, active=True)
    print(f"\nFinal count for {current_admin.email}: {current_admin_uploads.count()} active uploads")
    
    for upload in current_admin_uploads:
        print(f"  - {upload.original_filename} ({upload.processing_status})")

if __name__ == '__main__':
    transfer_uploads()
