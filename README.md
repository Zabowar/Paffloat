# Paffloat

Paffloat est une application web permettant de connaître la valeur des objets de son inventaire CS2 sur la plateforme CS Float.

## Fonctionnalités

* **Estimation CSFloat** : Récupération des prix moyens des objets similaires sur CSFloat avec conversion automatique USD/EUR en temps réel.
* **Calcul des bénéfices de votre inventaire**

## Limites

Les stickers présents sur les apparences d'armes ne sont pas pris en compte dans le prix affiché car leur influence sur la valeur de l'objet dépend de trop de facteurs spécifiques.

## Installation

### Prérequis
* Git
* Docker Desktop ou Docker Server
* Une clé API CSFloat : Trouvable sur Profil > Développeurs > Nouvelle clé

### Étapes

1.  **Cloner le dépôt** :
    ```bash
    git clone https://github.com/Zabowar/Paffloat.git
    cd paffloat
    ```
2.  **Configuration** :
    Dans le fichier `.env` à la racine du projet, ajoutez votre clé API CSFloat :
    ```text
    CSFLOAT_API_KEY=votre_cle_API
    ```
5. **Lancement** :
    ```bash
    docker compose up -d --build
    ```
L'interface sera alors accessible à l'adresse : `http://127.0.0.1:8000` ou sur l'IP de votre serveur.

## Utilisation

* Si vous utilisez Paffloat en local, exécutez le fichier lanceur.bat.
* Si Pafflot est sur un serveur, rendez vous simplement sur l'adresse de celui-ci.

## Mise à jour

Supprimez le dossier Paffloat qui a été créé lors de l'installation puis entrez à nouveau les commandes d'installation.

⚠️ Cela supprime tous les prix entrés manuellement ainsi que votre clé d'API CS Float. Veillez à bien sauvegarder préalablement cette dernière pour ne pas avoir à en recréer une.

---

*Ce projet n'est pas affilié à Valve ou à CSFloat.*
