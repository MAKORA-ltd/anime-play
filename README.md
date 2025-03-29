# ANIME PLAY Bot

Un bot Telegram pour collectionner des personnages d'anime avec des fonctionnalités avancées.

## 🚀 Fonctionnalités

- 🎯 Chasse de personnages d'anime
- 📚 Collection personnelle
- 💝 Système d'échange et de don
- 🏆 Classement des meilleurs chasseurs
- 🎁 Récompenses quotidiennes
- ⭐️ Système de rareté des personnages

## 🛠 Installation

### Installation Locale

1. Clonez ce dépôt :
```bash
git clone https://github.com/votre-username/anime-play-bot.git
cd anime-play-bot
```

2. Créez un environnement virtuel :
```bash
python -m venv venv
source venv/bin/activate  # Sur Windows: venv\Scripts\activate
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Configurez le fichier `.env` :
- Créez un fichier `.env` à la racine du projet
- Ajoutez votre token Telegram et votre ID admin :
```
TELEGRAM_TOKEN=votre_token_ici
ADMIN_IDS=votre_id_telegram
```

5. Lancez le bot :
```bash
python bot.py
```

### Déploiement Automatique avec Railway

Railway est une plateforme gratuite qui offre :
- 500 heures d'exécution par mois
- Déploiement automatique
- Base de données incluse
- Pas de configuration complexe

#### Configuration de Railway

1. Créez un compte sur [Railway](https://railway.app)

2. Créez un nouveau projet :
   - Cliquez sur "New Project"
   - Sélectionnez "Deploy from GitHub repo"
   - Choisissez ce dépôt

3. Configurez les variables d'environnement sur Railway :
   - `TELEGRAM_TOKEN`: Votre token Telegram
   - `ADMIN_IDS`: Votre ID Telegram admin

4. Obtenez votre token Railway :
   - Allez dans Account Settings > Developer Settings
   - Créez un nouveau token
   - Copiez le token

5. Configurez les secrets GitHub :
   - Allez dans votre dépôt GitHub > Settings > Secrets and variables > Actions
   - Ajoutez les secrets suivants :
     - `RAILWAY_TOKEN`: Votre token Railway
     - `TELEGRAM_TOKEN`: Votre token Telegram
     - `ADMIN_IDS`: Votre ID Telegram admin

6. Le déploiement se fera automatiquement à chaque push sur la branche `main`

## 📝 Commandes Disponibles

### Commandes Utilisateur
- `/start` - Démarrer le bot
- `/hunt` - Chasser un personnage
- `/collection` - Voir ta collection
- `/trade` - Échanger des personnages
- `/gift` - Offrir un personnage
- `/top` - Classement des meilleurs chasseurs
- `/daily` - Réclamer ta récompense quotidienne

### Commandes Admin
- `/add_character` - Ajouter un nouveau personnage
  Format: `/add_character nom anime image_url rareté`
  Exemple: `/add_character Tanjiro Demon_Slayer https://example.com/tanjiro.jpg 3`

## 🔒 Sécurité

- Les tokens sont stockés de manière sécurisée dans les variables d'environnement
- La base de données utilise SQLite pour un stockage local sécurisé
- Seuls les administrateurs peuvent ajouter des personnages

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésitez pas à :
1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 📞 Support

Pour toute question ou problème, n'hésitez pas à :
1. Ouvrir une issue sur GitHub
2. Nous contacter sur Telegram: @votre_username 