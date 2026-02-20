"""
Management command to perform live monitoring of Sentinel Hub imagery.

Usage:
    python manage.py monitor_sentinel --region-id 1 --days 7
    python manage.py monitor_sentinel --region-id 1 --start 2026-02-10 --end 2026-02-16
"""

import os
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from detection.models import MonitoringRegion, SatelliteImage, OilSpillDetection, Alert
from detection.sentinelhub_integration import get_sentinel_client, process_sentinel_image
from detection.ml_inference import predict_oil_spill

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Monitor Sentinel Hub for new oil spill imagery'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--region-id',
            type=int,
            help='Monitoring region ID to check'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Look back N days for imagery (default: 7)'
        )
        parser.add_argument(
            '--start',
            type=str,
            help='Start date (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--end',
            type=str,
            help='End date (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--auto-detect',
            action='store_true',
            help='Automatically run oil spill detection on downloaded images'
        )
    
    def handle(self, *args, **options):
        """Main command handler."""
        
        # Get Sentinel Hub client
        client = get_sentinel_client()
        if not client:
            raise CommandError(
                "Sentinel Hub not configured. "
                "Set SENTINEL_CLIENT_ID and SENTINEL_CLIENT_SECRET environment variables."
            )
        
        # Get monitoring regions
        regions = self._get_monitoring_regions(options)
        if not regions:
            self.stdout.write(self.style.WARNING("No monitoring regions found"))
            return
        
        # Get date range
        start_date, end_date = self._get_date_range(options)
        self.stdout.write(f"Searching for imagery between {start_date} and {end_date}")
        
        # Monitor each region
        total_imagery = 0
        total_detections = 0
        
        for region in regions:
            self.stdout.write(f"\n📍 Monitoring: {region.name}")
            
            # Parse bounding box
            try:
                boundary = json.loads(region.boundary) if isinstance(region.boundary, str) else region.boundary
                bbox = self._parse_bbox(boundary)
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Invalid boundary: {e}"))
                continue
            
            # Query and download imagery
            imagery_count = self._download_imagery(client, region, bbox, start_date, end_date)
            total_imagery += imagery_count
            
            # Optionally run automatic detection
            if options['auto_detect']:
                detection_count = self._run_detection(region)
                total_detections += detection_count
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✓ Monitoring complete!\n"
            f"  Downloaded: {total_imagery} images\n"
            f"  Detections: {total_detections} oil spills found"
        ))
    
    def _get_monitoring_regions(self, options) -> list:
        """Get monitoring regions to check."""
        if options.get('region_id'):
            try:
                return [MonitoringRegion.objects.get(id=options['region_id'])]
            except MonitoringRegion.DoesNotExist:
                raise CommandError(f"Region with ID {options['region_id']} not found")
        else:
            # Monitor all active regions
            regions = MonitoringRegion.objects.filter(active=True)
            if not regions.exists():
                return []
            return list(regions)
    
    def _get_date_range(self, options) -> tuple:
        """Parse date range from options."""
        if options.get('start') and options.get('end'):
            return options['start'], options['end']
        else:
            # Default: last N days
            days = options.get('days', 7)
            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=days)
            return start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')
    
    def _parse_bbox(self, boundary) -> tuple:
        """Extract bounding box from GeoJSON boundary."""
        if isinstance(boundary, dict) and 'coordinates' in boundary:
            coords = boundary['coordinates'][0]  # Polygon exterior ring
            lons = [c[0] for c in coords]
            lats = [c[1] for c in coords]
            return (min(lons), min(lats), max(lons), max(lats))
        raise ValueError("Invalid boundary format")
    
    def _download_imagery(
        self,
        client,
        region: MonitoringRegion,
        bbox: tuple,
        start_date: str,
        end_date: str
    ) -> int:
        """Download imagery for a region."""
        count = 0
        
        try:
            # Query available imagery
            results = client.query_imagery(bbox, start_date, end_date)
            
            if not results:
                self.stdout.write("  ⚠ No imagery available")
                return 0
            
            for result in results[:5]:  # Limit to 5 images per run
                # Check if already downloaded
                existing = SatelliteImage.objects.filter(
                    image_id=result['id'],
                    source='sentinel-2'
                ).exists()
                
                if existing:
                    self.stdout.write(f"  ℹ {result['id']} already downloaded")
                    continue
                
                # Download image
                filename = f"sentinel_{result['id']}_{result['acquired'][:10]}.tif"
                save_path = f"data/raw/{filename}"
                
                if client.download_imagery(bbox, start_date, end_date, save_path):
                    # Store metadata in database
                    try:
                        satellite_image = SatelliteImage.objects.create(
                            image_id=result['id'],
                            source='sentinel-2',
                            acquisition_date=result['acquired'][:10],
                            cloud_coverage=result['cloud_cover'],
                            resolution=10,
                            processed=False,
                            image_path=save_path,
                            center_point={
                                "type": "Point",
                                "coordinates": [
                                    (bbox[0] + bbox[2]) / 2,
                                    (bbox[1] + bbox[3]) / 2
                                ]
                            },
                            bounds=result['geometry']
                        )
                        count += 1
                        self.stdout.write(f"  ✓ Saved: {satellite_image.image_id}")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"  ✗ DB error: {e}"))
        
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ✗ Download error: {e}"))
        
        return count
    
    def _run_detection(self, region: MonitoringRegion) -> int:
        """Run oil spill detection on recently downloaded images."""
        count = 0
        
        # Get unprocessed images for this region (within 24 hours)
        cutoff = timezone.now() - timedelta(hours=24)
        images = SatelliteImage.objects.filter(
            source='sentinel-2',
            processed=False,
            center_point__isnull=False,
            created_at__gte=cutoff
        )[:10]  # Limit batch size
        
        for image in images:
            try:
                if not os.path.exists(image.image_path):
                    self.stdout.write(f"    ⚠ Image file not found: {image.image_path}")
                    continue
                
                # Run detection
                result = predict_oil_spill(image.image_path)
                
                if result['has_oil_spill']:
                    # Create detection record
                    detection = OilSpillDetection.objects.create(
                        satellite_image=image,
                        confidence_score=result['confidence'],
                        location={
                            "type": "Point",
                            "coordinates": image.center_point.get('coordinates', [0, 0])
                        },
                        area_size=0,  # Would need GIS calculation
                        severity='high' if result['confidence'] > 0.8 else 'medium'
                    )
                    
                    # Create alert
                    Alert.objects.create(
                        detection=detection,
                        message=f"Oil spill detected with {result['confidence']*100:.1f}% confidence",
                        sent=False
                    )
                    
                    count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"    🔴 OIL SPILL DETECTED: {image.image_id} "
                            f"({result['confidence']*100:.1f}% confidence)"
                        )
                    )
                else:
                    self.stdout.write(f"    ✓ {image.image_id} - No spill detected")
                
                # Mark as processed
                image.processed = True
                image.save()
            
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"    ✗ Detection error: {e}"))
        
        return count
