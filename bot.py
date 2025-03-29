import os
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from dotenv import load_dotenv
import sqlite3
from datetime import datetime, timedelta
import aiohttp
import asyncio
import traceback

# Configuration du logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Chargement des variables d'environnement
load_dotenv()
TOKEN = os.getenv('TELEGRAM_TOKEN')
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_IDS', '').split(',') if id]

# Configuration des raretés
RARITIES = {
    1: {"name": "⚪️ Commun", "chance": 50},
    2: {"name": "🟣 Rare", "chance": 30},
    3: {"name": "🟡 Légendaire", "chance": 15},
    4: {"name": "🟢 Ultra Rare", "chance": 5}
}

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    # Table des personnages
    c.execute('''CREATE TABLE IF NOT EXISTS characters
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  anime TEXT NOT NULL,
                  image_url TEXT NOT NULL,
                  rarity INTEGER NOT NULL,
                  added_by INTEGER NOT NULL,
                  added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Table des collections des utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS user_collections
                 (user_id INTEGER NOT NULL,
                  character_id INTEGER NOT NULL,
                  obtained_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (user_id, character_id),
                  FOREIGN KEY (character_id) REFERENCES characters(id))''')
    
    # Table des statistiques des utilisateurs
    c.execute('''CREATE TABLE IF NOT EXISTS user_stats
                 (user_id INTEGER PRIMARY KEY,
                  total_hunts INTEGER DEFAULT 0,
                  successful_hunts INTEGER DEFAULT 0,
                  last_hunt TIMESTAMP,
                  coins INTEGER DEFAULT 0,
                  last_daily TIMESTAMP)''')
    
    # Table des échanges en cours
    c.execute('''CREATE TABLE IF NOT EXISTS active_trades
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user1_id INTEGER NOT NULL,
                  user2_id INTEGER NOT NULL,
                  character1_id INTEGER NOT NULL,
                  character2_id INTEGER NOT NULL,
                  status TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    conn.commit()
    conn.close()

async def get_character_image(image_url: str) -> bytes:
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as response:
            return await response.read()

async def hunt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    # Vérifier le cooldown de la chasse
    c.execute('SELECT last_hunt FROM user_stats WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    
    if result and result[0]:
        last_hunt = datetime.fromisoformat(result[0])
        if (datetime.now() - last_hunt).total_seconds() < 300:  # 5 minutes de cooldown
            remaining_time = 300 - (datetime.now() - last_hunt).total_seconds()
            await update.message.reply_text(f"⏳ Tu dois attendre encore {int(remaining_time)} secondes avant de pouvoir chasser à nouveau!")
            conn.close()
            return
    
    # Sélectionner un personnage aléatoire
    c.execute('SELECT * FROM characters ORDER BY RANDOM() LIMIT 1')
    character = c.fetchone()
    
    if not character:
        await update.message.reply_text("❌ Aucun personnage disponible pour la chasse!")
        conn.close()
        return
    
    # Déterminer la rareté
    rarity_roll = random.randint(1, 100)
    current_sum = 0
    selected_rarity = 1
    
    for rarity, info in RARITIES.items():
        current_sum += info["chance"]
        if rarity_roll <= current_sum:
            selected_rarity = rarity
            break
    
    # Créer le message avec l'image
    message = (
        f"🎯 Un personnage apparaît!\n\n"
        f"Nom: {character[1]}\n"
        f"Anime: {character[2]}\n"
        f"Rareté: {RARITIES[selected_rarity]['name']}\n\n"
        "Veux-tu essayer de l'attraper?"
    )
    
    keyboard = [
        [InlineKeyboardButton("🎯 Attraper", callback_data=f"catch_{character[0]}_{selected_rarity}")],
        [InlineKeyboardButton("❌ Laisser partir", callback_data="release")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        image_data = await get_character_image(character[3])
        await update.message.reply_photo(
            photo=image_data,
            caption=message,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Erreur lors du chargement de l'image: {e}")
        await update.message.reply_text(message, reply_markup=reply_markup)
    
    conn.close()

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "release":
        await query.edit_message_text("❌ Le personnage s'est échappé!")
        return
    
    if query.data.startswith("catch_"):
        _, character_id, rarity = query.data.split("_")
        user_id = query.from_user.id
        
        conn = sqlite3.connect('anime_play.db')
        c = conn.cursor()
        
        # Vérifier si l'utilisateur a déjà ce personnage
        c.execute('SELECT 1 FROM user_collections WHERE user_id = ? AND character_id = ?', 
                 (user_id, character_id))
        if c.fetchone():
            await query.edit_message_text("❌ Tu as déjà ce personnage dans ta collection!")
            conn.close()
            return
        
        # Calculer la chance de capture
        base_chance = RARITIES[int(rarity)]["chance"]
        success = random.randint(1, 100) <= base_chance
        
        if success:
            # Ajouter à la collection
            c.execute('INSERT INTO user_collections (user_id, character_id) VALUES (?, ?)',
                     (user_id, character_id))
            
            # Mettre à jour les statistiques
            c.execute('''INSERT INTO user_stats (user_id, total_hunts, successful_hunts, last_hunt)
                        VALUES (?, 1, 1, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                        total_hunts = total_hunts + 1,
                        successful_hunts = successful_hunts + 1,
                        last_hunt = ?''',
                     (user_id, datetime.now().isoformat(), datetime.now().isoformat()))
            
            await query.edit_message_text(
                f"🎉 Félicitations! Tu as attrapé {character_id}!\n"
                f"Rareté: {RARITIES[int(rarity)]['name']}"
            )
        else:
            # Mettre à jour uniquement les statistiques
            c.execute('''INSERT INTO user_stats (user_id, total_hunts, last_hunt)
                        VALUES (?, 1, ?)
                        ON CONFLICT(user_id) DO UPDATE SET
                        total_hunts = total_hunts + 1,
                        last_hunt = ?''',
                     (user_id, datetime.now().isoformat(), datetime.now().isoformat()))
            
            await query.edit_message_text("❌ Le personnage s'est échappé!")
        
        conn.commit()
        conn.close()
    
    if query.data.startswith("trade_select_"):
        character_id = query.data.split("_")[2]
        user_id = query.from_user.id
        
        conn = sqlite3.connect('anime_play.db')
        c = conn.cursor()
        
        # Stocker la sélection dans le contexte
        context.user_data['trade_character_id'] = character_id
        
        # Demander l'utilisateur avec qui échanger
        await query.edit_message_text(
            "👥 Mentionne l'utilisateur avec qui tu veux échanger:\n"
            "Exemple: @username"
        )
        conn.close()

async def collection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    # Récupérer la collection de l'utilisateur
    c.execute('''
        SELECT c.name, c.anime, c.image_url, c.rarity, uc.obtained_date
        FROM user_collections uc
        JOIN characters c ON uc.character_id = c.id
        WHERE uc.user_id = ?
        ORDER BY c.rarity DESC, uc.obtained_date DESC
    ''', (user_id,))
    
    characters = c.fetchall()
    
    if not characters:
        await update.message.reply_text("📚 Ta collection est vide! Utilise /hunt pour commencer à chasser!")
        conn.close()
        return
    
    # Créer le message de la collection
    message = "📚 Ta Collection:\n\n"
    for char in characters:
        message += f"• {char[0]} ({char[1]}) - {RARITIES[char[3]]['name']}\n"
    
    # Ajouter les statistiques
    c.execute('SELECT total_hunts, successful_hunts FROM user_stats WHERE user_id = ?', (user_id,))
    stats = c.fetchone()
    if stats:
        message += f"\n🎯 Statistiques:\n"
        message += f"Total des chasses: {stats[0]}\n"
        message += f"Chasses réussies: {stats[1]}\n"
        message += f"Taux de réussite: {(stats[1]/stats[0]*100):.1f}%"
    
    await update.message.reply_text(message)
    conn.close()

# Commandes du bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    welcome_message = (
        f"👋 Bienvenue {user.first_name} dans ANIME PLAY!\n\n"
        "🎮 Commandes disponibles:\n"
        "/hunt - Chasser un personnage\n"
        "/collection - Voir ta collection\n"
        "/trade - Échanger des personnages\n"
        "/gift - Offrir un personnage\n"
        "/top - Classement des meilleurs chasseurs\n"
        "/daily - Réclamer ta récompense quotidienne"
    )
    await update.message.reply_text(welcome_message)

async def trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    # Vérifier si l'utilisateur a des personnages à échanger
    c.execute('''
        SELECT c.id, c.name, c.anime, c.rarity
        FROM user_collections uc
        JOIN characters c ON uc.character_id = c.id
        WHERE uc.user_id = ?
    ''', (user_id,))
    
    characters = c.fetchall()
    
    if not characters:
        await update.message.reply_text("❌ Tu n'as pas de personnages à échanger!")
        conn.close()
        return
    
    # Créer le message avec la liste des personnages
    message = "🎮 Sélectionne un personnage à échanger:\n\n"
    keyboard = []
    
    for char in characters:
        message += f"• {char[1]} ({char[2]}) - {RARITIES[char[3]]['name']}\n"
        keyboard.append([InlineKeyboardButton(
            f"{char[1]} ({RARITIES[char[3]]['name']})",
            callback_data=f"trade_select_{char[0]}"
        )])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(message, reply_markup=reply_markup)
    conn.close()

async def gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "❌ Usage: /gift @username character_id\n"
            "Exemple: /gift @user 123"
        )
        return
    
    if len(context.args) != 2:
        await update.message.reply_text("❌ Format incorrect! Utilise: /gift @username character_id")
        return
    
    target_username = context.args[0].replace("@", "")
    character_id = context.args[1]
    
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    # Vérifier si le personnage appartient à l'utilisateur
    c.execute('''
        SELECT c.name, c.anime, c.rarity
        FROM user_collections uc
        JOIN characters c ON uc.character_id = c.id
        WHERE uc.user_id = ? AND uc.character_id = ?
    ''', (update.effective_user.id, character_id))
    
    character = c.fetchone()
    if not character:
        await update.message.reply_text("❌ Tu ne possèdes pas ce personnage!")
        conn.close()
        return
    
    # Vérifier si l'utilisateur cible existe
    c.execute('SELECT id FROM user_stats WHERE user_id = ?', (target_username,))
    target_user = c.fetchone()
    if not target_user:
        await update.message.reply_text("❌ Utilisateur non trouvé!")
        conn.close()
        return
    
    # Transférer le personnage
    c.execute('''
        DELETE FROM user_collections 
        WHERE user_id = ? AND character_id = ?
    ''', (update.effective_user.id, character_id))
    
    c.execute('''
        INSERT INTO user_collections (user_id, character_id)
        VALUES (?, ?)
    ''', (target_user[0], character_id))
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"🎁 Tu as offert {character[0]} ({character[1]}) - {RARITIES[character[2]]['name']} à @{target_username}!"
    )

async def top(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    # Récupérer le top 10 des chasseurs
    c.execute('''
        SELECT us.user_id, us.successful_hunts, us.total_hunts,
               COUNT(DISTINCT uc.character_id) as collection_size
        FROM user_stats us
        LEFT JOIN user_collections uc ON us.user_id = uc.user_id
        GROUP BY us.user_id
        ORDER BY us.successful_hunts DESC
        LIMIT 10
    ''')
    
    top_users = c.fetchall()
    
    if not top_users:
        await update.message.reply_text("📊 Aucun classement disponible pour le moment!")
        conn.close()
        return
    
    message = "🏆 Top 10 des Meilleurs Chasseurs:\n\n"
    for i, user in enumerate(top_users, 1):
        success_rate = (user[1] / user[2] * 100) if user[2] > 0 else 0
        message += (
            f"{i}. Chasseur #{user[0]}\n"
            f"   🎯 Chasses réussies: {user[1]}\n"
            f"   📊 Taux de réussite: {success_rate:.1f}%\n"
            f"   📚 Collection: {user[3]} personnages\n\n"
        )
    
    await update.message.reply_text(message)
    conn.close()

async def daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    # Vérifier la dernière récompense quotidienne
    c.execute('SELECT last_daily FROM user_stats WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    
    if result and result[0]:
        last_daily = datetime.fromisoformat(result[0])
        if datetime.now() - last_daily < timedelta(days=1):
            next_daily = last_daily + timedelta(days=1)
            remaining_time = next_daily - datetime.now()
            hours = int(remaining_time.total_seconds() // 3600)
            minutes = int((remaining_time.total_seconds() % 3600) // 60)
            await update.message.reply_text(
                f"⏳ Tu dois attendre encore {hours}h {minutes}m avant ta prochaine récompense!"
            )
            conn.close()
            return
    
    # Donner la récompense
    coins = random.randint(100, 500)
    c.execute('''
        INSERT INTO user_stats (user_id, coins, last_daily)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
        coins = coins + ?,
        last_daily = ?
    ''', (user_id, coins, datetime.now().isoformat(), coins, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"🎁 Récompense quotidienne réclamée!\n"
        f"💰 Tu as reçu {coins} pièces!"
    )

async def add_character(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Cette commande est réservée aux administrateurs!")
        return
    
    if len(context.args) < 4:
        await update.message.reply_text(
            "❌ Usage: /add_character nom anime image_url rareté\n"
            "Exemple: /add_character Tanjiro Demon_Slayer https://example.com/tanjiro.jpg 3"
        )
        return
    
    name = context.args[0]
    anime = context.args[1]
    image_url = context.args[2]
    try:
        rarity = int(context.args[3])
        if rarity not in RARITIES:
            raise ValueError("Rareté invalide")
    except ValueError:
        await update.message.reply_text("❌ La rareté doit être un nombre entre 1 et 4!")
        return
    
    conn = sqlite3.connect('anime_play.db')
    c = conn.cursor()
    
    try:
        c.execute('''
            INSERT INTO characters (name, anime, image_url, rarity, added_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, anime, image_url, rarity, update.effective_user.id))
        
        conn.commit()
        await update.message.reply_text(
            f"✅ Personnage ajouté avec succès!\n"
            f"Nom: {name}\n"
            f"Anime: {anime}\n"
            f"Rareté: {RARITIES[rarity]['name']}"
        )
    except sqlite3.Error as e:
        logger.error(f"Erreur lors de l'ajout du personnage: {e}")
        await update.message.reply_text("❌ Une erreur est survenue lors de l'ajout du personnage!")
    finally:
        conn.close()

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error: {context.error}")
    logger.error(traceback.format_exc())
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ Une erreur est survenue. Veuillez réessayer plus tard."
        )

def main():
    # Initialisation de la base de données
    init_db()
    
    # Création de l'application
    application = Application.builder().token(TOKEN).build()

    # Ajout des handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("hunt", hunt))
    application.add_handler(CommandHandler("collection", collection))
    application.add_handler(CommandHandler("trade", trade))
    application.add_handler(CommandHandler("gift", gift))
    application.add_handler(CommandHandler("top", top))
    application.add_handler(CommandHandler("daily", daily))
    application.add_handler(CommandHandler("add_character", add_character))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Gestionnaire d'erreurs
    application.add_error_handler(error_handler)

    # Démarrage du bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main() 