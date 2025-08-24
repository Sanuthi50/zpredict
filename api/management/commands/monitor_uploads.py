from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.utils import process_stuck_uploads_automatically
import time
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor and automatically process stuck PDF uploads'

    def add_arguments(self, parser):
        parser.add_argument(
            '--interval',
            type=int,
            default=300,  # 5 minutes
            help='Check interval in seconds (default: 300)'
        )
        parser.add_argument(
            '--max-age',
            type=int,
            default=1,
            help='Maximum age in hours before processing stuck uploads (default: 1)'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (continuous monitoring)'
        )

    def handle(self, *args, **options):
        interval = options['interval']
        max_age = options['max_age']
        daemon_mode = options['daemon']
        
        self.stdout.write(f"Starting upload monitor (interval: {interval}s, max age: {max_age}h)")
        
        if daemon_mode:
            self.stdout.write("Running in daemon mode - press Ctrl+C to stop")
            try:
                while True:
                    self.check_and_process_uploads(max_age)
                    time.sleep(interval)
            except KeyboardInterrupt:
                self.stdout.write("\nMonitoring stopped by user")
        else:
            self.check_and_process_uploads(max_age)

    def check_and_process_uploads(self, max_age_hours):
        """Check for stuck uploads and process them"""
        try:
            processed_count = process_stuck_uploads_automatically(max_age_hours)
            
            if processed_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f"[{timezone.now()}] Processed {processed_count} stuck uploads")
                )
            else:
                self.stdout.write(f"[{timezone.now()}] No stuck uploads found")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"[{timezone.now()}] Monitor error: {e}")
            )
            logger.error(f"Upload monitor error: {e}")
