"""
SAR (Synthetic Aperture Radar) Image Preprocessing Module

Applies standard Sentinel-1 preprocessing to raw GRD products:
- Read GeoTIFF with rasterio
- Convert to backscatter if needed
- Apply speckle filtering
- Normalize pixel values
- Mask invalid pixels

Output: Clean 2D numeric raster ready for patch extraction.
"""

import logging
import numpy as np
from typing import Tuple, Optional, Dict
from pathlib import Path
import rasterio
from rasterio.plot import reshape_as_image
import cv2

logger = logging.getLogger(__name__)


class SARPreprocessor:
    """Preprocess Sentinel-1 SAR imagery"""
    
    def __init__(self):
        """Initialize SAR preprocessor"""
        self.log10_scale_factor = 10.0  # For dB conversion
    
    def read_sentinel1_vv(self, geotiff_path: str) -> Tuple[np.ndarray, Dict]:
        """
        Read Sentinel-1 VV polarization from GeoTIFF.
        
        Args:
            geotiff_path: Path to Sentinel-1 GRD GeoTIFF file
        
        Returns:
            Tuple of (raster array, metadata dict)
        """
        try:
            with rasterio.open(geotiff_path) as src:
                # Read VV band (typically band 1)
                vv_data = src.read(1)
                
                metadata = {
                    "crs": src.crs,
                    "transform": src.transform,
                    "dtype": str(src.dtypes[0]),
                    "nodata": src.nodata,
                    "width": src.width,
                    "height": src.height,
                    "bounds": src.bounds
                }
                
                logger.info(f"✓ Read Sentinel-1 VV from {geotiff_path}")
                logger.info(f"  Shape: {vv_data.shape}, dtype: {vv_data.dtype}")
                
                return vv_data, metadata
        
        except Exception as e:
            logger.error(f"Failed to read GeoTIFF {geotiff_path}: {e}")
            raise
    
    def linear_to_db(self, linear_data: np.ndarray) -> np.ndarray:
        """
        Convert linear backscatter values to dB (decibels).
        
        Sentinel-1 data is often in linear scale. Convert to dB for processing.
        
        Args:
            linear_data: Linear backscatter values
        
        Returns:
            dB-converted array
        """
        # Avoid log of zero/negative values
        linear_data_safe = np.where(linear_data > 0, linear_data, 1.0)
        db_data = self.log10_scale_factor * np.log10(linear_data_safe)
        
        return db_data
    
    def apply_speckle_filter(
        self,
        image: np.ndarray,
        filter_type: str = "median",
        kernel_size: int = 5
    ) -> np.ndarray:
        """
        Apply speckle noise reduction filter.
        
        Sentinel-1 SAR images contain characteristic speckle noise.
        Apply filtering to smooth while preserving edges.
        
        Args:
            image: Input SAR raster
            filter_type: "median", "bilateral", or "morphological"
            kernel_size: Filter kernel size (must be odd)
        
        Returns:
            Filtered image
        """
        if kernel_size % 2 == 0:
            kernel_size += 1
        
        logger.info(f"Applying {filter_type} speckle filter (kernel={kernel_size})")
        
        if filter_type == "median":
            # Median filter: effective for salt-and-pepper noise
            filtered = cv2.medianBlur(image.astype(np.float32), kernel_size)
        
        elif filter_type == "bilateral":
            # Bilateral filter: smooths while preserving edges
            filtered = cv2.bilateralFilter(
                image.astype(np.float32),
                d=kernel_size,
                sigmaColor=75,
                sigmaSpace=75
            )
        
        elif filter_type == "morphological":
            # Morphological opening: removes small noise
            kernel = cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE,
                (kernel_size, kernel_size)
            )
            filtered = cv2.morphologyEx(
                image.astype(np.float32),
                cv2.MORPH_OPEN,
                kernel
            )
        
        else:
            logger.warning(f"Unknown filter type: {filter_type}, returning original")
            filtered = image
        
        return filtered
    
    def normalize_pixel_values(
        self,
        image: np.ndarray,
        method: str = "minmax"
    ) -> np.ndarray:
        """
        Normalize pixel values to standard range.
        
        Args:
            image: Input image
            method: "minmax" (0-1) or "zscore" (mean=0, std=1)
        
        Returns:
            Normalized image
        """
        logger.info(f"Normalizing pixel values using {method} method")
        
        if method == "minmax":
            # Min-max normalization: scale to [0, 1]
            img_min = np.min(image)
            img_max = np.max(image)
            
            if img_max == img_min:
                normalized = np.zeros_like(image)
            else:
                normalized = (image - img_min) / (img_max - img_min)
        
        elif method == "zscore":
            # Z-score normalization: mean=0, std=1
            normalized = (image - np.mean(image)) / (np.std(image) + 1e-8)
        
        else:
            logger.warning(f"Unknown normalization method: {method}")
            normalized = image
        
        return normalized
    
    def mask_invalid_pixels(
        self,
        image: np.ndarray,
        nodata_value: Optional[float] = None,
        mask_water: bool = False
    ) -> np.ndarray:
        """
        Mask invalid or non-relevant pixels.
        
        Args:
            image: Input image
            nodata_value: Value to treat as invalid (None uses dataset's nodata)
            mask_water: If True, try to mask land (keep water only for marine context)
        
        Returns:
            Masked image (invalid pixels set to 0)
        """
        masked = image.copy()
        
        # Mask nodata values
        if nodata_value is not None:
            masked[image == nodata_value] = 0
        
        # If requested, mask very low backscatter (likely non-water)
        # In SAR, water typically has low backscatter
        if mask_water:
            logger.info("Applying water mask (keeping low backscatter areas)")
            # Keep pixels with backscatter below threshold
            backscatter_threshold = np.percentile(masked[masked > 0], 25)
            masked[masked > backscatter_threshold] = 0
        
        return masked
    
    def preprocess_sar_image(
        self,
        geotiff_path: str,
        output_path: Optional[str] = None,
        apply_db_conversion: bool = True,
        speckle_filter: str = "median",
        normalization: str = "minmax",
        mask_water: bool = False
    ) -> Tuple[np.ndarray, Dict]:
        """
        Complete SAR preprocessing pipeline.
        
        Implements Step 4 of the oil spill detection pipeline.
        
        Args:
            geotiff_path: Path to input Sentinel-1 GeoTIFF
            output_path: Optional path to save preprocessed image
            apply_db_conversion: Convert linear to dB scale
            speckle_filter: Type of speckle filter
            normalization: Normalization method
            mask_water: Apply water-only mask
        
        Returns:
            Tuple of (preprocessed raster, metadata)
        """
        logger.info("="*60)
        logger.info("SAR PREPROCESSING PIPELINE")
        logger.info("="*60)
        
        # Step 1: Read GeoTIFF
        raster, metadata = self.read_sentinel1_vv(geotiff_path)
        
        # Step 2: Convert to dB if needed
        if apply_db_conversion:
            raster = self.linear_to_db(raster)
        
        # Step 3: Apply speckle filtering
        raster = self.apply_speckle_filter(raster, filter_type=speckle_filter)
        
        # Step 4: Normalize pixel values
        raster = self.normalize_pixel_values(raster, method=normalization)
        
        # Step 5: Mask invalid pixels
        raster = self.mask_invalid_pixels(
            raster,
            nodata_value=metadata.get("nodata"),
            mask_water=mask_water
        )
        
        # Save preprocessed image if requested
        if output_path:
            self._save_preprocessed_image(
                raster,
                output_path,
                metadata
            )
        
        logger.info(f"✓ Preprocessing complete")
        logger.info(f"  Output shape: {raster.shape}")
        logger.info(f"  Value range: [{raster.min():.4f}, {raster.max():.4f}]")
        
        return raster, metadata
    
    def _save_preprocessed_image(
        self,
        image: np.ndarray,
        output_path: str,
        metadata: Dict
    ):
        """Save preprocessed image as GeoTIFF"""
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with rasterio.open(
                output_path,
                'w',
                driver='GTiff',
                height=image.shape[0],
                width=image.shape[1],
                count=1,
                dtype=image.dtype,
                crs=metadata["crs"],
                transform=metadata["transform"],
                nodata=metadata["nodata"]
            ) as dst:
                dst.write(image, 1)
            
            logger.info(f"✓ Saved preprocessed image to {output_path}")
        
        except Exception as e:
            logger.error(f"Failed to save preprocessed image: {e}")


class MultiPolarizationProcessor:
    """
    Process multi-polarization Sentinel-1 data (VV and VH).
    
    VV: Vertical transmit, Vertical receive (better for rough surfaces)
    VH: Vertical transmit, Horizontal receive (better for vegetation)
    
    For oil spill detection, VV is typically primary.
    """
    
    def __init__(self):
        self.preprocessor = SARPreprocessor()
    
    def read_dual_pol(
        self,
        geotiff_vv: str,
        geotiff_vh: str
    ) -> Tuple[np.ndarray, np.ndarray, Dict]:
        """
        Read both VV and VH polarizations.
        
        Args:
            geotiff_vv: Path to VV band
            geotiff_vh: Path to VH band
        
        Returns:
            Tuple of (VV array, VH array, metadata)
        """
        vv, metadata_vv = self.preprocessor.read_sentinel1_vv(geotiff_vv)
        
        # Read VH using same logic but band 2
        with rasterio.open(geotiff_vh) as src:
            vh = src.read(1)
        
        logger.info(f"✓ Read dual-polarization Sentinel-1 data")
        return vv, vh, metadata_vv
    
    def compute_vh_vv_ratio(
        self,
        vv: np.ndarray,
        vh: np.ndarray
    ) -> np.ndarray:
        """
        Compute VH/VV ratio (useful for oil spill detection).
        
        Oil spills tend to dampen the radar signal,
        affecting the VH/VV ratio distinctly.
        
        Args:
            vv: VV polarization band
            vh: VH polarization band
        
        Returns:
            VH/VV ratio array
        """
        vv_safe = np.where(vv > 0, vv, 1.0)
        ratio = vh / vv_safe
        
        logger.info(f"✓ Computed VH/VV ratio")
        return ratio
