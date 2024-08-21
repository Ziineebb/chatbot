import os
import openai
import mysql.connector

# Configuration de la clé API OpenAI
openai.api_key = "key"

# Configuration de la connexion MySQL
db_config = {
    'user': 'root',
    'password': 'mdps',  # Entrer le mot de passe
    'host': 'localhost',
    'database': 'telecom_assistant',
}

# Connexion à la base de données MySQL
conn = mysql.connector.connect(**db_config)
cursor = conn.cursor()

# Fonction pour insérer les offres si elles n'existent pas
def insert_offers():
    offers_data = [
        ("Forfait Illimité", "Appels illimités vers tous les réseaux, 50 Go de data.", "200 DH/mois"),
        ("Forfait International", "Appels vers l'international à tarif réduit, 10 Go de data.", "300 DH/mois"),
        ("Forfait Jeunes", "10 Go de data, SMS illimités.", "100 DH/mois"),
        ("Forfait Famille", "Partage de 100 Go de data, appels gratuits entre membres de la famille.", "500 DH/mois")
    ]
    cursor.execute('DELETE FROM offers')
    cursor.executemany('INSERT IGNORE INTO offers (name, description, price) VALUES (%s, %s, %s)', offers_data)
    conn.commit()

# Fonction pour récupérer les messages commencant par qst
def getquestion():
    query = '''
                SELECT DISTINCT content
                FROM messages
                WHERE role = "user"
                LIMIT 50;
            '''
    cursor.execute(query)
    data = cursor.fetchall()
    simple_list = [item[0] for item in data]
    return simple_list

# Fonction pour récupérer les détails des offres depuis la base de données
def get_offer_details():
    cursor.execute('SELECT name, description, price FROM offers')
    return cursor.fetchall()

# Fonction pour insérer un message dans la base de données
def log_to_db(role, content):
    cursor.execute('INSERT INTO messages (role, content) VALUES (%s, %s)', (role, content))
    conn.commit()

# Fonction de requête OpenAI
def Chat(user_messages) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=user_messages,
    )
    return response.choices[0].message['content']

# Liste pour stocker l'historique des messages
message_history = []

# Fonction pour démarrer le chat
def startChat(user_message):
    insert_offers()  # Initialiser les offres dans la base de données
    
    global message_history
    
    # Ajouter le message utilisateur à l'historique
    message_history.append({"role": "user", "content": user_message})
    
    # Limiter l'historique aux 10 derniers messages
    if len(message_history) > 10:
        message_history = message_history[-10:]
    
    # Ajouter un message système au début si l'historique est vide
    if len(message_history) == 1:
        message_history.insert(0, {
            "role": "system", 
            "content": "Vous êtes un assistant de Maroc Telecom, vous pouvez uniquement répondre aux questions relatives aux offres de Maroc Telecom."
        })
    
    # Vérifier les mots-clés pour les offres et insérer les détails si nécessaire
    if any(word in user_message.lower() for word in ["tarifs", "détails", "offres", "offre", "tarif"]):
        offers = get_offer_details()
        if offers:
            response = "Voici les détails des offres de Maroc Telecom :\n" + "\n".join(
                f"Offre: {offer[0]}\nDescription: {offer[1]}\nPrix: {offer[2]}\n"
                for offer in offers
            )
        else:
            response = "Je n'ai pas d'informations sur les offres pour le moment."
        
        # Enregistrer la réponse dans l'historique
        message_history.append({"role": "assistant", "content": response})
        
        # Limiter l'historique aux 10 derniers messages
        if len(message_history) > 10:
            message_history = message_history[-10:]
        
        log_to_db('user', user_message)
        log_to_db('assistant', response)
        return response

    # Générer la réponse avec l'API OpenAI en utilisant l'historique
    result = Chat(message_history)
    
    # Ajouter la réponse du chatbot à l'historique
    message_history.append({"role": "assistant", "content": result})
    
    # Limiter l'historique aux 10 derniers messages
    if len(message_history) > 10:
        message_history = message_history[-10:]
    
    log_to_db('user', user_message)
    log_to_db('assistant', result)
    
    return result
