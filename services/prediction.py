import sys
from functools import lru_cache

import tensorflow as tf

from image_utils import load_and_preprocess_image, load_class_names

MODEL_PATH = './model.keras'
CONFIDENCE_THRESHOLD = 0.80   # below: manual review (spec §3.4)
MARGIN_THRESHOLD = 0.20       # minimum gap between the top 2 classes
REJECT_CLASS = 'autre'


@lru_cache(maxsize=1)
def load_model():
    return tf.keras.models.load_model(MODEL_PATH), load_class_names()


def predict_document(img_path, target_class=None):
    """Classifies a document (image or PDF). The model already outputs probabilities
    (softmax). If target_class is given (e.g. 'cin'), also checks whether the document
    matches the expected type."""
    model, class_names = load_model()
    probabilities = model.predict(load_and_preprocess_image(img_path), verbose=0)[0]

    order = probabilities.argsort()[::-1]
    top1, top2 = order[0], order[1]
    confidence = float(probabilities[top1])
    margin = confidence - float(probabilities[top2])
    predicted_class = class_names[top1]

    needs_manual_review = (confidence < CONFIDENCE_THRESHOLD
                           or margin < MARGIN_THRESHOLD
                           or predicted_class == REJECT_CLASS)

    result = {
        'predicted_class': predicted_class,
        'confidence': confidence,
        'revue_manuelle': needs_manual_review,
        'class_confidences': {class_names[i]: float(probabilities[i]) for i in order},
    }

    if target_class is not None:
        result['target_class'] = target_class
        result['match'] = predicted_class == target_class
        if result['match']:
            result['message'] = f"OK ! C'est bien un {target_class}."
        else:
            result['message'] = f"Non ! Ce document ressemble plutôt à : {predicted_class}."

    return result


if __name__ == '__main__':
    path = sys.argv[1] if len(sys.argv) > 1 else './testImage/tulipe.jpg'
    print(predict_document(path))
