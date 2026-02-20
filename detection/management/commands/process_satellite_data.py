"""
Django management command to process real satellite data
Run with: python manage.py process_satellite_data --region-id 2
"""

from django.core.management.base import BaseCommand, CommandError
import sys
from pathlib import Path

# Add scripts directory to path
scripts_dir = Path(__file__).parent.parent.parent.parent / 'scripts'
sys.path.insert(0, str(scripts_dir))

from process_real_satellite_data import RealSatelliteDataProcessor


class Command(BaseCommand):
    help = 'Process real satellite data through ML model and create detections'

    def add_arguments(self, parser):
        parser.add_argument(
            '--region-id',
            type=int,
            help='MonitoringRegion ID to process',
            default=None
        )
        parser.add_argument(
            '--days-back',
            type=int,
            default=7,
            help='Number of days back to search for data'
        )
        parser.add_argument(
            '--source',
            choices=['goes', 'sentinel'],
            default='goes',
            help='Satellite data source'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🛰️  REAL SATELLITE DATA PROCESSOR\n'))
        
        try:
            processor = RealSatelliteDataProcessor()
            processor.process_region(
                region_id=options['region_id'],
                days_back=options['days_back']
            )
            self.stdout.write(self.style.SUCCESS('✓ Processing complete!'))
        except Exception as e:
            raise CommandError(f'Error processing satellite data: {e}')
