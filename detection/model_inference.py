"""
Model Inference Engine

Loads pretrained sklearn model and makes predictions on feature vectors.

Implements Step 7 and Step 8 of the oil spill detection pipeline.
"""

import logging
import numpy as np
import joblib
from typing import Dict, List, Tuple, Optional
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """Result of a single patch prediction"""
    patch_id: int
    predicted_class: int  # 0 = no spill, 1 = oil spill
    confidence: float  # Confidence score (0-1)
    prediction_time: float  # Inference time in ms
    
    def is_oil_spill(self) -> bool:
        """Check if prediction is positive for oil spill"""
        return self.predicted_class == 1
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "patch_id": self.patch_id,
            "predicted_class": self.predicted_class,
            "confidence": self.confidence,
            "prediction_time": self.prediction_time,
            "is_oil_spill": self.is_oil_spill()
        }


class SklearnModelInference:
    """
    Load and use pretrained sklearn models for inference.
    
    Supports various sklearn estimators:
    - RandomForestClassifier
    - SVC
    - LogisticRegression
    - GradientBoostingClassifier
    - etc.
    """
    
    def __init__(self, model_path: str):
        """
        Load pretrained model.
        
        Args:
            model_path: Path to saved sklearn model (joblib format)
        """
        self.model_path = Path(model_path)
        
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model not found at {model_path}")
        
        # Load model
        self.model = joblib.load(self.model_path)
        
        # Load metadata if available
        metadata_path = self.model_path.with_suffix('.json')
        self.metadata = {}
        
        if metadata_path.exists():
            import json
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
        
        logger.info(f"✓ Model loaded from {model_path}")
        logger.info(f"  Model type: {type(self.model).__name__}")
        
        if self.metadata:
            logger.info(f"  Accuracy: {self.metadata.get('accuracy', 'N/A')}")
            logger.info(f"  F1-score: {self.metadata.get('f1_score', 'N/A')}")
    
    def _get_prediction_confidence(
        self,
        prediction: int,
        predict_proba_result: Optional[np.ndarray] = None
    ) -> float:
        """
        Extract confidence score from model output.
        
        Args:
            prediction: Class prediction (0 or 1)
            predict_proba_result: Output from predict_proba() if available
        
        Returns:
            Confidence score (0-1)
        """
        if predict_proba_result is not None:
            # Use probability for predicted class
            if len(predict_proba_result.shape) == 1:
                confidence = float(predict_proba_result[prediction])
            else:
                confidence = float(predict_proba_result[0, prediction])
        else:
            # If no probabilities, confidence is 0.5-1.0
            # (model made prediction, but no confidence available)
            confidence = 0.5 if prediction == 0 else 0.75
        
        return max(0.0, min(1.0, float(confidence)))  # Clamp to [0, 1]
    
    def predict_single(self, features: np.ndarray) -> PredictionResult:
        """
        Make prediction on a single feature vector.
        
        Args:
            features: 1D feature vector
        
        Returns:
            PredictionResult
        """
        import time
        
        start_time = time.time()
        
        # Ensure 2D input
        if features.ndim == 1:
            features = features.reshape(1, -1)
        
        # Make prediction
        prediction = self.model.predict(features)[0]
        
        # Get confidence if available
        confidence = 0.5
        try:
            proba = self.model.predict_proba(features)[0]
            confidence = self._get_prediction_confidence(prediction, proba)
        except AttributeError:
            pass  # Model doesn't have predict_proba
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return PredictionResult(
            patch_id=0,
            predicted_class=int(prediction),
            confidence=confidence,
            prediction_time=elapsed_ms
        )
    
    def predict_batch(
        self,
        feature_matrix: np.ndarray,
        patch_ids: Optional[List[int]] = None
    ) -> Tuple[List[PredictionResult], float]:
        """
        Make predictions on multiple feature vectors.
        
        Implements Step 8 of the pipeline.
        
        Args:
            feature_matrix: (num_patches, num_features) array
            patch_ids: Optional list of patch IDs
        
        Returns:
            Tuple of (predictions, total_time)
        """
        import time
        
        logger.info("="*60)
        logger.info("MODEL INFERENCE")
        logger.info("="*60)
        
        start_time = time.time()
        
        if patch_ids is None:
            patch_ids = list(range(feature_matrix.shape[0]))
        
        # Make predictions
        predictions = self.model.predict(feature_matrix)
        
        # Get confidence scores if available
        confidences = np.zeros(len(predictions))
        try:
            probas = self.model.predict_proba(feature_matrix)
            for i, pred in enumerate(predictions):
                confidences[i] = self._get_prediction_confidence(pred, probas[i])
        except AttributeError:
            pass  # Model doesn't have predict_proba
        
        total_time = (time.time() - start_time) * 1000
        
        # Create result objects
        results = []
        for i, (patch_id, pred, conf) in enumerate(zip(patch_ids, predictions, confidences)):
            result = PredictionResult(
                patch_id=patch_id,
                predicted_class=int(pred),
                confidence=float(conf),
                prediction_time=total_time / len(predictions)
            )
            results.append(result)
        
        logger.info(f"✓ Inference complete on {len(predictions)} patches")
        logger.info(f"  Oil spills detected: {sum(1 for r in results if r.is_oil_spill())}")
        logger.info(f"  Total inference time: {total_time:.2f}ms")
        logger.info(f"  Average time per patch: {total_time/len(predictions):.2f}ms")
        
        return results, total_time


class EnsembleModelInference:
    """
    Use ensemble of multiple models for more robust predictions.
    
    Useful for combining predictions from multiple model architectures.
    """
    
    def __init__(self, model_paths: List[str]):
        """
        Initialize ensemble of models.
        
        Args:
            model_paths: List of paths to model files
        """
        self.models = []
        
        for path in model_paths:
            try:
                model = joblib.load(path)
                self.models.append((path, model))
                logger.info(f"✓ Loaded model from {path}")
            except Exception as e:
                logger.error(f"Failed to load model from {path}: {e}")
        
        logger.info(f"✓ Ensemble initialized with {len(self.models)} models")
    
    def predict_ensemble(
        self,
        feature_matrix: np.ndarray,
        method: str = "voting",
        patch_ids: Optional[List[int]] = None
    ) -> List[PredictionResult]:
        """
        Make predictions using ensemble.
        
        Args:
            feature_matrix: (num_patches, num_features) array
            method: "voting" (majority vote) or "averaging" (average probability)
            patch_ids: Optional list of patch IDs
        
        Returns:
            List of prediction results
        """
        if not self.models:
            raise ValueError("No models in ensemble")
        
        logger.info(f"Running ensemble prediction ({method})")
        
        if patch_ids is None:
            patch_ids = list(range(feature_matrix.shape[0]))
        
        results = []
        
        for patch_idx in range(feature_matrix.shape[0]):
            features = feature_matrix[patch_idx:patch_idx+1]
            
            if method == "voting":
                # Majority voting
                votes = []
                confidences = []
                
                for path, model in self.models:
                    pred = model.predict(features)[0]
                    votes.append(pred)
                    
                    try:
                        conf = model.predict_proba(features)[0, pred]
                    except:
                        conf = 0.5
                    confidences.append(conf)
                
                final_pred = 1 if sum(votes) > len(votes) / 2 else 0
                final_conf = np.mean(confidences)
            
            elif method == "averaging":
                # Average probabilities
                probs_oil = []
                
                for path, model in self.models:
                    try:
                        proba = model.predict_proba(features)[0]
                        probs_oil.append(proba[1] if len(proba) > 1 else 0.5)
                    except:
                        probs_oil.append(0.5)
                
                final_conf = np.mean(probs_oil)
                final_pred = 1 if final_conf > 0.5 else 0
            
            else:
                raise ValueError(f"Unknown method: {method}")
            
            result = PredictionResult(
                patch_id=patch_ids[patch_idx],
                predicted_class=final_pred,
                confidence=final_conf,
                prediction_time=0.0
            )
            results.append(result)
        
        logger.info(f"✓ Ensemble predictions complete")
        return results


def create_inference_engine(
    model_path: str,
    model_type: str = "single"
) -> SklearnModelInference:
    """
    Factory function to create inference engine.
    
    Args:
        model_path: Path to model file
        model_type: "single" or "ensemble"
    
    Returns:
        Inference engine
    """
    if model_type == "single":
        return SklearnModelInference(model_path)
    else:
        raise ValueError(f"Unknown model type: {model_type}")
