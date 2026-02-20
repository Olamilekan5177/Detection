#!/usr/bin/env python
"""Train oil spill detector using scikit-learn (no TensorFlow needed)"""

import os
import sys
import pickle
import numpy as np
from pathlib import Path
from PIL import Image
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
import json

PROJECT_ROOT = Path.cwd()  # Use current working directory (should be project root)
DATA_DIR = PROJECT_ROOT / 'data/training'
MODEL_SAVE_PATH = PROJECT_ROOT / 'ml_models/saved_models/oil_spill_detector.pkl'
MODEL_SAVE_PATH.parent.mkdir(parents=True, exist_ok=True)

IMG_SIZE = (256, 256)

print("=" * 60)
print("OIL SPILL DETECTION - MODEL TRAINING (scikit-learn)")
print("=" * 60)

# 1. Load images
print("\n[1/4] Loading images...")
X = []
y = []

# Oil spill images
oil_dir = DATA_DIR / 'oil_spill'
if oil_dir.exists():
    for img_path in sorted(oil_dir.glob('*')):
        if img_path.suffix.lower() in ['.tif', '.tiff', '.jpg', '.jpeg', '.png']:
            try:
                img = Image.open(img_path).convert('RGB')
                img = img.resize(IMG_SIZE)
                X.append(np.array(img).flatten())
                y.append(1)
            except:
                pass

# No spill images
no_spill_dir = DATA_DIR / 'no_spill'
if no_spill_dir.exists():
    for img_path in sorted(no_spill_dir.glob('*')):
        if img_path.suffix.lower() in ['.tif', '.tiff', '.jpg', '.jpeg', '.png']:
            try:
                img = Image.open(img_path).convert('RGB')
                img = img.resize(IMG_SIZE)
                X.append(np.array(img).flatten())
                y.append(0)
            except:
                pass

X = np.array(X, dtype=np.float32)
y = np.array(y)

print(f"✓ Loaded {len(X)} images")
print(f"  - Oil spills: {np.sum(y)}")
print(f"  - No spills: {len(y) - np.sum(y)}")
print(f"  - Image shape: {X[0].shape}")

# 2. Normalize
print("\n[2/4] Normalizing images...")
X = X / 255.0
print(f"✓ Normalized to [0, 1]")

# 3. Split
print("\n[3/4] Splitting dataset...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
print(f"✓ Train: {len(X_train)} | Test: {len(X_test)}")

# 4. Train
print("\n[4/4] Training neural network...")
print("(This may take 1-2 minutes...)")

model = MLPClassifier(
    hidden_layer_sizes=(256, 128, 64),
    max_iter=500,
    early_stopping=True,
    validation_fraction=0.2,
    n_iter_no_change=20,
    learning_rate_init=0.001,
    random_state=42,
    verbose=1
)

model.fit(X_train, y_train)

# Evaluate
print("\nEvaluating...")
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
precision = precision_score(y_test, y_pred)
recall = recall_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_pred_proba)

print("\n" + "=" * 60)
print("TEST RESULTS")
print("=" * 60)
print(f"Accuracy:  {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall:    {recall:.4f}")
print(f"AUC:       {auc:.4f}")

# Save model
with open(MODEL_SAVE_PATH, 'wb') as f:
    pickle.dump(model, f)

# Save metadata
metadata = {
    'model_type': 'sklearn_mlp',
    'img_size': IMG_SIZE,
    'input_features': X[0].shape[0],
    'accuracy': float(accuracy),
    'precision': float(precision),
    'recall': float(recall),
    'auc': float(auc),
    'training_samples': len(X_train),
    'test_samples': len(X_test),
}

metadata_path = MODEL_SAVE_PATH.with_suffix('.json')
with open(metadata_path, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"\n✓ Model saved to: {MODEL_SAVE_PATH}")
print(f"✓ Metadata saved to: {metadata_path}")
print("=" * 60)
