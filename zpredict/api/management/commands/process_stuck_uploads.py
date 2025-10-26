from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import AdminUpload
from api.tasks import process_pdf_and_create_vectorstore


class Command(BaseCommand):
    help = 'Process stuck PDF uploads that have been pending for too long'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=1,
            help='Process uploads stuck for more than this many hours (default: 1)'
        )
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Process all pending uploads regardless of time'
        )

    def handle(self, *args, **options):
        hours_threshold = options['hours']
        force_all = options['force_all']
        
        # Find stuck uploads
        if force_all:
            stuck_uploads = AdminUpload.objects.filter(
                processing_status__in=['pending', 'processing']
            )
            self.stdout.write(f"Processing all {stuck_uploads.count()} pending/processing uploads...")
        else:
            cutoff_time = timezone.now() - timedelta(hours=hours_threshold)
            stuck_uploads = AdminUpload.objects.filter(
                processing_status__in=['pending', 'processing'],
                uploaded_at__lt=cutoff_time
            )
            self.stdout.write(f"Processing {stuck_uploads.count()} uploads stuck for more than {hours_threshold} hours...")

        if not stuck_uploads.exists():
            self.stdout.write(self.style.SUCCESS("No stuck uploads found."))
            return

        processed_count = 0
        failed_count = 0

        for upload in stuck_uploads:
            self.stdout.write(f"Processing upload {upload.id}: {upload.original_filename}")
            
            try:
                # Process synchronously
                result = process_pdf_and_create_vectorstore(upload.id)
                self.stdout.write(self.style.SUCCESS(f"[OK] Upload {upload.id} processed successfully: {result}"))
                processed_count += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"[FAIL] Upload {upload.id} failed: {str(e)}"))
                # Mark as failed
                upload.processing_status = 'failed'
                upload.save()
                failed_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nProcessing complete: {processed_count} successful, {failed_count} failed"
        ))
