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
* Python 3.8 ou supérieur.
* Votre ID Steam : Trouvable dans les Détails de votre compte Steam en-dessous de votre pseudo.
* Une clé API CSFloat : Trouvable sur votre Profil > Développeurs > Nouvelle clé

### Étapes

1.  **Cloner le dépôt** :
    ```bash
    git clone https://github.com/Zabowar/Paffloat.git
    cd paffloat
    ```

2.  **Créer un environnement virtuel** :
    ```bash
    python -m venv venv
    # Sur Windows
    venv\Scripts\activate
    # Sur Linux/Mac
    source venv/bin/activate
    ```

3.  **Installer les dépendances** :
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configuration** :
    Dans le fichier `.env` à la racine du projet, ajoutez votre clé API CSFloat :
    ```text
    CSFLOAT_API_KEY=votre_cle_API
    ```
5. **Lancement** :
    ```bash
    uvicorn main:app --reload
    ```
L'interface sera alors accessible à l'adresse suivante : `http://127.0.0.1:8000`.

## Utilisation

Exécutez simplement le fichier lanceur.bat.

## Mise à jour

Supprimez le dossier Paffloat qui a été créé lors de l'installation puis entrez à nouveau les commandes d'installation.

⚠️ Cela supprime tous les prix entrés manuellement ainsi que votre clé d'API CS Float. Veillez à bien sauvegarder préalablement cette dernière pour ne pas avoir à en recréer une.

---

*Ce projet n'est pas affilié à Valve Corporation ou CSFloat.*
