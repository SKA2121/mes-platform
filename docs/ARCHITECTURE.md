# Architecture — MES Platform

## Vue d'ensemble : de l'URL au pod

```
                          TON POSTE WINDOWS
                     navigateur : http://mes.lab.local
                                  │
                    (résolution via fichier hosts Windows
                     mes.lab.local -> 192.168.56.200)
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────┐
        │   MetalLB attribue 192.168.56.200 à Traefik      │
        │   (répond à l'ARP : "c'est ce nœud qui a l'IP")  │
        └─────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────┐
        │   Traefik (Ingress) lit le hostname mes.lab.local│
        │   et route vers le Service mes-tracker-api       │
        └─────────────────────────────────────────────────┘
                                  │
                     ┌────────────┼────────────┐
                     ▼            ▼            ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ pod api  │ │ pod api  │ │ pod api  │   3 replicas
              │ agent1   │ │ agent2   │ │ agent1   │   (anti-affinité
              └──────────┘ └──────────┘ └──────────┘    + PDB)
                     └────────────┼────────────┘
                                  ▼
                        ┌──────────────────┐
                        │ Service postgres │
                        │  (StatefulSet)   │
                        │  PVC sur NFS     │
                        └──────────────────┘
```

## La chaîne de livraison (CI/CD/GitOps)

```
  Développeur                GitHub                    Cluster k3s
  ───────────                ──────                    ───────────
  git push app/  ──────►  GitHub Actions
                          build image Docker
                          push vers GHCR ──────┐
                                               │
  git push helm/ ──────►  (repo = source        │
                           de vérité)            │
                              │                  │
                              ▼                  ▼
                          Argo CD  ◄──── surveille le repo
                          détecte l'écart
                          synchronise ──────►  déploie le chart Helm
                                               (namespace mes-dev/prod)
```

## L'automatisation (AAP/AWX + Ansible)

```
  AWX (sur le cluster)                    Control node (k3s-server)
  ────────────────────                    ─────────────────────────
  Job Template "deploy-mes"
        │
   déclenché par :
   - clic UI, OU
   - API REST  ◄──── (chez Rolex : Control-M appelle cette API)
        │
        ▼
   exécute le playbook Ansible ──────►  kubernetes.core.helm
                                        déploie/met à jour le chart
```

## Les briques et leur rôle

| Brique | Rôle dans le projet |
|--------|---------------------|
| **k3s** | Le cluster : orchestre les conteneurs sur 3 nœuds |
| **MetalLB** | Donne une IP réseau à Traefik (load balancer on-prem) |
| **Traefik (Ingress)** | Route le trafic HTTP par hostname vers les services |
| **Helm** | Package l'application (API + PostgreSQL + Ingress + HA) |
| **GitHub Actions** | Construit l'image Docker et la pousse (CI) |
| **Argo CD** | Déploie depuis Git, maintient l'état (GitOps) |
| **NFS StorageClass** | Stockage persistant pour PostgreSQL |
| **Ansible** | Automatise le déploiement (playbooks) |
| **AWX (AAP)** | Exécute les playbooks, pilotable par API (comme Control-M) |

## La haute disponibilité, éprouvée

Trois mécanismes se combinent :
1. **Réplication** : 3 pods API répartis sur les nœuds.
2. **Anti-affinité** : le scheduler évite de mettre 2 pods API sur le même nœud.
3. **PodDisruptionBudget** : garantit un minimum de pods pendant les maintenances.

Tu l'éprouves toi-même (voir README, phase HA) : une boucle curl continue sur
mes.lab.local pendant que tu tues un nœud (`vagrant halt k3s-agent1 --force`).
Le service doit rester disponible — c'est TA démonstration de résilience.
