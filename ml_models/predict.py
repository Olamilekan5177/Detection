#!/usr/bin/env python
"""Use the trained model to predict oil spills in new images"""

import pickle
import numpy as np
from pathlib import Path
from PIL import Image
import json

class OilSpillPredictor:
    """Load trained model and make predictions"""
    
    def __init__(self, model_path):
        """Load saved model"""
        self.model_path = Path(model_path)
        
        # Load model
        with open(self.model_path, 'rb') as f:
            self.model = pickle.load(f)
        
        # Load metadata
        metadata_path = self.model_path.with_suffix('.json')
        with open(metadata_path, 'r') as f:
            self.metadata = json.load(f)
        
        self.img_size = tuple(self.metadata['img_size'])
        print(f"✓ Model loaded from {model_path}")
        print(f"  Accuracy: {self.metadata['accuracy']:.2%}")
    
    def predict_image(self, image_path):
        """Predict if image contains oil spill
        
        Returns:
            {
                'has_oil_spill': bool,
                'confidence': float (0-1),
                'probability': float (0-1)
            }
        """
        # Load and preprocess image
        img = Image.open(image_path).convert('RGB')
        img = img.resize(self.img_size)
        img_array = np.array(img, dtype=np.float32).flatten()
        img_array = img_array / 255.0  # Normalize
        
        # Make prediction
        probability = self.model.predict_proba([img_array])[0, 1]
        prediction = self.model.predict([img_array])[0]
        
        has_oil_spill = bool(prediction == 1)
        
        return {
            'has_oil_spill': has_oil_spill,
            'probability': float(probability),
            'confidence': float(max(probability, 1 - probability))
        }
    
    def predict_batch(self, image_paths):
        """Predict on multiple images"""
        results = []
        for img_path in image_paths:
            result = self.predict_image(img_path)
            result['image_path'] = str(img_path)
            results.append(result)
        return results

if __name__ == '__main__':
    # Example usage
    model_path = Path.cwd() / 'ml_models/saved_models/oil_spill_detector.pkl'
    
    if model_path.exists():
        predictor = OilSpillPredictor(model_path)
        
        # Test on a few images
        test_images = list((Path.cwd() / 'data/training/oil_spill').glob('*.tif'))[:3]
        
        if test_images:
            print("\nTesting predictions on oil spill images...")
            for img_path in test_images:
                result = predictor.predict_image(img_path)
                print(f"  {img_path.name}: Oil Spill={result['has_oil_spill']}, "
                      f"Confidence={result['confidence']:.2%}")
    else:
        print(f"Model not found at {model_path}")
        print("Run: python train_sklearn_model.py")
