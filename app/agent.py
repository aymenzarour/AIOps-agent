import os
import google.generativeai as genai
import requests
from kubernetes import client, config, watch

try:
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    TELEGRAM_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    TELEGRAM_CHAT_ID = os.environ['TELEGRAM_CHAT_ID']
except KeyError:
    print("Erreur: Les variables d'environnement ne sont pas définies!")
    exit(1)

print("--- Recherche de modèles Gemini compatibles (v7)... ---")
available_model_name = None
preferred_models = ['models/gemini-1.5-flash', 'models/gemini-1.0-pro']

try:
    genai.configure(api_key=GEMINI_API_KEY)
    all_models = list(genai.list_models())
    
    for model_name in preferred_models:
        for m in all_models:
            if m.name == model_name and 'generateContent' in m.supported_generation_methods:
                available_model_name = m.name
                break
        if available_model_name:
            break
    
    if not available_model_name:
        for m in all_models:
            if 'pro' in m.name and 'exp' not in m.name and 'generateContent' in m.supported_generation_methods:
                available_model_name = m.name
                break

    if not available_model_name:
        for m in all_models:
            if 'flash' in m.name and 'exp' not in m.name and 'generateContent' in m.supported_generation_methods:
                available_model_name = m.name
                break

    if not available_model_name:
        print("Erreur: Aucun modèle compatible 'generateContent' n'a été trouvé.")
        exit(1)
        
    print(f"--- Modèle sélectionné (v7): {available_model_name} ---")
    gemini_model = genai.GenerativeModel(available_model_name)

except Exception as e:
    print(f"Erreur grave lors de la connexion à l'API Gemini pour lister les modèles: {e}")
    exit(1)


def get_ai_analysis(pod_name, namespace, event_reason, event_message):
    print(f"Demande d'analyse à Gemini pour le pod {pod_name}...")
    
    # --- PROMPT SIMPLIFIÉ ---
    prompt = f"""
    Contexte: Je suis un agent AIOps K3s. Sois très concis (2 phrases maximum).
    Problème Détecté: Le pod '{pod_name}' ({namespace}) a l'événement '{event_reason}' avec le message: "{event_message}".
    
    Tâche:
    1.  Explique le problème en une seule phrase très simple.
    2.  Donne UNIQUEMENT la commande kubectl la plus importante pour enquêter.

    Format de réponse attendu (Markdown):
    **Analyse Simple** : [Ton explication en 1 phrase]
    **Diagnostic** : `[Ta commande kubectl]`
    """
    
    try:
        response = gemini_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Erreur lors de l'appel à Gemini: {e}")
        return f"Erreur de l'IA: {e}" 

def send_telegram_message(message_text):
    print("Envoi du message à Telegram...")
    api_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': message_text,
        'parse_mode': 'Markdown'
    }
    try:
        requests.post(api_url, json=payload)
    except Exception as e:
        print(f"Erreur lors de l'envoi à Telegram: {e}")



already_reported_cache = set()

def watch_k8s_events():
    config.load_incluster_config() 
    v1 = client.CoreV1Api()
    
    print("Démarrage de la surveillance des événements K3s...")
    w = watch.Watch()
    
    for event in w.stream(v1.list_event_for_all_namespaces):
        event_type = event['type']
        event_obj = event['object']
        
        if event_type == "ADDED" and event_obj.type == "Warning":
            common_problems = [
                "Failed", "BackOff", "CrashLoopBackOff", 
                "FailedScheduling", "ImagePullBackOff", "OOMKilled"
            ]
            
            if any(problem in event_obj.reason for problem in common_problems):
                pod_name = event_obj.involved_object.name
                namespace = event_obj.involved_object.namespace
                reason = event_obj.reason
                message = event_obj.message
                
                
                problem_key = f"{namespace}/{pod_name}/{reason}"
                
                if problem_key in already_reported_cache:
                    print(f"--- Problème ({reason}) sur {pod_name} déjà signalé. Ignoré. ---")
                    continue # On ignore cet événement

                print(f"--- Problème Détecté ({reason}) sur {namespace}/{pod_name} ---")
                
                analysis = get_ai_analysis(pod_name, namespace, reason, message)
                
                final_message = f"🚨 **Alerte AIOps K3s** 🚨\n\n" \
                                f"**Pod**: `{namespace}/{pod_name}`\n" \
                                f"**Raison**: `{reason}`\n\n" \
                                f"--- Analyse Gemini (Simple) ---\n" \
                                f"{analysis}"
                
                send_telegram_message(final_message)
                
                already_reported_cache.add(problem_key)
                print("--------------------------------------------------")

if __name__ == "__main__":
    watch_k8s_events()