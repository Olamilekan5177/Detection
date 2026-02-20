import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers, models
from tensorflow.keras.applications import ResNet50, EfficientNetB0

class OilSpillDetector:
    """CNN model for oil spill detection from satellite imagery"""
    
    def __init__(self, input_shape=(256, 256, 3), use_pretrained=True):
        self.input_shape = input_shape
        self.use_pretrained = use_pretrained
        self.model = None
    
    def build_custom_cnn(self):
        """Build custom CNN from scratch
        
        Why: Full control over architecture, lighter weight
        Good for: Limited computational resources
        """
        model = models.Sequential([
            # Block 1
            layers.Conv2D(32, (3, 3), activation='relu', 
                         input_shape=self.input_shape),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Block 2
            layers.Conv2D(64, (3, 3), activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Block 3
            layers.Conv2D(128, (3, 3), activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Block 4
            layers.Conv2D(256, (3, 3), activation='relu'),
            layers.BatchNormalization(),
            layers.MaxPooling2D((2, 2)),
            layers.Dropout(0.25),
            
            # Dense layers
            layers.Flatten(),
            layers.Dense(512, activation='relu'),
            layers.BatchNormalization(),
            layers.Dropout(0.5),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.5),
            
            # Output
            layers.Dense(1, activation='sigmoid')
        ])
        
        return model
    
    def build_transfer_learning_model(self, base_model_name='resnet50'):
        """Build model using transfer learning
        
        Why: Leverages pre-trained features, better accuracy
        Good for: When you have adequate compute resources
        """
        # Choose base model
        if base_model_name == 'resnet50':
            base_model = ResNet50(
                weights='imagenet',
                include_top=False,
                input_shape=self.input_shape
            )
        elif base_model_name == 'efficientnet':
            base_model = EfficientNetB0(
                weights='imagenet',
                include_top=False,
                input_shape=self.input_shape
            )
        
        # Freeze base model layers
        base_model.trainable = False
        
        # Add custom classification head
        model = models.Sequential([
            base_model,
            layers.GlobalAveragePooling2D(),
            layers.Dense(512, activation='relu'),
            layers.Dropout(0.5),
            layers.Dense(256, activation='relu'),
            layers.Dropout(0.3),
            layers.Dense(1, activation='sigmoid')
        ])
        
        return model
    
    def build(self, model_type='transfer'):
        """Build the model"""
        if model_type == 'custom':
            self.model = self.build_custom_cnn()
        else:
            self.model = self.build_transfer_learning_model()
        
        return self.model
    
    def compile_model(self, learning_rate=0.001):
        """Compile the model with optimizer and loss"""
        self.model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss='binary_crossentropy',
            metrics=[
                'accuracy',
                keras.metrics.Precision(name='precision'),
                keras.metrics.Recall(name='recall'),
                keras.metrics.AUC(name='auc')
            ]
        )
    
    def get_callbacks(self, model_save_path):
        """Define training callbacks"""
        return [
            # Save best model
            keras.callbacks.ModelCheckpoint(
                model_save_path,
                monitor='val_auc',
                mode='max',
                save_best_only=True,
                verbose=1
            ),
            # Early stopping
            keras.callbacks.EarlyStopping(
                monitor='val_loss',
                patience=10,
                restore_best_weights=True,
                verbose=1
            ),
            # Reduce learning rate
            keras.callbacks.ReduceLROnPlateau(
                monitor='val_loss',
                factor=0.5,
                patience=5,
                min_lr=1e-7,
                verbose=1
            ),
            # TensorBoard logging
            keras.callbacks.TensorBoard(
                log_dir='./logs',
                histogram_freq=1
            )
        ]