"""
Utility functions for automatic PDF processing and monitoring
"""
import os
import logging
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from .models import AdminUpload
from .tasks import process_pdf_and_create_vectorstore

logger = logging.getLogger(__name__)


def check_celery_worker_health():
    """Check if Celery worker is running and responsive"""
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        return bool(stats)
    except Exception as e:
        logger.warning(f"Celery health check failed: {e}")
        return False


def process_stuck_uploads_automatically(max_age_hours=1):
    """
    Automatically process uploads that have been stuck for too long.
    Returns number of uploads processed.
    """
    cutoff_time = timezone.now() - timedelta(hours=max_age_hours)
    stuck_uploads = AdminUpload.objects.filter(
        processing_status__in=['pending', 'processing'],
        uploaded_at__lt=cutoff_time
    )
    
    processed_count = 0
    for upload in stuck_uploads:
        try:
            logger.info(f"Auto-processing stuck upload {upload.id}: {upload.original_filename}")
            
            # Try Celery first if available
            if check_celery_worker_health():
                process_pdf_and_create_vectorstore.delay(upload.id)
                logger.info(f"Queued upload {upload.id} for Celery processing")
            else:
                # Fallback to synchronous processing
                result = process_pdf_and_create_vectorstore(upload.id)
                logger.info(f"Synchronously processed upload {upload.id}: {result}")
            
            processed_count += 1
            
        except Exception as e:
            logger.error(f"Failed to auto-process upload {upload.id}: {e}")
            upload.processing_status = 'failed'
            upload.save()
    
    return processed_count


def ensure_pdf_processing(upload_id, timeout_minutes=5):
    """
    Ensure a PDF upload gets processed within a reasonable time.
    Falls back to synchronous processing if Celery fails.
    """
    try:
        upload = AdminUpload.objects.get(id=upload_id)
        
        # If already completed, return
        if upload.processing_status == 'completed':
            return True
            
        # Try Celery first
        if check_celery_worker_health():
            task = process_pdf_and_create_vectorstore.delay(upload_id)
            logger.info(f"Queued upload {upload_id} for Celery processing")
            return True
        else:
            # Fallback to synchronous processing
            logger.warning(f"Celery unavailable, processing upload {upload_id} synchronously")
            result = process_pdf_and_create_vectorstore(upload_id)
            logger.info(f"Synchronously processed upload {upload_id}: {result}")
            return True
            
    except Exception as e:
        logger.error(f"Failed to ensure processing for upload {upload_id}: {e}")
        return False
