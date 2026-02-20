#!/usr/bin/env python
"""Create mock training data for development/testing"""

import numpy as np
from pathlib import Path
from PIL import Image
import sys

# Setup paths
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.append(str(PROJECT_ROOT))

def create_mock_images(output_dir, label_dir, num_images=50, img_size=(256, 256)):
    """Create synthetic satellite images"""
    output_path = Path(output_dir) / label_dir
    output_path.mkdir(parents=True, exist_ok=True)
    
    for i in range(num_images):
        if label_dir == 'oil_spill':
            # Create image with dark region (simulating oil spill)
            img = np.random.randint(100, 200, (img_size[0], img_size[1], 3), dtype=np.uint8)
            
            # Add dark spot (oil spill)
            y, x = np.random.randint(50, img_size[0]-50, 2)
            r = np.random.randint(30, 60)
            for dy in range(-r, r):
                for dx in range(-r, r):
                    if dy**2 + dx**2 < r**2:
                        ny, nx = y + dy, x + dx
                        if 0 <= ny < img_size[0] and 0 <= nx < img_size[1]:
                            img[ny, nx] = [30, 30, 30]  # Dark spot
        else:
            # Create clean image (no oil spill)
            img = np.random.randint(120, 220, (img_size[0], img_size[1], 3), dtype=np.uint8)
            # Add some random noise to simulate water texture
            noise = np.random.normal(0, 5, (img_size[0], img_size[1], 3))
            img = np.clip(img + noise, 0, 255).astype(np.uint8)
        
        # Save image
        pil_img = Image.fromarray(img, 'RGB')
        output_filename = output_path / f'{label_dir}_{i:04d}.tif'
        pil_img.save(output_filename)
        
        if (i + 1) % 10 == 0:
            print(f"  Created {i + 1}/{num_images} {label_dir} images")

def main():
    """Generate mock training data"""
    data_dir = PROJECT_ROOT / 'data/training'
    
    print("=" * 60)
    print("CREATING MOCK TRAINING DATA")
    print("=" * 60)
    
    # Parameters
    num_oil_spill = 50
    num_no_spill = 50
    img_size = (256, 256)
    
    print(f"\nGenerating {num_oil_spill} oil spill images...")
    create_mock_images(data_dir, 'oil_spill', num_oil_spill, img_size)
    
    print(f"\nGenerating {num_no_spill} no spill images...")
    create_mock_images(data_dir, 'no_spill', num_no_spill, img_size)
    
    print("\n" + "=" * 60)
    print(f"✓ Mock training data created at: {data_dir}")
    print(f"  - {num_oil_spill} oil spill images")
    print(f"  - {num_no_spill} no spill images")
    print("=" * 60)

if __name__ == '__main__':
    main()
