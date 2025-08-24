from django.core.management.base import BaseCommand
from api.models import AdminUpload
from api.tasks import process_pdf_and_create_vectorstore

class Command(BaseCommand):
    help = 'Reprocesses the latest active PDF upload'

    def handle(self, *args, **options):
        try:
            # Get the latest active upload
            upload = AdminUpload.objects.filter(active=True).latest('uploaded_at')
            
            # Reset processing status
            upload.processing_status = 'pending'
            upload.save()
            
            # Process the PDF
            process_pdf_and_create_vectorstore(upload.id)
            
            self.stdout.write(self.style.SUCCESS('Successfully reprocessed PDF'))
            
        except AdminUpload.DoesNotExist:
            self.stdout.write(self.style.ERROR('No active uploads found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
