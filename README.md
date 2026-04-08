<div align="center">
    <img src="static/favicon.svg" alt="Paffloat Logo" width="200"/>
    <h1>Paffloat</h1>
    <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" alt="Python">
    <img src="https://img.shields.io/badge/FastAPI-005571?style=flat&logo=fastapi" alt="FastAPI">
    <img src="https://img.shields.io/badge/SQLite-07405E?style=flat&logo=sqlite&logoColor=white" alt="SQLite">
    <img src="https://img.shields.io/badge/HTMX-336699?style=flat&logo=htmx&logoColor=white" alt="HTMX">
    <img src="https://img.shields.io/badge/Alpine.js-8BC0D0?style=flat&logo=alpine.js&logoColor=white" alt="Alpine.js">
    <img src="https://img.shields.io/badge/Jinja-B41717?style=flat&logo=jinja&logoColor=white" alt="Jinja">
    <img src="https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white" alt="Docker">
</div>

<br>

**Paffloat** est une application web permettant d'estimer et de suivre la valeur de votre inventaire *Counter-Strike 2* en se basant sur les données de la plateforme **CSFloat**.

---

## ✨ Fonctionnalités

* **Authentification Steam sécurisée** : Connectez-vous directement via Steam OpenID pour récupérer votre inventaire.
* **Estimation CSFloat en direct** : Récupération des prix moyens des objets similaires sur CSFloat.
* **Conversion dynamique** : Conversion automatique des prix USD vers EUR en temps réel.
* **Calcul de rentabilité** : Suivez vos prix d'achat, calculez vos bénéfices (ROI) et la valeur totale de votre inventaire.
* **Gestion avancée des lots** : Prise en charge des objets empilables (caisses, capsules, stickers) avec possibilité d'assigner différents prix d'achat par lot.
* **Interface réactive** : Tri et filtrage instantanés (par bénéfice, prix, float, catégorie) pour analyser facilement vos investissements.

## ⚠️ Limite

* **Stickers appliqués** : Les stickers présents sur les armes ne sont pas pris en compte dans le prix affiché, car leur influence sur la valeur finale dépend de trop de facteurs spécifiques au marché.

---

## 🚀 Installation

### Prérequis

* **Git**.
* **Docker** (Docker Desktop ou Docker Server).
* **Clé API CSFloat** : Récupérable sur CSFloat dans `Profil > Développeurs > Nouvelle clé`.

### Étapes d'installation

1. **Cloner le dépôt** :
   ```bash
   git clone https://github.com/Zabowar/Paffloat.git
   cd paffloat

2. **Configuration** :
   Créez ou modifiez le fichier `.env` à la racine du projet et ajoutez-y votre clé API CSFloat :
   ```env
   CSFLOAT_API_KEY=votre_cle_API_ici
   ```

3. **Lancement via Docker** :
   ```bash
   docker compose up -d --build
   ```

L'interface sera alors accessible depuis votre navigateur à l'adresse : **`http://127.0.0.1:8000`** (ou sur l'adresse IP de votre serveur).

---

## 💻 Utilisation

* **Utilisation locale (Windows)** : Double-cliquez simplement sur le fichier `lanceur.bat` fourni à la racine. Il démarrera le serveur Docker et ouvrira la page automatiquement dans votre navigateur.
* **Utilisation sur un serveur** : Accédez simplement à l'IP locale ou publique de votre serveur.

---

## 🔄 Mise à jour

### Méthode recommandée (Sans perte de données)
Pour mettre à jour Paffloat **sans perdre** vos prix d'achat saisis manuellement, ouvrez un terminal dans le dossier `Paffloat` et exécutez :
```bash
git pull
docker compose up -d --build
```

### Méthode de réinstallation complète ⚠️
Si vous préférez supprimer le dossier Paffloat et tout recommencer, **pensez à sauvegarder votre fichier `.env` ainsi que le dossier `data/`** avant de supprimer le dossier principal. Le dossier `data/` contient votre base de données (`paffloat.db`) avec tous les prix d'achat que vous avez saisis. Si vous ne le sauvegardez pas, votre historique sera perdu !

---

Ce projet n'est en aucun cas affilié, associé, autorisé ou approuvé par Valve ou CSFloat.*
