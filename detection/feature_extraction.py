"""
Feature Extraction from SAR Patches

Extracts numerical features from each patch for sklearn model input.
Features include statistical moments and texture descriptors.

Implements Step 6 of the oil spill detection pipeline.
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
from skimage.feature import greycomatrix, greycoprops
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PatchFeatures:
    """Feature vector for a single patch"""
    patch_id: int
    features: np.ndarray  # 1D feature vector
    feature_names: List[str]
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "patch_id": self.patch_id,
            "features": self.features.tolist(),
            "feature_names": self.feature_names
        }
    
    def to_list(self) -> List[float]:
        """Return features as list"""
        return self.features.tolist()


class StatisticalFeatureExtractor:
    """Extract statistical features from patches"""
    
    @staticmethod
    def extract_basic_statistics(patch: np.ndarray) -> Dict[str, float]:
        """
        Extract basic statistical features.
        
        Features:
        - mean: Average pixel value
        - std: Standard deviation
        - min: Minimum pixel value
        - max: Maximum pixel value
        - median: Median pixel value
        - kurtosis: Sharpness of distribution
        - skewness: Asymmetry of distribution
        
        Args:
            patch: 2D patch array
        
        Returns:
            Dictionary of feature names and values
        """
        return {
            "mean": float(np.mean(patch)),
            "std": float(np.std(patch)),
            "min": float(np.min(patch)),
            "max": float(np.max(patch)),
            "median": float(np.median(patch)),
            "kurtosis": float(np.kurtosis(patch.flatten())),
            "skewness": float(np.skew(patch.flatten()))
        }
    
    @staticmethod
    def extract_range_features(patch: np.ndarray) -> Dict[str, float]:
        """
        Extract range-based features.
        
        Features:
        - range: max - min
        - iqr: Interquartile range (Q3 - Q1)
        - cv: Coefficient of variation (std / mean)
        
        Args:
            patch: 2D patch array
        
        Returns:
            Dictionary of feature names and values
        """
        flat = patch.flatten()
        q1, q3 = np.percentile(flat, [25, 75])
        mean = np.mean(patch)
        
        return {
            "range": float(np.max(patch) - np.min(patch)),
            "iqr": float(q3 - q1),
            "cv": float(np.std(patch) / (mean + 1e-8))  # Avoid division by zero
        }
    
    @staticmethod
    def extract_histogram_features(patch: np.ndarray, bins: int = 8) -> Dict[str, float]:
        """
        Extract histogram-based features.
        
        Features:
        - entropy: Information content of histogram
        - energy: Sum of squared histogram bins
        
        Args:
            patch: 2D patch array
            bins: Number of histogram bins
        
        Returns:
            Dictionary of feature names and values
        """
        hist, _ = np.histogram(patch.flatten(), bins=bins, range=(0, 1))
        hist = hist / hist.sum()  # Normalize
        
        # Entropy: -sum(p * log(p))
        entropy = -np.sum(hist * np.log(hist + 1e-10))
        
        # Energy: sum(p^2)
        energy = np.sum(hist ** 2)
        
        return {
            "entropy": float(entropy),
            "energy": float(energy)
        }


class TextureFeatureExtractor:
    """Extract texture features (GLCM) from patches"""
    
    @staticmethod
    def extract_glcm_features(
        patch: np.ndarray,
        distances: List[int] = [1, 2],
        angles: List[float] = [0, np.pi/4, np.pi/2, 3*np.pi/4],
        quantize_levels: int = 8
    ) -> Dict[str, float]:
        """
        Extract Gray Level Co-occurrence Matrix (GLCM) features.
        
        Features:
        - contrast: Local variation in intensity
        - dissimilarity: Average difference between pixels
        - homogeneity: Local homogeneity
        - energy: Angular second moment
        - correlation: Linear dependency on neighbors
        - asm: Angular second moment (same as energy)
        
        GLCM is useful for characterizing texture patterns.
        Oil spills show distinctive texture in SAR images.
        
        Args:
            patch: 2D patch array
            distances: Co-occurrence distances to compute
            angles: Angles to compute
            quantize_levels: Quantization levels for GLCM
        
        Returns:
            Dictionary of feature names and values
        """
        try:
            # Quantize patch to reduce computation
            patch_quantized = (patch * (quantize_levels - 1)).astype(np.uint8)
            
            # Compute GLCM
            glcm = greycomatrix(
                patch_quantized,
                distances=distances,
                angles=angles,
                levels=quantize_levels,
                symmetric=True,
                normed=True
            )
            
            # Extract properties (average over all distances and angles)
            features = {}
            for prop in ['contrast', 'dissimilarity', 'homogeneity', 'energy', 'correlation', 'asm']:
                values = greycoprops(glcm, prop)
                features[f"glcm_{prop}"] = float(np.mean(values))
            
            return features
        
        except Exception as e:
            logger.warning(f"GLCM feature extraction failed: {e}, returning zeros")
            return {
                "glcm_contrast": 0.0,
                "glcm_dissimilarity": 0.0,
                "glcm_homogeneity": 0.0,
                "glcm_energy": 0.0,
                "glcm_correlation": 0.0,
                "glcm_asm": 0.0
            }
    
    @staticmethod
    def extract_lbp_features(patch: np.ndarray, radius: int = 1) -> Dict[str, float]:
        """
        Extract Local Binary Pattern (LBP) features.
        
        Simple rotation-invariant texture descriptor.
        
        Args:
            patch: 2D patch array
            radius: LBP radius
        
        Returns:
            Dictionary of feature names and values
        """
        try:
            from skimage.feature import local_binary_pattern
            
            # Compute LBP
            lbp = local_binary_pattern(patch, 8, radius, method='uniform')
            
            # Histogram of LBP values
            hist, _ = np.histogram(lbp.flatten(), bins=59, range=(0, 59))
            hist = hist / hist.sum()
            
            # Use histogram entropy as feature
            entropy = -np.sum(hist * np.log(hist + 1e-10))
            
            return {
                "lbp_entropy": float(entropy)
            }
        
        except Exception as e:
            logger.warning(f"LBP feature extraction failed: {e}")
            return {"lbp_entropy": 0.0}


class PatchFeatureExtractor:
    """
    Complete feature extraction pipeline for patches.
    
    Combines statistical, histogram, and texture features.
    """
    
    def __init__(
        self,
        include_statistical: bool = True,
        include_histogram: bool = True,
        include_glcm: bool = True,
        include_lbp: bool = False
    ):
        """
        Initialize feature extractor.
        
        Args:
            include_statistical: Include mean, std, min, max, etc.
            include_histogram: Include histogram and entropy features
            include_glcm: Include GLCM texture features
            include_lbp: Include LBP texture features
        """
        self.include_statistical = include_statistical
        self.include_histogram = include_histogram
        self.include_glcm = include_glcm
        self.include_lbp = include_lbp
        
        self.stat_extractor = StatisticalFeatureExtractor()
        self.texture_extractor = TextureFeatureExtractor()
        
        # Build feature name list
        self.feature_names = self._build_feature_names()
        logger.info(f"Feature extractor initialized: {len(self.feature_names)} features")
    
    def _build_feature_names(self) -> List[str]:
        """Build list of feature names"""
        names = []
        
        if self.include_statistical:
            names.extend([
                "mean", "std", "min", "max", "median", "kurtosis", "skewness",
                "range", "iqr", "cv"
            ])
        
        if self.include_histogram:
            names.extend(["entropy", "energy"])
        
        if self.include_glcm:
            names.extend([
                "glcm_contrast", "glcm_dissimilarity", "glcm_homogeneity",
                "glcm_energy", "glcm_correlation", "glcm_asm"
            ])
        
        if self.include_lbp:
            names.append("lbp_entropy")
        
        return names
    
    def extract_features(self, patch: np.ndarray, patch_id: int = 0) -> PatchFeatures:
        """
        Extract all features from a single patch.
        
        Args:
            patch: 2D patch array (normalized to [0, 1])
            patch_id: Patch identifier
        
        Returns:
            PatchFeatures object
        """
        features_dict = {}
        
        # Statistical features
        if self.include_statistical:
            features_dict.update(self.stat_extractor.extract_basic_statistics(patch))
            features_dict.update(self.stat_extractor.extract_range_features(patch))
        
        # Histogram features
        if self.include_histogram:
            features_dict.update(self.stat_extractor.extract_histogram_features(patch))
        
        # Texture features
        if self.include_glcm:
            features_dict.update(self.texture_extractor.extract_glcm_features(patch))
        
        if self.include_lbp:
            features_dict.update(self.texture_extractor.extract_lbp_features(patch))
        
        # Convert to feature vector
        feature_vector = np.array([
            features_dict.get(name, 0.0) for name in self.feature_names
        ], dtype=np.float32)
        
        return PatchFeatures(
            patch_id=patch_id,
            features=feature_vector,
            feature_names=self.feature_names
        )
    
    def extract_batch_features(
        self,
        patches: List[np.ndarray],
        patch_ids: Optional[List[int]] = None
    ) -> Tuple[np.ndarray, List[PatchFeatures]]:
        """
        Extract features from multiple patches.
        
        Implements Step 6 of the pipeline.
        
        Args:
            patches: List of 2D patch arrays
            patch_ids: Optional list of patch IDs
        
        Returns:
            Tuple of (feature matrix, feature objects)
        """
        logger.info("="*60)
        logger.info("FEATURE EXTRACTION")
        logger.info("="*60)
        
        if patch_ids is None:
            patch_ids = list(range(len(patches)))
        
        patch_features_list = []
        
        for i, patch in enumerate(patches):
            patch_features = self.extract_features(patch, patch_ids[i])
            patch_features_list.append(patch_features)
        
        # Create feature matrix (num_patches x num_features)
        feature_matrix = np.vstack([
            pf.features for pf in patch_features_list
        ])
        
        logger.info(f"✓ Extracted features from {len(patches)} patches")
        logger.info(f"  Feature matrix shape: {feature_matrix.shape}")
        logger.info(f"  Features: {', '.join(self.feature_names[:5])}...")
        
        return feature_matrix, patch_features_list


def create_feature_extractor(feature_level: str = "standard") -> PatchFeatureExtractor:
    """
    Factory function to create feature extractor with predefined levels.
    
    Args:
        feature_level: "minimal", "standard", or "comprehensive"
    
    Returns:
        Configured PatchFeatureExtractor
    """
    if feature_level == "minimal":
        return PatchFeatureExtractor(
            include_statistical=True,
            include_histogram=False,
            include_glcm=False,
            include_lbp=False
        )
    
    elif feature_level == "standard":
        return PatchFeatureExtractor(
            include_statistical=True,
            include_histogram=True,
            include_glcm=True,
            include_lbp=False
        )
    
    elif feature_level == "comprehensive":
        return PatchFeatureExtractor(
            include_statistical=True,
            include_histogram=True,
            include_glcm=True,
            include_lbp=True
        )
    
    else:
        logger.warning(f"Unknown feature level: {feature_level}, using standard")
        return PatchFeatureExtractor()
