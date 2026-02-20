"""
Patch Extraction Engine

Splits SAR raster into fixed-size patches for processing.
Maintains spatial metadata for coordinate reconstruction.

Implements Step 5 of the oil spill detection pipeline.
"""

import logging
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PatchMetadata:
    """Metadata for a single patch"""
    patch_id: int
    row_start: int
    row_end: int
    col_start: int
    col_end: int
    row_idx: int  # Patch row index in grid
    col_idx: int  # Patch column index in grid
    
    @property
    def center_pixel(self) -> Tuple[int, int]:
        """Get center pixel coordinates (row, col)"""
        row_center = (self.row_start + self.row_end) // 2
        col_center = (self.col_start + self.col_end) // 2
        return (row_center, col_center)
    
    @property
    def size(self) -> Tuple[int, int]:
        """Get patch size (height, width)"""
        height = self.row_end - self.row_start
        width = self.col_end - self.col_start
        return (height, width)
    
    def to_dict(self) -> Dict:
        """Serialize to dictionary"""
        return {
            "patch_id": self.patch_id,
            "row_start": self.row_start,
            "row_end": self.row_end,
            "col_start": self.col_start,
            "col_end": self.col_end,
            "row_idx": self.row_idx,
            "col_idx": self.col_idx,
            "center_pixel": self.center_pixel,
            "size": self.size
        }


class PatchExtractor:
    """Extract fixed-size patches from SAR raster"""
    
    def __init__(
        self,
        patch_size: int = 128,
        stride: int = 64
    ):
        """
        Initialize patch extractor.
        
        Args:
            patch_size: Size of each patch in pixels (patch_size x patch_size)
            stride: Overlap stride (stride < patch_size means overlapping patches)
        """
        self.patch_size = patch_size
        self.stride = stride
        
        logger.info(
            f"Patch Extractor initialized: "
            f"patch_size={patch_size}x{patch_size}, stride={stride}"
        )
    
    def extract_patches(
        self,
        raster: np.ndarray,
        metadata: Optional[Dict] = None
    ) -> Tuple[List[np.ndarray], List[PatchMetadata], Dict]:
        """
        Extract all patches from a raster.
        
        Implements Step 5 of the pipeline.
        
        Args:
            raster: 2D numpy array (SAR image)
            metadata: Optional raster metadata (CRS, transform, etc.)
        
        Returns:
            Tuple of (patch arrays, patch metadata, pipeline metadata)
        """
        logger.info("="*60)
        logger.info("PATCH EXTRACTION")
        logger.info("="*60)
        
        height, width = raster.shape
        logger.info(f"Raster size: {height} x {width}")
        
        patches = []
        patch_metadata_list = []
        patch_id = 0
        
        # Iterate over raster in stride steps
        for row_idx, row_start in enumerate(range(0, height - self.patch_size + 1, self.stride)):
            for col_idx, col_start in enumerate(range(0, width - self.patch_size + 1, self.stride)):
                
                row_end = row_start + self.patch_size
                col_end = col_start + self.patch_size
                
                # Extract patch
                patch = raster[row_start:row_end, col_start:col_end]
                
                # Ensure correct size (handle edge patches)
                if patch.shape != (self.patch_size, self.patch_size):
                    patch = self._pad_patch(patch)
                
                patches.append(patch)
                
                # Create metadata
                patch_meta = PatchMetadata(
                    patch_id=patch_id,
                    row_start=row_start,
                    row_end=row_end,
                    col_start=col_start,
                    col_end=col_end,
                    row_idx=row_idx,
                    col_idx=col_idx
                )
                patch_metadata_list.append(patch_meta)
                patch_id += 1
        
        # Handle remaining patches on right edge
        if width % self.stride != 0:
            col_start = width - self.patch_size
            for row_idx, row_start in enumerate(range(0, height - self.patch_size + 1, self.stride)):
                row_end = row_start + self.patch_size
                patch = raster[row_start:row_end, col_start:col_start + self.patch_size]
                
                if patch.shape != (self.patch_size, self.patch_size):
                    patch = self._pad_patch(patch)
                
                patches.append(patch)
                
                patch_meta = PatchMetadata(
                    patch_id=patch_id,
                    row_start=row_start,
                    row_end=row_end,
                    col_start=col_start,
                    col_end=col_start + self.patch_size,
                    row_idx=row_idx,
                    col_idx=width // self.stride
                )
                patch_metadata_list.append(patch_meta)
                patch_id += 1
        
        # Handle remaining patches on bottom edge
        if height % self.stride != 0:
            row_start = height - self.patch_size
            for col_idx, col_start in enumerate(range(0, width - self.patch_size + 1, self.stride)):
                col_end = col_start + self.patch_size
                patch = raster[row_start:row_start + self.patch_size, col_start:col_end]
                
                if patch.shape != (self.patch_size, self.patch_size):
                    patch = self._pad_patch(patch)
                
                patches.append(patch)
                
                patch_meta = PatchMetadata(
                    patch_id=patch_id,
                    row_start=row_start,
                    row_end=row_start + self.patch_size,
                    col_start=col_start,
                    col_end=col_end,
                    row_idx=height // self.stride,
                    col_idx=col_idx
                )
                patch_metadata_list.append(patch_meta)
                patch_id += 1
        
        # Pipeline metadata
        pipeline_metadata = {
            "raster_shape": (height, width),
            "patch_size": self.patch_size,
            "stride": self.stride,
            "num_patches": len(patches),
            "raster_metadata": metadata or {}
        }
        
        logger.info(f"✓ Extracted {len(patches)} patches")
        logger.info(f"  Patch grid: {len(set(m.row_idx for m in patch_metadata_list))} x "
                   f"{len(set(m.col_idx for m in patch_metadata_list))}")
        
        return patches, patch_metadata_list, pipeline_metadata
    
    def _pad_patch(self, patch: np.ndarray) -> np.ndarray:
        """
        Pad undersized patch to correct size.
        
        Uses reflection padding at edges.
        
        Args:
            patch: Undersized patch
        
        Returns:
            Padded patch of correct size
        """
        target_h, target_w = self.patch_size, self.patch_size
        current_h, current_w = patch.shape
        
        pad_h = target_h - current_h
        pad_w = target_w - current_w
        
        padded = np.pad(
            patch,
            ((0, pad_h), (0, pad_w)),
            mode='reflect'
        )
        
        return padded[:target_h, :target_w]
    
    def extract_roi(
        self,
        raster: np.ndarray,
        bbox: Tuple[int, int, int, int],
        return_metadata: bool = True
    ) -> Tuple[List[np.ndarray], List[PatchMetadata], Dict]:
        """
        Extract patches from a specific region of interest (ROI).
        
        Args:
            raster: Full raster
            bbox: (row_start, col_start, row_end, col_end) in pixel coordinates
            return_metadata: Include metadata in return
        
        Returns:
            Patches, metadata, pipeline info
        """
        row_start, col_start, row_end, col_end = bbox
        roi = raster[row_start:row_end, col_start:col_end]
        
        logger.info(f"Extracting patches from ROI: {bbox}")
        
        return self.extract_patches(roi)


class AdaptivePatchExtractor:
    """
    Extract patches with adaptive size based on features.
    
    Useful when regions of interest vary in size.
    """
    
    def __init__(self, base_patch_size: int = 128):
        self.base_patch_size = base_patch_size
        self.extractor = PatchExtractor(patch_size=base_patch_size)
    
    def extract_adaptive_patches(
        self,
        raster: np.ndarray,
        interest_map: Optional[np.ndarray] = None,
        min_patch_size: int = 64,
        max_patch_size: int = 256
    ) -> Tuple[List[np.ndarray], List[PatchMetadata], Dict]:
        """
        Extract patches with sizes adapted to local interest.
        
        Args:
            raster: Input SAR raster
            interest_map: Heatmap indicating regions of interest (optional)
            min_patch_size: Minimum patch size
            max_patch_size: Maximum patch size
        
        Returns:
            Patches, metadata, pipeline info
        """
        # If no interest map, fall back to uniform patches
        if interest_map is None:
            return self.extractor.extract_patches(raster)
        
        logger.info("Extracting adaptive patches based on interest map")
        
        # For now, use uniform patches
        # In advanced implementation, could use region-growing or
        # watershed algorithm to create adaptive regions
        
        return self.extractor.extract_patches(raster)


def visualize_patches(
    patches: List[np.ndarray],
    patch_metadata: List[PatchMetadata],
    num_display: int = 9,
    save_path: Optional[str] = None
):
    """
    Visualize extracted patches (useful for debugging).
    
    Args:
        patches: List of patch arrays
        patch_metadata: List of patch metadata
        num_display: Number of patches to visualize
        save_path: Optional path to save visualization
    """
    import matplotlib.pyplot as plt
    
    n_display = min(num_display, len(patches))
    grid_size = int(np.ceil(np.sqrt(n_display)))
    
    fig, axes = plt.subplots(grid_size, grid_size, figsize=(12, 12))
    axes = axes.flatten()
    
    for i in range(n_display):
        patch = patches[i]
        meta = patch_metadata[i]
        
        axes[i].imshow(patch, cmap='gray')
        axes[i].set_title(f"Patch {meta.patch_id}\n({meta.row_idx}, {meta.col_idx})")
        axes[i].axis('off')
    
    # Hide unused subplots
    for i in range(n_display, len(axes)):
        axes[i].axis('off')
    
    plt.tight_layout()
    
    if save_path:
        plt.savefig(save_path, dpi=100, bbox_inches='tight')
        logger.info(f"✓ Saved patch visualization to {save_path}")
    
    plt.close()
