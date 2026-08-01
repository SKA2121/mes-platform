# AWX (AAP open source) — installation et déclenchement par API

AWX est la version communautaire d'Ansible Automation Platform. Sur ce projet,
il joue le rôle de **déclencheur** : il exécute le playbook de déploiement, et
surtout il est pilotable par **API REST** — exactement comme AAP sera piloté par
Control-M chez Rolex.

> AWX consomme de la RAM (~2-3 Go). Si ton lab est juste, comprends d'abord le
> pattern (section API ci-dessous) ; l'installation complète est un bonus.

## 1. Installer via l'operator

```bash
kubectl apply -k "https://github.com/ansible/awx-operator/config/default?ref=2.19.1"
kubectl config set-context --current --namespace=awx

cat <<EOF | kubectl apply -f -
apiVersion: awx.ansible.com/v1beta1
kind: AWX
metadata:
  name: awx-lab
spec:
  service_type: LoadBalancer     # MetalLB lui donnera une IP (.206 par ex.)
EOF

kubectl get pods -n awx -w        # patiente : plusieurs minutes
```

Un **Operator** étend Kubernetes : tu déclares un objet `kind: AWX` et l'operator
construit et maintient tous les composants sous-jacents. C'est un pattern majeur
en entreprise, que tu vois ici en action.

## 2. Accès

```bash
kubectl get svc -n awx awx-lab-service          # note l'EXTERNAL-IP
kubectl get secret awx-lab-admin-password -n awx -o jsonpath="{.data.password}" | base64 -d; echo
```

## 3. Configurer le job

Dans l'UI AWX :
1. **Credentials** → type Kubernetes (ou monte le kubeconfig via le playbook)
2. **Projects** → pointe sur ton repo GitHub `mes-platform`
3. **Job Templates** → nouveau, playbook `ansible/playbooks/deploy.yml`,
   variable `env: dev`

Lance-le une fois depuis l'UI pour valider. Note l'**ID** du job template.

## 4. Le point clé : déclenchement par API

```bash
./scripts/trigger-awx-job.sh <IP_AWX> <TEMPLATE_ID> admin <password>
```

Ou directement :

```bash
curl -sk -X POST \
  https://<IP_AWX>/api/v2/job_templates/<ID>/launch/ \
  -u admin:<password> -H "Content-Type: application/json"
```

Le job se lance comme si tu avais cliqué. **Remplace ce curl par un job Control-M
et tu as le pattern de production Rolex** : Control-M déclenche AAP, AAP déploie
sur Kubernetes.

## Ce qu'il faut retenir pour l'entretien
- Un **operator** gère le cycle de vie d'une app complexe via un objet déclaratif.
- AAP/AWX exécute des playbooks, pilotable par **UI ET API**.
- L'**API REST** permet l'orchestration par un outil tiers (Control-M) — c'est le
  maillon entre l'ordonnancement d'entreprise et l'automatisation Kubernetes.
