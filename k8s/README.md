# Kubernetes RBAC Configuration

This directory contains the necessary Kubernetes RBAC (Role-Based Access Control) resources for the Prefect worker to create and manage backup jobs.

## Resources

- **ServiceAccount**: `prefect-worker` - Service account used by the Prefect worker
- **Role**: `prefect-worker-role` - Defines permissions needed to manage Jobs and Pods
- **RoleBinding**: `prefect-worker-rolebinding` - Binds the role to the service account

## Permissions Granted

The `prefect-worker-role` grants the following permissions in the `default` namespace:

- **Jobs** (batch): create, get, list, watch, delete, patch
- **Jobs/status** (batch): get
- **Pods**: get, list, watch
- **Pods/log**: get (for retrieving job logs)

## Installation

Apply the RBAC configuration to your Kubernetes cluster:

```bash
kubectl apply -f k8s/rbac.yaml
```

Verify the resources were created:

```bash
kubectl get serviceaccount prefect-worker -n default
kubectl get role prefect-worker-role -n default
kubectl get rolebinding prefect-worker-rolebinding -n default
```

## Usage with Prefect

After applying these manifests, you need to configure your Prefect deployment to use the `prefect-worker` service account.

### Option 1: Update Prefect Work Pool (Recommended)

Update your Kubernetes work pool to use the service account:

```bash
# Via Prefect CLI
prefect work-pool set-variable kubernetes service_account_name prefect-worker
```

Or update via the Prefect UI:
- Go to Work Pools → kubernetes → Edit
- Add `service_account_name: prefect-worker` to the job template

### Option 2: Update Flow Code

Alternatively, you can specify the service account in your flow deployment by updating `prefect.yaml`:

```yaml
deployments:
  - name: dbbackup_flow
    # ... other config ...
    work_pool:
      name: kubernetes
      job_variables:
        packages:
          - "prefect-kubernetes==0.7.2"
        service_account_name: prefect-worker
```

## Troubleshooting

If you see permission errors like:

```
User "system:serviceaccount:default:default" cannot create resource "jobs"
```

This means the Prefect worker is still using the `default` service account. Make sure you've:

1. Applied the RBAC manifests: `kubectl apply -f k8s/rbac.yaml`
2. Configured the work pool or deployment to use `service_account_name: prefect-worker`
3. Redeployed your flow: `just deploy`

## Security Notes

- These permissions are scoped to the `default` namespace only
- The service account can only manage Jobs and read Pod logs
- For production, consider creating a dedicated namespace for backups
- Use Kubernetes Secrets for sensitive credentials instead of Prefect Secrets if preferred
