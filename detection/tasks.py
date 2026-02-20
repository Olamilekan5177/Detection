from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
import numpy as np
import os
from io import BytesIO
from PIL import Image
import logging

from .models import SatelliteImage, OilSpillDetection, Alert, MonitoringRegion
from ml_models.preprocessing import ImagePreprocessor
from ml_models.model_architecture import OilSpillDetector

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3)
def process_satellite_image(self, image_id):
    """
    Process a satellite image to detect oil spills
    
    Args:
        image_id: ID of SatelliteImage to process
    """
    try:
        # Get the image
        image = SatelliteImage.objects.get(id=image_id)
        
        if image.processed:
            logger.info(f"Image {image.image_id} already processed")
            return {'status': 'already_processed', 'image_id': image_id}
        
        logger.info(f"Starting processing for image {image.image_id}")
        
        # Load preprocessor
        preprocessor = ImagePreprocessor(target_size=(256, 256))
        
        # Preprocess image
        if image.image_path:
            preprocessed = preprocessor.preprocess(
                str(image.image_path.path),
                is_satellite=True
            )
        else:
            raise ValueError(f"No image path for {image.image_id}")
        
        # Load and run model
        detector = OilSpillDetector()
        detector.build(model_type='transfer')
        model_path = 'ml_models/saved_models/oil_spill_detector.h5'
        
        if os.path.exists(model_path):
            detector.model.load_weights(model_path)
        else:
            logger.warning(f"Model not found at {model_path}, using untrained model")
        
        # Predict
        img_input = np.expand_dims(preprocessed, axis=0)
        prediction = detector.model.predict(img_input, verbose=0)
        confidence = float(prediction[0][0])
        
        # Generate detection if confidence is high enough
        threshold = 0.5
        if confidence > threshold:
            # Default location as GeoJSON
            location = image.center_point or {'type': 'Point', 'coordinates': [0, 0]}
            
            # Estimate area (this is simplified - in production would use segmentation)
            area_size = float(np.random.uniform(0.5, 50.0))  # Mock: 0.5-50 km²
            
            # Determine severity based on confidence
            if confidence > 0.9:
                severity = 'CRITICAL'
            elif confidence > 0.8:
                severity = 'HIGH'
            elif confidence > 0.7:
                severity = 'MEDIUM'
            else:
                severity = 'LOW'
            
            detection = OilSpillDetection.objects.create(
                satellite_image=image,
                confidence_score=confidence,
                location=location,
                area_size=area_size,
                severity=severity
            )
            
            logger.info(f"Created detection {detection.id} with confidence {confidence}")
            
            # Create alert
            alert = Alert.objects.create(
                detection=detection,
                message=f"Oil spill detected with confidence {confidence:.2%}",
                recipients=['admin@example.com']  # Configure in settings
            )
            
            logger.info(f"Created alert {alert.id}")
        else:
            logger.info(f"Confidence {confidence} below threshold {threshold}")
        
        # Mark as processed
        image.processed = True
        image.processing_date = timezone.now()
        image.save()
        
        return {
            'status': 'success',
            'image_id': image_id,
            'confidence': confidence,
            'detected': confidence > threshold
        }
    
    except SatelliteImage.DoesNotExist:
        logger.error(f"SatelliteImage {image_id} not found")
        return {'status': 'error', 'message': 'Image not found'}
    
    except Exception as exc:
        logger.error(f"Error processing image {image_id}: {str(exc)}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def check_monitoring_region(region_id):
    """
    Check a monitoring region for recent detections and send alerts
    
    Args:
        region_id: ID of MonitoringRegion to check
    """
    try:
        region = MonitoringRegion.objects.get(id=region_id)
        
        logger.info(f"Checking monitoring region {region.name}")
        
        # Get recent unverified detections in region
        # For SQLite, filtering happens in Python (in production, use PostGIS)
        detections = OilSpillDetection.objects.filter(
            verified=False,
            confidence_score__gte=region.alert_threshold
        ).order_by('-detection_date')[:10]
        
        # Filter by boundary if needed (simplified for SQLite)
        if isinstance(region.boundary, dict) and 'coordinates' in region.boundary:
            coords = region.boundary.get('coordinates', [[[[0, 0]]]])
            if coords and coords[0]:
                lons = [c[0] for ring in coords for c in ring]
                lats = [c[1] for ring in coords for c in ring]
                min_lon, max_lon = min(lons), max(lons)
                min_lat, max_lat = min(lats), max(lats)
                
                filtered_detections = []
                for d in detections:
                    if isinstance(d.location, dict) and 'coordinates' in d.location:
                        lon, lat = d.location['coordinates']
                        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
                            filtered_detections.append(d)
                detections = filtered_detections
        
        alert_count = 0
        for detection in detections:
            # Check if alert already exists
            if not hasattr(detection, 'alert'):
                Alert.objects.create(
                    detection=detection,
                    message=f"Detection in {region.name}",
                    recipients=[]  # Configure on model
                )
                alert_count += 1
        
        # Update last checked
        region.last_checked = timezone.now()
        region.save()
        
        logger.info(f"Created {alert_count} new alerts for region {region.name}")
        
        return {
            'status': 'success',
            'region_id': region_id,
            'detections_found': len(detections),
            'alerts_created': alert_count
        }
    
    except MonitoringRegion.DoesNotExist:
        logger.error(f"MonitoringRegion {region_id} not found")
        return {'status': 'error', 'message': 'Region not found'}
    
    except Exception as exc:
        logger.error(f"Error checking region {region_id}: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task
def batch_process_satellite_images(source='SENTINEL', hours=24):
    """
    Batch process unprocessed satellite images
    
    Args:
        source: Image source filter
        hours: Process images from last N hours
    """
    from datetime import timedelta
    
    try:
        start_time = timezone.now() - timedelta(hours=hours)
        
        # Get unprocessed images
        images = SatelliteImage.objects.filter(
            source=source,
            processed=False,
            upload_date__gte=start_time
        )
        
        task_ids = []
        for image in images:
            task = process_satellite_image.delay(image.id)
            task_ids.append(task.id)
        
        logger.info(f"Queued {len(task_ids)} images for processing")
        
        return {
            'status': 'queued',
            'task_ids': task_ids,
            'count': len(task_ids)
        }
    
    except Exception as exc:
        logger.error(f"Error in batch processing: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task
def send_alerts():
    """
    Send pending alerts via email
    """
    try:
        # Get unsent alerts
        pending_alerts = Alert.objects.filter(sent=False)
        
        sent_count = 0
        for alert in pending_alerts:
            try:
                # Mock email sending - implement with actual email backend
                logger.info(f"Sending alert {alert.id} to {alert.recipients}")
                
                # In production: use send_mail or async email task
                # send_mail(
                #     f"Oil Spill Alert",
                #     alert.message,
                #     'noreply@oilspill.com',
                #     alert.recipients,
                #     fail_silently=False,
                # )
                
                alert.sent = True
                alert.sent_at = timezone.now()
                alert.save()
                sent_count += 1
            
            except Exception as e:
                logger.error(f"Failed to send alert {alert.id}: {str(e)}")
        
        logger.info(f"Sent {sent_count} alerts")
        
        return {
            'status': 'success',
            'alerts_sent': sent_count
        }
    
    except Exception as exc:
        logger.error(f"Error sending alerts: {str(exc)}", exc_info=True)
        return {'status': 'error', 'message': str(exc)}


@shared_task(bind=True, max_retries=3)
def process_real_satellite_data(self, region_id=None):
    """
    Process real satellite data and create detections
    
    This task:
    1. Downloads real satellite imagery from NOAA/Sentinel
    2. Runs trained ML model for detection
    3. Creates OilSpillDetection records
    4. Triggers alerts for new detections
    
    Args:
        region_id: Optional MonitoringRegion ID to process
    
    Returns:
        dict with processing results
    """
    try:
        logger.info("Starting real satellite data processing pipeline")
        
        # Import here to avoid circular imports
        import sys
        from pathlib import Path
        scripts_dir = Path(__file__).parent.parent.parent / 'scripts'
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        
        from process_real_satellite_data import RealSatelliteDataProcessor
        
        # Create processor
        processor = RealSatelliteDataProcessor()
        
        # Process region
        processor.process_region(
            region_id=region_id,
            days_back=7
        )
        
        logger.info("Real satellite data processing completed successfully")
        
        return {
            'status': 'success',
            'message': 'Real satellite data processed'
        }
        
    except Exception as exc:
        logger.error(f"Error processing real satellite data: {str(exc)}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries), max_retries=3)
