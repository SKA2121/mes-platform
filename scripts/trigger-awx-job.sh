#!/usr/bin/env bash
# =============================================================
# Déclenche un Job Template AWX via son API REST.
# C'est EXACTEMENT le pattern par lequel Control-M pilotera AAP
# chez Rolex : un ordonnanceur externe appelle cette API pour
# lancer un déploiement au bon moment.
#
# Usage :
#   ./trigger-awx-job.sh <IP_AWX> <JOB_TEMPLATE_ID> <user> <password>
# Exemple :
#   ./trigger-awx-job.sh 192.168.56.206 7 admin monMotDePasse
# =============================================================
set -euo pipefail

AWX_HOST="${1:?IP ou host AWX requis}"
TEMPLATE_ID="${2:?ID du job template requis}"
AWX_USER="${3:-admin}"
AWX_PASS="${4:?mot de passe requis}"

echo ">>> Lancement du job template ${TEMPLATE_ID} sur ${AWX_HOST}..."

RESPONSE=$(curl -sk -X POST \
  "https://${AWX_HOST}/api/v2/job_templates/${TEMPLATE_ID}/launch/" \
  -u "${AWX_USER}:${AWX_PASS}" \
  -H "Content-Type: application/json")

JOB_ID=$(echo "$RESPONSE" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

if [ -n "${JOB_ID:-}" ]; then
  echo ">>> Job lancé avec succès. ID : ${JOB_ID}"
  echo ">>> Suivi : https://${AWX_HOST}/#/jobs/playbook/${JOB_ID}/output"
else
  echo ">>> Réponse AWX :"
  echo "$RESPONSE"
fi
