# Contexte projet — MES Platform (pour Claude Code)

## Ce qu'est ce projet
Plateforme MES de démonstration déployée de bout en bout sur un cluster k3s
on-prem. Objectif pédagogique : maîtriser Kubernetes, Helm, Argo CD (GitOps),
GitHub Actions (CI), MetalLB (load balancing), et Ansible/AWX (automatisation)
pour un poste d'Ingénieur Middleware & Automation.

## Topologie de l'infrastructure (VMs Vagrant + VirtualBox)
- **k3s-server** — 192.168.56.10 — control plane k3s + control node Ansible
- **k3s-agent1** — 192.168.56.11 — worker
- **k3s-agent2** — 192.168.56.12 — worker
- Réseau host-only : 192.168.56.0/24
- Pilotage depuis un poste Windows (Git Bash / MobaXterm) via kubectl + kubeconfig

## Composants déjà en place
- k3s installé (server + 2 agents), interface réseau : enp0s8
- MetalLB : pool 192.168.56.200-220 (mode L2)
- Ingress : Traefik (fourni par k3s)
- StorageClass : nfs-client (serveur NFS sur k3s-server, /srv/nfs/k8s)
- firewalld actif, SELinux enforcing (Rocky Linux 9)

## Conventions
- Le pilotage kubectl/helm se fait DEPUIS le poste Windows (jamais dans les VMs)
- Ansible tourne DEPUIS k3s-server (control node), kubeconfig k3s en /etc/rancher/k3s/k3s.yaml
- Tout manifeste va dans Git ; rien d'impératif non tracé
- Namespaces : mes-dev (sync auto Argo CD), mes-prod (sync manuel)

## Pièges connus de ce lab
- Services k3s : `k3s` sur le server, `k3s-agent` sur les agents
- secure_path sudo sur Rocky : binaires /usr/local/bin non vus par sudo
- MobaXterm : passer KUBECONFIG en chemin Windows natif (C:\...) pas /drives/c/
- Le fichier hosts Windows ne gère pas les wildcards
