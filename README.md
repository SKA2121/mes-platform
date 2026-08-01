# MES Platform — Projet intégré Kubernetes de bout en bout

Une plateforme MES (suivi d'ordres de fabrication) déployée à travers **toute**
la chaîne d'outils d'un environnement on-prem moderne. Objectif : partir d'une
**URL** (`http://mes.lab.local`) et remonter toute la pile jusqu'aux pods, en
**haute disponibilité que tu éprouves toi-même**.

**Chaîne complète :** Docker → GitHub Actions (CI) → Helm → Argo CD (GitOps) →
MetalLB + Traefik (load balancing) → k3s (3 nœuds) → Ansible/AWX (automatisation).

Lis d'abord **`docs/ARCHITECTURE.md`** : il contient le schéma du flux complet.

---

## Ta topologie

| VM | IP | Rôle |
|----|----|----|
| k3s-server | 192.168.56.10 | control plane k3s + **control node Ansible** |
| k3s-agent1 | 192.168.56.11 | worker |
| k3s-agent2 | 192.168.56.12 | worker |

Prérequis déjà en place (semaine 1 du programme) : k3s, MetalLB (pool
.200-.220), Traefik, StorageClass `nfs-client`.

Avant tout : **remplace `ska2121`** par ton identifiant GitHub dans
`helm-chart/values.yaml`, `argocd/app-dev.yaml`, `argocd/app-prod.yaml`.

---

## Phase 0 — GitHub

```bash
git init && git add . && git commit -m "MES Platform initial"
git remote add origin https://github.com/TON_COMPTE/mes-platform.git
git branch -M main && git push -u origin main
```

Le push déclenche la CI (onglet **Actions**). Une fois l'image construite, rends
le package GHCR **public** (repo → Packages → Package settings → Public), sinon
le cluster ne pourra pas la tirer.

---

## Phase 1 — Helm (déploiement manuel, pour comprendre)

```bash
helm lint ./helm-chart
helm template mes ./helm-chart -f helm-chart/values-dev.yaml   # inspecte le rendu

helm install mes ./helm-chart -f helm-chart/values-dev.yaml \
  --namespace mes-dev --create-namespace
kubectl get pods -n mes-dev -w
```

Ajoute au fichier hosts Windows (`C:\Windows\System32\drivers\etc\hosts`), avec
l'IP de Traefik (`kubectl get svc -n kube-system traefik`) :

```
192.168.56.200  mes-dev.lab.local
192.168.56.200  mes.lab.local
```

Teste : ouvre `http://mes-dev.lab.local` dans le navigateur, tu vois la page MES
avec le nom du pod qui répond.

**Exercice rollback** : change `api.version`, `helm upgrade`, puis
`helm rollback mes 1 -n mes-dev` et `helm history mes -n mes-dev`.

Désinstalle pour laisser la place à Argo CD : `helm uninstall mes -n mes-dev`.

---

## Phase 2 — Argo CD (GitOps)

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl get pods -n argocd -w

# mot de passe admin
kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d; echo
# UI (terminal dédié)
kubectl port-forward svc/argocd-server -n argocd 8080:443
```

Déclare les applications :

```bash
kubectl apply -f argocd/app-dev.yaml    # sync auto
kubectl apply -f argocd/app-prod.yaml   # sync manuel (promotion contrôlée)
```

**Geste GitOps** : modifie `values-dev.yaml`, commit, push → Argo CD synchronise
seul. **Rollback** = `git revert` + push. **Self-heal** : `kubectl scale ...` à
la main → Argo CD ramène l'état de Git.

---

## Phase 3 — Haute disponibilité (le cœur de ta demande)

Synchronise `mes-platform-prod` dans l'UI. L'app prod tourne en 3 replicas avec
anti-affinité + PDB.

```bash
kubectl get pods -n mes-prod -o wide       # répartis sur agent1 et agent2
```

**Éprouve la résilience toi-même.** Terminal 1, trafic continu :

```bash
while true; do curl -s http://mes.lab.local/version | grep -o '"pod":"[^"]*"' || echo DOWN; sleep 1; done
```

Tu verras le champ `pod` changer : le load balancing répartit sur les 3 replicas.
Terminal 2, tue un nœud :

```bash
vagrant halt k3s-agent1 --force
```

Observe le terminal 1 : le service continue de répondre (les pods survivants
encaissent), et après ~30-60s les pods d'agent1 sont recréés sur agent2. **Aucun
DOWN prolongé = HA démontrée.** Rallume : `vagrant up k3s-agent1`.

Teste aussi le drain propre, protégé par le PDB :

```bash
kubectl drain k3s-agent2 --ignore-daemonsets --delete-emptydir-data
kubectl uncordon k3s-agent2
```

---

## Phase 4 — Ansible + AWX (automatisation pilotée par API)

Le pattern de ton futur poste : un déclencheur externe (chez Rolex, Control-M)
appelle l'API d'AAP qui lance un playbook de déploiement.

### 4a. Ansible en CLI d'abord (sur k3s-server)

```bash
# Sur k3s-server
sudo dnf install -y python3-pip
pip3 install kubernetes
ansible-galaxy collection install kubernetes.core
# clone le repo sur le server, puis :
ansible-playbook ansible/playbooks/deploy.yml -e env=dev
```

### 4b. AWX (déclencheur par API)

Suis **`docs/AWX.md`** : installation via operator, création du Job Template
pointant sur `ansible/playbooks/deploy.yml`, puis déclenchement par API avec :

```bash
./scripts/trigger-awx-job.sh <IP_AWX> <TEMPLATE_ID> admin <password>
```

Ce script simule ce que fera Control-M. C'est le maillon final de la chaîne.

---

## La démo complète (capstone)

1. Modifie `app/app.py`, commit, push → la CI build l'image
2. Bump le tag dans `values-dev.yaml`, push → Argo CD déploie en dev
3. Promeus en prod (SYNC manuel)
4. Casse la v2 (mauvais tag) → `git revert` → Argo CD rollback
5. Lance une boucle curl sur mes.lab.local, tue un nœud → le service tient
6. Déclenche un redéploiement via l'API AWX (le pattern Control-M)

Si tu déroules ça sans notes, tu es prêt pour le poste.

---

## Utiliser Claude Code sur ce projet

Le fichier `CLAUDE.md` à la racine donne tout le contexte à Claude Code (topologie,
IPs, pièges connus). Ouvre le dépôt avec `claude` et demande-lui d'ajouter des
composants (HPA, NetworkPolicy), de débugger un pod (`kubectl describe`/`logs`),
ou d'expliquer un template. Idéal pour le YAML verbeux et le diagnostic — mais
garde la main sur les gestes centraux, c'est toi qui apprends.

---

## Correspondance programme

| Phase | Outils | Bloc |
|-------|--------|------|
| 0-1 | Docker, GitHub Actions, Helm | CI + Helm côté auteur |
| 2 | Argo CD | GitOps |
| 3 | MetalLB, anti-affinité, PDB | Load balancing + HA |
| 4 | Ansible, AWX, API | Pont automatisation (Control-M/AAP) |
