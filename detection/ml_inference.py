"""Django view to process satellite images with ML model"""

import pickle
import json
import numpy as np
from pathlib import Path
from PIL import Image
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from django.core.files.base import ContentFile

# Load the trained model once when Django starts
MODEL_PATH = Path(__file__).parent.parent / 'ml_models/saved_models/oil_spill_detector.pkl'
PREDICTOR = None

def get_predictor():
    """Lazy load the predictor"""
    global PREDICTOR
    if PREDICTOR is None and MODEL_PATH.exists():
        with open(MODEL_PATH, 'rb') as f:
            PREDICTOR = pickle.load(f)
    return PREDICTOR

def predict_oil_spill(image_path, img_size=(256, 256)):
    """Use trained model to predict if image has oil spill
    
    Returns:
        {
            'has_oil_spill': bool,
            'probability': float,
            'confidence': float
        }
    """
    predictor = get_predictor()
    if predictor is None:
        return None
    
    try:
        # Load and preprocess image
        img = Image.open(image_path).convert('RGB')
        img = img.resize(img_size)
        img_array = np.array(img, dtype=np.float32).flatten()
        img_array = img_array / 255.0  # Normalize
        
        # Make prediction
        probability = predictor.predict_proba([img_array])[0, 1]
        prediction = predictor.predict([img_array])[0]
        
        return {
            'has_oil_spill': bool(prediction == 1),
            'probability': float(probability),
            'confidence': float(max(probability, 1 - probability))
        }
    except Exception as e:
        print(f"Prediction error: {e}")
        return None

# Add this method to SatelliteImageViewSet in detection/views.py
def process_satellite_image_action(self, request, pk=None):
    """
    Process a satellite image with ML model to detect oil spills
    
    POST /api/satellite-images/{id}/process/
    Returns: Created OilSpillDetection if spill detected, or empty response
    """
    from .models import SatelliteImage, OilSpillDetection
    
    try:
        satellite_image = self.get_object()
        
        # Get image file path
        if not satellite_image.image_path:
            return Response(
                {'error': 'No image file associated'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Make prediction
        image_path = satellite_image.image_path
        if isinstance(image_path, str):
            image_path = Path(image_path)
        
        result = predict_oil_spill(str(image_path))
        
        if result is None:
            return Response(
                {'error': 'Model not loaded or prediction failed'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        # Return prediction result
        response_data = {
            'satellite_image_id': satellite_image.id,
            'has_oil_spill': result['has_oil_spill'],
            'confidence': result['confidence'],
            'probability': result['probability']
        }
        
        # If oil spill detected, create OilSpillDetection record
        if result['has_oil_spill'] and result['confidence'] > 0.5:
            detection = OilSpillDetection.objects.create(
                satellite_image=satellite_image,
                confidence_score=result['probability'],
                location=satellite_image.center_point,
                area_size=100.0,  # Placeholder
                severity='HIGH' if result['probability'] > 0.7 else 'MEDIUM'
            )
            response_data['created_detection_id'] = detection.id
            response_data['status'] = 'detection_created'
        else:
            response_data['status'] = 'no_spill_detected'
        
        return Response(response_data, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
