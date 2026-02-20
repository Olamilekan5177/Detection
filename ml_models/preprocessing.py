import cv2
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
import rasterio
from rasterio.plot import reshape_as_image

class ImagePreprocessor:
    """Preprocess satellite imagery for ML model"""
    
    def __init__(self, target_size=(256, 256)):
        self.target_size = target_size
    
    def load_sentinel_image(self, file_path, bands=[1, 2, 3]):
        """Load Sentinel satellite image
        
        Why: Sentinel images are multi-band raster files, not regular images
        Params: bands - which bands to use (typically RGB or NIR combinations)
        """
        with rasterio.open(file_path) as src:
            # Read selected bands
            img_array = src.read(bands)
            # Convert to height x width x channels
            img_array = reshape_as_image(img_array)
        
        return img_array
    
    def normalize_image(self, image):
        """Normalize pixel values
        
        Why: Neural networks train better with normalized inputs
        """
        # Check if image is 16-bit (common in satellite imagery)
        if image.dtype == np.uint16:
            image = image.astype(np.float32) / 65535.0
        else:
            image = image.astype(np.float32) / 255.0
        
        return image
    
    def resize_image(self, image):
        """Resize image to target size"""
        return cv2.resize(image, self.target_size)
    
    def enhance_contrast(self, image):
        """Apply contrast enhancement
        
        Why: Oil spills often have subtle visual differences
        """
        # Convert to LAB color space
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        
        # Apply CLAHE to L channel
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        l = clahe.apply(l)
        
        # Merge and convert back
        enhanced = cv2.merge([l, a, b])
        enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2RGB)
        
        return enhanced
    
    def preprocess(self, image_path, is_satellite=True):
        """Complete preprocessing pipeline"""
        # Load image
        if is_satellite:
            image = self.load_sentinel_image(image_path)
        else:
            image = cv2.imread(image_path)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize
        image = self.resize_image(image)
        
        # Enhance contrast
        image = self.enhance_contrast(image)
        
        # Normalize
        image = self.normalize_image(image)
        
        return image
    
    def get_data_augmentation(self):
        """Data augmentation for training
        
        Why: Increases dataset size and model robustness
        """
        return ImageDataGenerator(
            rotation_range=20,
            width_shift_range=0.2,
            height_shift_range=0.2,
            horizontal_flip=True,
            vertical_flip=True,
            zoom_range=0.2,
            shear_range=0.15,
            fill_mode='reflect'
        )