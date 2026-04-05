# Paffloat

Paffloat est une application web permettant de connaître la valeur des objets de son inventaire CS2 sur la plateforme CS Float.

## Fonctionnalités

* **Estimation CSFloat** : Récupération des prix moyens des objets similaires sur CSFloat avec conversion automatique USD/EUR en temps réel.
* **Calcul des bénéfices de votre inventaire**

## Installation

### Prérequis
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

## Utilisation

Pour lancer l'application en mode développement :

```bash
uvicorn main:app --reload
```

L'interface sera alors accessible à l'adresse suivante : `http://127.0.0.1:8000`.

## Limites

Les stickers présents sur les apparences d'armes ne sont pas pris en compte dans le prix affiché car leur influence sur la valeur de l'objet dépend de trop de facteur spécifiques.

---

*Ce projet n'est pas affilié à Valve Corporation ou CSFloat.*
