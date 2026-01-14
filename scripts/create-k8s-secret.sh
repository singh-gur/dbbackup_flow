#!/bin/bash
# Helper script to create Kubernetes secret for pg-backup-secrets

set -e

NAMESPACE="${NAMESPACE:-prefect}"
SECRET_NAME="${SECRET_NAME:-pg-backup-secrets}"

echo "Creating Kubernetes secret: $SECRET_NAME in namespace: $NAMESPACE"
echo ""

# Prompt for secrets
read -sp "Enter PostgreSQL password: " PG_PASSWORD
echo ""
read -sp "Enter AWS access key: " AWS_ACCESS_KEY
echo ""
read -sp "Enter AWS secret key: " AWS_SECRET_KEY
echo ""

# Create the secret
kubectl create secret generic "$SECRET_NAME" \
  --from-literal=pg-password="$PG_PASSWORD" \
  --from-literal=aws-access-key="$AWS_ACCESS_KEY" \
  --from-literal=aws-secret-key="$AWS_SECRET_KEY" \
  --namespace="$NAMESPACE" \
  --dry-run=client -o yaml | kubectl apply -f -

echo ""
echo "Secret created successfully!"
echo ""
echo "To verify:"
echo "  kubectl get secret $SECRET_NAME -n $NAMESPACE"
