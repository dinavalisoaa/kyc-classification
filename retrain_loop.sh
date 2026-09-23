#!/bin/sh
# Boucle de ré-entraînement continu : lance training.retrain à intervalle fixe.
# RETRAIN_INTERVAL_SECONDS (défaut 86400 = 1x/jour) réglable via docker-compose.yml.
set -e

INTERVAL="${RETRAIN_INTERVAL_SECONDS:-86400}"

while true; do
    echo "[retrain_loop] $(date -Iseconds) -- lancement training.retrain"
    python -m training.retrain || echo "[retrain_loop] training.retrain a échoué, on réessaiera au prochain cycle"
    echo "[retrain_loop] prochain cycle dans ${INTERVAL}s"
    sleep "$INTERVAL"
done
