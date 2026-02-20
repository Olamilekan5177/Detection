import os
import sys
import numpy as np
from pathlib import Path
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.utils import class_weight

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from ml_models.model_architecture import OilSpillDetector
from ml_models.preprocessing import ImagePreprocessor
from ml_models.data_loader import DatasetLoader

def plot_training_history(history, save_path='training_history.png'):
    """Plot training metrics"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    
    # Accuracy
    axes[0, 0].plot(history.history['accuracy'], label='Train')
    axes[0, 0].plot(history.history['val_accuracy'], label='Validation')
    axes[0, 0].set_title('Model Accuracy')
    axes[0, 0].set_xlabel('Epoch')
    axes[0, 0].set_ylabel('Accuracy')
    axes[0, 0].legend()
    
    # Loss
    axes[0, 1].plot(history.history['loss'], label='Train')
    axes[0, 1].plot(history.history['val_loss'], label='Validation')
    axes[0, 1].set_title('Model Loss')
    axes[0, 1].set_xlabel('Epoch')
    axes[0, 1].set_ylabel('Loss')
    axes[0, 1].legend()
    
    # Precision
    axes[1, 0].plot(history.history['precision'], label='Train')
    axes[1, 0].plot(history.history['val_precision'], label='Validation')
    axes[1, 0].set_title('Precision')
    axes[1, 0].set_xlabel('Epoch')
    axes[1, 0].set_ylabel('Precision')
    axes[1, 0].legend()
    
    # Recall
    axes[1, 1].plot(history.history['recall'], label='Train')
    axes[1, 1].plot(history.history['val_recall'], label='Validation')
    axes[1, 1].set_title('Recall')
    axes[1, 1].set_xlabel('Epoch')
    axes[1, 1].set_ylabel('Recall')
    axes[1, 1].legend()
    
    plt.tight_layout()
    plt.savefig(save_path)
    print(f"Training history saved to {save_path}")

def train_model():
    """Main training function"""
    
    # Configuration
    DATA_DIR = PROJECT_ROOT / 'data/training'
    MODEL_SAVE_PATH = PROJECT_ROOT / 'ml_models/saved_models/oil_spill_detector.h5'
    BATCH_SIZE = 32
    EPOCHS = 50
    IMG_SIZE = (256, 256)
    
    print("=" * 50)
    print("OIL SPILL DETECTION MODEL TRAINING")
    print("=" * 50)
    
    # 1. Load dataset
    print("\n[1/6] Loading dataset...")
    loader = DatasetLoader(DATA_DIR, img_size=IMG_SIZE)
    X, y = loader.load_dataset()
    print(f"Dataset loaded: {len(X)} images")
    print(f"Oil spills: {np.sum(y)}, No spills: {len(y) - np.sum(y)}")
    
    # 2. Split dataset
    print("\n[2/6] Splitting dataset...")
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, random_state=42, stratify=y
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, random_state=42, stratify=y_temp
    )
    
    print(f"Train: {len(X_train)} | Val: {len(X_val)} | Test: {len(X_test)}")
    
    # 3. Handle class imbalance
    print("\n[3/6] Computing class weights...")
    class_weights = class_weight.compute_class_weight(
        'balanced',
        classes=np.unique(y_train),
        y=y_train
    )
    class_weight_dict = {i: weight for i, weight in enumerate(class_weights)}
    print(f"Class weights: {class_weight_dict}")
    
    # 4. Build model
    print("\n[4/6] Building model...")
    detector = OilSpillDetector(input_shape=(*IMG_SIZE, 3))
    model = detector.build(model_type='transfer')  # or 'custom'
    detector.compile_model(learning_rate=0.001)
    
    print(model.summary())
    
    # 5. Train model
    print("\n[5/6] Training model...")
    
    # Data augmentation
    preprocessor = ImagePreprocessor(target_size=IMG_SIZE)
    train_datagen = preprocessor.get_data_augmentation()
    
    # Fit augmentation on training data
    train_generator = train_datagen.flow(
        X_train, y_train,
        batch_size=BATCH_SIZE
    )
    
    # Callbacks
    callbacks = detector.get_callbacks(str(MODEL_SAVE_PATH))
    
    # Train
    history = model.fit(
        train_generator,
        epochs=EPOCHS,
        validation_data
        =(X_val, y_val),
        class_weight=class_weight_dict,
        callbacks=callbacks,
        verbose=1
        )
        # 6. Evaluate
print("\n[6/6] Evaluating model...")
test_loss, test_acc, test_precision, test_recall, test_auc = model.evaluate(
    X_test, y_test, verbose=0
)

print(f"\nTest Results:")
print(f"  Accuracy:  {test_acc:.4f}")
print(f"  Precision: {test_precision:.4f}")
print(f"  Recall:    {test_recall:.4f}")
print(f"  AUC:       {test_auc:.4f}")

# Plot training history
plot_training_history(history, 'training_history.png')

print(f"\n✓ Model saved to: {MODEL_SAVE_PATH}")
print("=" * 50)

if __name__ == "__main__":
    train_model()

---

### **STEP 7: Inference/Prediction Module**

**File: `ml_models/predict.py`**

**Why**: Handles real-time prediction on new satellite images.
```python
import numpy as np
import cv2
from tensorflow import keras
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

from ml_models.preprocessing import ImagePreprocessor

class OilSpillPredictor:
    """Make predictions on new satellite images"""
    
    def __init__(self, model_path):
        self.model = keras.models.load_model(model_path)
        self.preprocessor = ImagePreprocessor(target_size=(256, 256))
        print(f"Model loaded from {model_path}")
    
    def predict_single(self, image_path):
        """Predict on a single image
        
        Returns:
            dict: {
                'has_oil_spill': bool,
                'confidence': float,
                'probability': float
            }
        """
        # Preprocess image
        image = self.preprocessor.preprocess(image_path)
        
        # Add batch dimension
        image_batch = np.expand_dims(image, axis=0)
        
        # Predict
        probability = self.model.predict(image_batch, verbose=0)[0][0]
        
        # Threshold at 0.5
        has_oil_spill = probability >= 0.5
        confidence = probability if has_oil_spill else (1 - probability)
        
        return {
            'has_oil_spill': bool(has_oil_spill),
            'confidence': float(confidence),
            'probability': float(probability)
        }
    
    def predict_batch(self, image_paths):
        """Predict on multiple images"""
        results = []
        for img_path in image_paths:
            result = self.predict_single(img_path)
            result['image_path'] = str(img_path)
            results.append(result)
        
        return results
    
    def predict_with_heatmap(self, image_path, save_path=None):
        """Generate prediction with attention heatmap
        
        Why: Shows which parts of image influenced the decision
        Uses: Grad-CAM technique
        """
        import tensorflow as tf
        
        # Preprocess
        image = self.preprocessor.preprocess(image_path)
        image_batch = np.expand_dims(image, axis=0)
        
        # Get the last convolutional layer
        last_conv_layer = None
        for layer in reversed(self.model.layers):
            if 'conv' in layer.name.lower():
                last_conv_layer = layer
                break
        
        if last_conv_layer is None:
            print("No convolutional layer found")
            return self.predict_single(image_path)
        
        # Create gradient model
        grad_model = keras.models.Model(
            inputs=self.model.input,
            outputs=[last_conv_layer.output, self.model.output]
        )
        
        # Compute gradients
        with tf.GradientTape() as tape:
            conv_output, predictions = grad_model(image_batch)
            loss = predictions[0]
        
        # Get gradients
        grads = tape.gradient(loss, conv_output)
        pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))
        
        # Weight the channels
        conv_output = conv_output[0]
        heatmap = conv_output @ pooled_grads[..., tf.newaxis]
        heatmap = tf.squeeze(heatmap)
        
        # Normalize heatmap
        heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)
        heatmap = heatmap.numpy()
        
        # Resize heatmap to image size
        heatmap = cv2.resize(heatmap, (256, 256))
        heatmap = np.uint8(255 * heatmap)
        heatmap = cv2.applyColorMap(heatmap, cv2.COLORMAP_JET)
        
        # Superimpose heatmap on image
        original_image = cv2.imread(image_path)
        original_image = cv2.resize(original_image, (256, 256))
        superimposed = cv2.addWeighted(original_image, 0.6, heatmap, 0.4, 0)
        
        if save_path:
            cv2.imwrite(save_path, superimposed)
        
        # Get prediction
        result = self.predict_single(image_path)
        result['heatmap_path'] = save_path
        
        return result
```

---

### **STEP 8: Celery Tasks for Async Processing**

**File: `config/celery.py`**

**Why**: Celery handles long-running tasks (image processing, ML inference) asynchronously without blocking the web server.
```python
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('oil_spill_detection')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Periodic tasks
app.conf.beat_schedule = {
    'check-monitoring-regions-every-6-hours': {
        'task': 'apps.detection.tasks.check_all_monitoring_regions',
        'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
    },
    'cleanup-old-images-daily': {
        'task': 'apps.detection.tasks.cleanup_old_images',
        'schedule': crontab(minute=0, hour=3),  # 3 AM daily
    },
}
```

**File: `apps/detection/tasks.py`**
```python
from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from pathlib import Path
import numpy as np
import cv2

from .models import SatelliteImage, OilSpillDetection, Alert, MonitoringRegion
from ml_models.predict import OilSpillPredictor
from ml_models.preprocessing import ImagePreprocessor

# Initialize predictor (loaded once)
MODEL_PATH = Path(__file__).parent.parent.parent / 'ml_models/saved_models/oil_spill_detector.h5'
predictor = None

def get_predictor():
    global predictor
    if predictor is None:
        predictor = OilSpillPredictor(str(MODEL_PATH))
    return predictor

@shared_task
def process_satellite_image(image_id):
    """Process a single satellite image for oil spill detection
    
    Why: Long-running ML inference shouldn't block web requests
    """
    try:
        # Get image
        sat_image = SatelliteImage.objects.get(id=image_id)
        
        print(f"Processing image: {sat_image.image_id}")
        
        # Get predictor
        pred = get_predictor()
        
        # Make prediction
        result = pred.predict_single(sat_image.image_path)
        
        # If oil spill detected
        if result['has_oil_spill'] and result['confidence'] > 0.7:
            print(f"Oil spill detected with confidence: {result['confidence']}")
            
            # Generate heatmap
            heatmap_path = f"media/heatmaps/{sat_image.image_id}_heatmap.jpg"
            pred.predict_with_heatmap(sat_image.image_path, heatmap_path)
            
            # Create detection record
            detection = OilSpillDetection.objects.create(
                satellite_image=sat_image,
                confidence_score=result['confidence'],
                location=sat_image.center_point,
                affected_area=sat_image.bounds,  # Simplified - would need refinement
                area_size=calculate_area(sat_image.bounds),
                cropped_image_path=sat_image.image_path,
                heatmap_path=heatmap_path
            )
            
            # Create alert
            create_alert_for_detection(detection.id)
            
            print(f"Detection created: {detection.id}")
        
        # Mark as processed
        sat_image.processed = True
        sat_image.save()
        
        return {
            'status': 'success',
            'image_id': image_id,
            'has_oil_spill': result['has_oil_spill'],
            'confidence': result['confidence']
        }
        
    except Exception as e:
        print(f"Error processing image {image_id}: {str(e)}")
        return {'status': 'error', 'message': str(e)}

@shared_task
def create_alert_for_detection(detection_id):
    """Create and send alert for new detection"""
    try:
        detection = OilSpillDetection.objects.get(id=detection_id)
        
        message = (
            f"Oil Spill Detected!\n"
            f"Severity: {detection.severity}\n"
            f"Confidence: {detection.confidence_score:.2%}\n"
            f"Area: {detection.area_size:.2f} km²\n"
            f"Location: {detection.location.coords}"
        )
        
        alert = Alert.objects.create(
            detection=detection,
            message=message,
            recipients=['admin@example.com']  # Configure as needed
        )
        
        # Here you would integrate email/SMS sending
        # For now, just mark as sent
        alert.sent = True
        alert.sent_at = timezone.now()
        alert.save()
        
        return {'status': 'success', 'alert_id': alert.id}
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

@shared_task
def check_all_monitoring_regions():
    """Periodic task to check all active monitoring regions"""
    regions = MonitoringRegion.objects.filter(active=True)
    
    results = []
    for region in regions:
        # Check if it's time to check this region
        if should_check_region(region):
            result = check_monitoring_region.delay(region.id)
            results.append(result.id)
            
            # Update last checked
            region.last_checked = timezone.now()
            region.save()
    
    return {'regions_checked': len(results), 'task_ids': results}

@shared_task
def check_monitoring_region(region_id):
    """Download and process new images for a monitoring region
    
    Why: Automated monitoring without manual intervention
    """
    try:
        region = MonitoringRegion.objects.get(id=region_id)
        
        # Download new satellite images for this region
        # This would use Sentinel API (simplified here)
        new_images = download_sentinel_images_for_region(region)
        
        # Process each new image
        task_ids = []
        for img in new_images:
            task_id = process_satellite_image.delay(img.id)
            task_ids.append(task_id)
        
        return {
            'status': 'success',
            'region_id': region_id,
            'images_processed': len(task_ids)
        }
        
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def calculate_area(polygon):
    """Calculate area of polygon in km²"""
    # Simplified - use proper geodesic calculations in production
    return polygon.area * 111 * 111  # Rough conversion

def should_check_region(region):
    """Check if region is due for monitoring"""
    if not region.last_checked:
        return True
    
    time_since_check = timezone.now() - region.last_checked
    return time_since_check.total_seconds() >= (region.check_interval * 3600)

def download_sentinel_images_for_region(region):
    """Download Sentinel images for a region
    
    This is a placeholder - actual implementation would use:
    - sentinelsat library
    - Copernicus Open Access Hub API
    - Sentinel Hub API
    """
    # Placeholder
    return []