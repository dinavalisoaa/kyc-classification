---
title: Classification Images KYC
emoji: 🪪
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# Documentation du Projet de Classification d'Images

## Introduction
Ce projet consiste en une application de classification d'images utilisant TensorFlow et Flask. L'application permet de charger des images, d'entraîner un modèle de classification, et de faire des prédictions en utilisant ce modèle.

## Installation

### Prérequis
- **Python** : Version 3.6 ou ultérieure
- **TensorFlow** : Pour la construction et l'entraînement du modèle
- **Flask** : Pour créer l'application web
- **NumPy** : Pour les opérations sur les tableaux
- **Pillow** : Pour la manipulation des images
- **Matplotlib** : Pour la visualisation des métriques

Voici les tailles approximatives des principales bibliothèques requises pour le projet :

- **TensorFlow** : Environ 500 Mo à 1 Go. TensorFlow est une bibliothèque volumineuse, surtout si tu installes les versions avec le support GPU.

- **Flask** : Environ 1 Mo. Flask est relativement léger.

- **NumPy** : Environ 20 Mo. NumPy est aussi assez léger.

- **Pillow** : Environ 10 Mo. Pillow est une bibliothèque légère pour la manipulation d'images.

- **Matplotlib** : Environ 100 Mo. Matplotlib est plus lourd que Flask et Pillow, mais reste raisonnable.

Les tailles peuvent varier légèrement en fonction des versions et des plateformes. Les tailles totales d'installation dépendent aussi de la configuration de ton environnement et des dépendances supplémentaires qui peuvent être installées automatiquement.

### Installation des Dépendances
Utilise le fichier `requirements.txt` pour installer les dépendances nécessaires :
```txt
Flask
tensorflow>=2.0
numpy
Pillow
matplotlib
```
Installe les dépendances avec la commande suivante :
```bash
pip install -r requirements.txt
```

## Configuration

### Structure du Projet
- **Entraînement du Modèle** :
  - `training/model_training.py` : Script pour construire, entraîner et évaluer le modèle.
  - `data/train/` : Répertoire contenant les sous-dossiers pour chaque classe d'images.
  - `model.keras` : Modèle de machine learning pré-entraîné.

- **Application Flask** :
  - `app.py` : Script principal pour l'application Flask.
  - `uploads/` : Répertoire où les images téléchargées sont stockées temporairement.
  - `templates/` : Contient les fichiers HTML pour les interfaces utilisateur :
    - `index.html` : Page d'accueil avec le formulaire d'upload.
    - `results.html` : Page pour afficher les résultats des prédictions.

### Fichiers de Configuration
Aucun fichier de configuration spécifique n'est requis pour ces scripts. Assure-toi que les chemins vers le modèle et les données sont corrects.

## Entraînement du Modèle

### Description des Fonctions

- **`prepare_datasets(img_height, img_width, batch_size)`**
  - Charge et prétraite les ensembles de données d'entraînement et de validation.
  - Normalise les images en les redimensionnant à une échelle de [0, 1].

- **`build_model(img_height, img_width, num_classes)`**
  - Construit un modèle séquentiel avec des couches de convolution, de max-pooling, de dropout, et des couches denses.

- **`compile_model(model)`**
  - Compile le modèle avec l'optimiseur Adam et la perte de catégorie croisée.

- **`train_model(model, train_ds, val_ds, epochs)`**
  - Entraîne le modèle avec un arrêt précoce pour éviter le surapprentissage.

- **`plot_and_save_metrics(history, filename='metrics_plot.png')`**
  - Trace et enregistre les métriques d'entraînement et de validation dans un fichier PNG.

- **`save_model(model, filepath='./model.keras')`**
  - Enregistre le modèle entraîné dans un fichier Keras.

- **`evaluate_model(model, val_ds)`**
  - Évalue le modèle sur l'ensemble de validation et affiche la précision.

### Exemple de Code
Voici comment utiliser les fonctions pour entraîner le modèle :
```python
img_height = 180
img_width = 180
batch_size = 32
num_classes = 6
epochs = 10

train_ds, val_ds = prepare_datasets(img_height, img_width, batch_size)
model = build_model(img_height, img_width, num_classes)
compile_model(model)
history = train_model(model, train_ds, val_ds, epochs)
plot_and_save_metrics(history)
save_model(model)
evaluate_model(model, val_ds)
```

## Application Flask

### Description des Routes

- **`/` (GET, POST)** : 
  - **GET** : Affiche le formulaire de téléchargement de l'image.
  - **POST** : Gère le téléchargement de l'image, la prédiction, et affiche les résultats.

- **`/results`** : Affiche la page des résultats. Cette route est utilisée pour rendre le modèle de résultats plus lisible.

### Description des Fonctions

- **`allowed_file(filename)`**
  - Vérifie si le fichier a une extension autorisée (jpg, jpeg, png).

- **`softmax(x)`**
  - Fonction softmax pour convertir les scores en probabilités.

- **`load_model_and_classes()`**
  - Charge le modèle pré-entraîné et récupère les noms des classes à partir des répertoires d'entraînement.

- **`get_classes_from_data_dir()`**
  - Obtient les noms des classes à partir du répertoire de données.

- **`load_and_preprocess_image(img_path, img_height, img_width)`**
  - Charge l'image depuis le disque, la redimensionne, la convertit en tableau numpy et la normalise.

- **`predict_flower(img_path, model, img_height, img_width, class_names)`**
  - Prétraite l'image, fait des prédictions avec le modèle, et retourne les résultats sous forme de dictionnaire.

### Exemple de Code
Voici comment utiliser les fonctions dans l'application Flask pour faire une prédiction :
```python
img_height = 180
img_width = 180
file_path = 'path_to_your_image.jpg'
results = predict_flower(file_path, model, img_height, img_width, class_names)
print(results)
```

## Résolution de Problèmes

### Erreurs Courantes
- **Entraînement du Modèle** :
  - **Problème de Chargement des Données** : Assure-toi que les chemins vers les dossiers `data/train` et `data/val` sont corrects et que les images sont correctement organisées.
  - **Problème d'Installation** : Vérifie les versions des bibliothèques et assure-toi qu'elles sont compatibles avec le script.

- **Application Flask** :
  - **Problème de Téléchargement de Fichier** : Assure-toi que le fichier est au format autorisé et que la taille du fichier ne dépasse pas la limite spécifiée.
  - **Problème de Chargement du Modèle** : Vérifie que le fichier `model.keras` est présent et accessible.
  - **Problème de Prédiction** : Assure-toi que l'image est correctement prétraitée et que le modèle est correctement chargé.

### Dépannage
- **Pour les erreurs lors de l'entraînement** : Vérifie les paramètres d'entrée et ajuste les hyperparamètres du modèle si nécessaire.
- **Pour les problèmes de l'application Flask** : Assure-toi que les chemins de fichiers sont corrects et que les dépendances sont installées correctement.

## Déploiement en production (Docker) et ré-entraînement continu

### Démarrage

```bash
docker compose up -d --build
```

Lance deux services :
- **`app`** : l'API Flask servie par gunicorn (1 worker, 4 threads — le modèle n'est chargé qu'une fois en mémoire), exposée sur `http://localhost:8000`.
- **`retrain`** : boucle de ré-entraînement continu (`retrain_loop.sh`), qui lance `training/retrain.py` toutes les `RETRAIN_INTERVAL_SECONDS` secondes (défaut : 86400, soit 1x/jour).

Variables d'environnement (`.env` ou export avant `docker compose up`) :
- `RELOAD_TOKEN` : jeton partagé entre `app` et `retrain` pour autoriser le rechargement du modèle. À changer en prod (défaut `change-me`).
- `RETRAIN_INTERVAL_SECONDS` : intervalle entre deux cycles de ré-entraînement.

### Appeler l'API

```bash
curl -F file=@testImage/tulipe.jpg http://localhost:8000/api/classify
```

Retourne un JSON avec `predicted_class`, `confidence`, `revue_manuelle` et `class_confidences` (voir `prediction.py`).

### Comment fonctionne le ré-entraînement continu

1. Déposer les nouvelles images labellisées dans `cin-data/<classe>/`.
2. Au prochain cycle (ou immédiatement via `docker compose run --rm retrain python -m training.retrain`), `training/retrain.py` :
   - reconstruit `data/kyc` depuis `cin-data` (`training/prepare_dataset.py`),
   - entraîne une nouvelle version et l'évalue sur le même set de validation que l'ancien modèle en prod,
   - refuse de déployer en cas de régression d'accuracy (sauf `--force`),
   - sauvegarde chaque tentative dans `models/` et garde une copie de rollback du modèle prod précédent.
3. Si le nouveau modèle est déployé (`model.keras` écrasé), `training/retrain.py` notifie automatiquement le service `app` via `POST /internal/reload` pour qu'il recharge le modèle sans redémarrage.

## Contributions

### Comment Contribuer
Pour contribuer au projet, propose des modifications via des pull requests sur le dépôt GitHub du projet.

### Licence
Ce projet est sous la licence MIT. Consulte le fichier `LICENSE` pour plus de détails.

## Références

- [Documentation TensorFlow](https://www.tensorflow.org/api_docs/python/tf)
- [Documentation Flask](https://flask.palletsprojects.com/)
- [NumPy Documentation](https://numpy.org/doc/stable/)
- [Pillow Documentation](https://pillow.readthedocs.io/en/stable/)
- [Matplotlib Documentation](https://matplotlib.org/stable/contents.html)