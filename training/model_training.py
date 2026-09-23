import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf
from sklearn.metrics import classification_report, confusion_matrix
from tensorflow.keras import layers, models

from image_utils import IMG_SIZE, save_class_names

TRAIN_DIR = 'data/kyc/train'
VAL_DIR = 'data/kyc/val'


def prepare_datasets(img_height, img_width, batch_size):
    # Load the datasets (values 0-255: MobileNetV3 normalizes internally)
    train_ds = tf.keras.utils.image_dataset_from_directory(
        TRAIN_DIR, image_size=(img_height, img_width), batch_size=batch_size,
        shuffle=True, seed=42
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        VAL_DIR, image_size=(img_height, img_width), batch_size=batch_size,
        shuffle=False
    )
    class_names = train_ds.class_names
    assert class_names == val_ds.class_names, 'Different train/val classes'

    # Class weights to compensate for imbalance (autre >> cif/stat)
    labels = np.concatenate([y.numpy() for _, y in train_ds])
    counts = np.bincount(labels, minlength=len(class_names))
    class_weight = {i: len(labels) / (len(class_names) * c) for i, c in enumerate(counts)}

    train_ds = train_ds.prefetch(tf.data.AUTOTUNE)
    val_ds = val_ds.prefetch(tf.data.AUTOTUNE)
    return train_ds, val_ds, class_names, class_weight


def build_model(img_height, img_width, num_classes):
    # Transfer learning: ImageNet-pretrained MobileNetV3Small + classification head
    base = tf.keras.applications.MobileNetV3Small(
        input_shape=(img_height, img_width, 3), include_top=False, weights='imagenet',
        include_preprocessing=True, name='base'
    )
    base.trainable = False

    # "Phone photo" style augmentation (active only during training)
    augmentation = models.Sequential([
        layers.RandomRotation(0.03),
        layers.RandomZoom(0.1),
        layers.RandomTranslation(0.05, 0.05),
        layers.RandomContrast(0.2),
        layers.RandomBrightness(0.2, value_range=(0, 255)),
    ], name='augmentation')

    inputs = layers.Input(shape=(img_height, img_width, 3))
    x = augmentation(inputs)
    x = base(x, training=False)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.3)(x)
    outputs = layers.Dense(num_classes, activation='softmax')(x)
    return models.Model(inputs, outputs)


def compile_model(model, learning_rate=1e-3):
    model.compile(optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
                  loss='sparse_categorical_crossentropy',
                  metrics=['accuracy'])


def train_model(model, train_ds, val_ds, epochs, class_weight=None):
    # Phase 1: head only (base frozen)
    callbacks = [tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5,
                                                  restore_best_weights=True)]
    h1 = model.fit(train_ds, validation_data=val_ds, epochs=epochs,
                   callbacks=callbacks, class_weight=class_weight)

    # Phase 2: fine-tune the base's last layers, small learning rate
    base = model.get_layer('base')
    base.trainable = True
    for layer in base.layers[:-30]:
        layer.trainable = False
    for layer in base.layers:  # keep BatchNorm frozen (small dataset)
        if isinstance(layer, layers.BatchNormalization):
            layer.trainable = False
    compile_model(model, learning_rate=1e-5)
    callbacks = [tf.keras.callbacks.EarlyStopping(monitor='val_loss', patience=5,
                                                  restore_best_weights=True)]
    h2 = model.fit(train_ds, validation_data=val_ds, epochs=epochs,
                   callbacks=callbacks, class_weight=class_weight)

    # Combined history of both phases
    return {k: h1.history[k] + h2.history[k] for k in h1.history}


def plot_and_save_metrics(history, filename='metrics_plot.png'):
    epochs = range(1, len(history['loss']) + 1)
    plt.figure(figsize=(12, 6))

    plt.subplot(1, 2, 1)
    plt.plot(epochs, history['accuracy'], label="Précision d'entraînement")
    plt.plot(epochs, history['val_accuracy'], label='Précision de validation')
    plt.title('Précision du modèle')
    plt.xlabel('Époque')
    plt.ylabel('Précision')
    plt.legend(loc='upper left')

    plt.subplot(1, 2, 2)
    plt.plot(epochs, history['loss'], label="Perte d'entraînement")
    plt.plot(epochs, history['val_loss'], label='Perte de validation')
    plt.title('Perte du modèle')
    plt.xlabel('Époque')
    plt.ylabel('Perte')
    plt.legend(loc='upper left')

    plt.tight_layout()
    plt.savefig(filename, format='png')
    plt.close()
    print(f"Tracé des métriques enregistré sous {filename}")


def save_model(model, filepath='./model.keras'):
    model.save(filepath)
    print(f"Modèle enregistré sous {filepath}")


def evaluate_model(model, val_ds, class_names, cm_filename='confusion_matrix.png'):
    loss, acc = model.evaluate(val_ds, verbose=0)
    print(f"Précision de validation : {acc:.3f}")

    y_true = np.concatenate([y.numpy() for _, y in val_ds])
    y_pred = np.argmax(model.predict(val_ds, verbose=0), axis=1)
    labels = list(range(len(class_names)))
    print(classification_report(y_true, y_pred, labels=labels,
                                target_names=class_names, zero_division=0))

    cm = confusion_matrix(y_true, y_pred, labels=labels)
    plt.figure(figsize=(7, 6))
    plt.imshow(cm, cmap='Blues')
    plt.xticks(labels, class_names, rotation=45, ha='right')
    plt.yticks(labels, class_names)
    for i in labels:
        for j in labels:
            plt.text(j, i, cm[i, j], ha='center', va='center')
    plt.xlabel('Prédit')
    plt.ylabel('Réel')
    plt.title('Matrice de confusion (validation)')
    plt.tight_layout()
    plt.savefig(cm_filename)
    plt.close()
    print(f"Matrice de confusion enregistrée sous {cm_filename}")


def main():
    batch_size = 16
    epochs = 30

    train_ds, val_ds, class_names, class_weight = prepare_datasets(IMG_SIZE, IMG_SIZE, batch_size)
    print("Classes :", class_names)

    model = build_model(IMG_SIZE, IMG_SIZE, len(class_names))
    compile_model(model)
    history = train_model(model, train_ds, val_ds, epochs, class_weight)

    plot_and_save_metrics(history)
    save_model(model)
    save_class_names(class_names)
    evaluate_model(model, val_ds, class_names)


if __name__ == "__main__":
    main()
