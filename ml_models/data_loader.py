import os
import numpy as np
from pathlib import Path
import cv2
from sklearn.preprocessing import StandardScaler
import logging

logger = logging.getLogger(__name__)

class DatasetLoader:
    """Load dataset from directory structure with two subdirectories: oil_spill/ and no_spill/"""
    
    def __init__(self, data_dir, img_size=(256, 256)):
        """
        Args:
            data_dir: Path to directory containing oil_spill/ and no_spill/ subdirectories
            img_size: Target image size (height, width)
        """
        self.data_dir = Path(data_dir)
        self.img_size = img_size
        self.scaler = StandardScaler()
    
    def load_dataset(self):
        """
        Load all images from directory structure
        
        Returns:
            X: Array of shape (N, height, width, 3)
            y: Binary labels (1 for oil spill, 0 for no spill)
        """
        X = []
        y = []
        
        # Load oil spill images (label = 1)
        oil_spill_dir = self.data_dir / 'oil_spill'
        if oil_spill_dir.exists():
            logger.info(f"Loading oil spill images from {oil_spill_dir}")
            for img_path in oil_spill_dir.glob('*'):
                if self._is_image_file(img_path):
                    try:
                        img = self._load_and_preprocess_image(img_path)
                        X.append(img)
                        y.append(1)
                    except Exception as e:
                        logger.warning(f"Failed to load {img_path}: {str(e)}")
        else:
            logger.warning(f"Oil spill directory not found: {oil_spill_dir}")
        
        # Load no spill images (label = 0)
        no_spill_dir = self.data_dir / 'no_spill'
        if no_spill_dir.exists():
            logger.info(f"Loading no-spill images from {no_spill_dir}")
            for img_path in no_spill_dir.glob('*'):
                if self._is_image_file(img_path):
                    try:
                        img = self._load_and_preprocess_image(img_path)
                        X.append(img)
                        y.append(0)
                    except Exception as e:
                        logger.warning(f"Failed to load {img_path}: {str(e)}")
        else:
            logger.warning(f"No-spill directory not found: {no_spill_dir}")
        
        if len(X) == 0:
            raise ValueError(f"No images found in {self.data_dir}")
        
        # Convert to numpy arrays
        X = np.array(X, dtype=np.float32)
        y = np.array(y, dtype=np.int32)
        
        logger.info(f"Loaded {len(X)} images")
        logger.info(f"Data shape: {X.shape}")
        logger.info(f"Label distribution - Oil spill: {np.sum(y)}, No spill: {len(y) - np.sum(y)}")
        
        return X, y
    
    def load_dataset_with_paths(self):
        """
        Load dataset and return file paths alongside data
        
        Returns:
            X: Image array
            y: Labels
            paths: List of original file paths
        """
        X = []
        y = []
        paths = []
        
        # Load oil spill images
        oil_spill_dir = self.data_dir / 'oil_spill'
        if oil_spill_dir.exists():
            for img_path in oil_spill_dir.glob('*'):
                if self._is_image_file(img_path):
                    try:
                        img = self._load_and_preprocess_image(img_path)
                        X.append(img)
                        y.append(1)
                        paths.append(str(img_path))
                    except Exception as e:
                        logger.warning(f"Failed to load {img_path}: {str(e)}")
        
        # Load no spill images
        no_spill_dir = self.data_dir / 'no_spill'
        if no_spill_dir.exists():
            for img_path in no_spill_dir.glob('*'):
                if self._is_image_file(img_path):
                    try:
                        img = self._load_and_preprocess_image(img_path)
                        X.append(img)
                        y.append(0)
                        paths.append(str(img_path))
                    except Exception as e:
                        logger.warning(f"Failed to load {img_path}: {str(e)}")
        
        return np.array(X), np.array(y), paths
    
    def _is_image_file(self, path):
        """Check if file is a valid image"""
        valid_extensions = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.bmp', '.gif'}
        return Path(path).suffix.lower() in valid_extensions
    
    def _load_and_preprocess_image(self, img_path):
        """
        Load and preprocess a single image
        
        Args:
            img_path: Path to image file
            
        Returns:
            Preprocessed image array
        """
        # Read image
        img = cv2.imread(str(img_path))
        
        if img is None:
            raise ValueError(f"Failed to read image: {img_path}")
        
        # Convert BGR to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Resize to target size
        img = cv2.resize(img, self.img_size)
        
        # Normalize to [0, 1]
        img = img.astype(np.float32) / 255.0
        
        return img
    
    def get_sample_batch(self, batch_size=8):
        """
        Get a random sample batch for visualization
        
        Args:
            batch_size: Number of samples to return
            
        Returns:
            X_batch: Batch of images
            y_batch: Batch of labels
        """
        X, y = self.load_dataset()
        
        indices = np.random.choice(len(X), size=batch_size, replace=False)
        X_batch = X[indices]
        y_batch = y[indices]
        
        return X_batch, y_batch
    
    @staticmethod
    def create_mock_dataset(data_dir, num_spill=50, num_no_spill=50, img_size=(256, 256)):
        """
        Create a mock dataset for testing
        
        Args:
            data_dir: Directory to save mock dataset
            num_spill: Number of oil spill mock images
            num_no_spill: Number of no-spill mock images
            img_size: Image dimensions
        """
        data_dir = Path(data_dir)
        
        # Create directories
        (data_dir / 'oil_spill').mkdir(parents=True, exist_ok=True)
        (data_dir / 'no_spill').mkdir(parents=True, exist_ok=True)
        
        # Create mock oil spill images (darker regions)
        logger.info(f"Creating {num_spill} mock oil spill images...")
        for i in range(num_spill):
            img = np.random.randint(50, 150, (*img_size, 3), dtype=np.uint8)
            # Add some darker spots (simulating oil)
            for _ in range(3):
                y, x = np.random.randint(0, img_size[0], 2)
                h, w = np.random.randint(20, 60, 2)
                img[y:y+h, x:x+w] = np.random.randint(20, 80, 3)
            
            path = data_dir / 'oil_spill' / f'spill_{i:04d}.png'
            cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        
        # Create mock no-spill images (random noise)
        logger.info(f"Creating {num_no_spill} mock no-spill images...")
        for i in range(num_no_spill):
            img = np.random.randint(100, 200, (*img_size, 3), dtype=np.uint8)
            path = data_dir / 'no_spill' / f'no_spill_{i:04d}.png'
            cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
        
        logger.info(f"Mock dataset created at {data_dir}")
        
        return data_dir
