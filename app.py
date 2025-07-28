import os
import json
import requests
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from prompts import prompts # prompts.py dosyasından dil verilerini import et

# --- FLASK UYGULAMASINI BAŞLATMA ---
app = Flask(__name__)
load_dotenv()

# --- GEMINI API AYARLARI ---
API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# --- FLASK ROUTE'LARI (API ENDPOINTS) ---

@app.route('/')
def index():
    """Ana HTML sayfasını templates klasöründen render eder."""
    return render_template('index.html')

@app.route('/api/debate', methods=['POST'])
def handle_debate():
    """Kullanıcının mesajını alır ve AI cevabını oluşturur."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Geçersiz istek: JSON verisi bulunamadı."}), 400
            
        lang = data.get('lang', 'tr')
        topic = data.get('topic')
        stance_key = data.get('stance')
        stance = "for" if stance_key == "savunuyorum" else "against"
        messages = data.get('messages', [])

        conversation_history = "\\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])

        system_prompt_template = prompts[lang]["debate_system"]
        system_prompt = system_prompt_template.format(topic=topic, stance=stance)
        
        full_prompt = f"{system_prompt}\\n\\n---CHAT HISTORY---\\n{conversation_history}\\n\\nAI Debater's next response:"

        payload = {
            "contents": [{"role": "user", "parts": [{"text": full_prompt}]}]
        }
        
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        reply = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": reply})

    except requests.exceptions.HTTPError as http_err:
        error_info = http_err.response.json()
        return jsonify({"error": f"API Hatası: {error_info.get('error', {}).get('message', 'Bilinmeyen API hatası')}"}), http_err.response.status_code
    except Exception as e:
        return jsonify({"error": f"Sunucuda beklenmedik bir hata oluştu: {str(e)}"}), 500


@app.route('/api/report', methods=['POST'])
def handle_report():
    """Sohbet geçmişini alır ve performans raporu oluşturur."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Geçersiz istek: JSON verisi bulunamadı."}), 400

        lang = data.get('lang', 'tr')
        messages = data.get('messages', [])
        conversation_history = "\\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])

        report_prompt = prompts[lang]["report_system"].format(conversation_history=conversation_history)

        payload = { "contents": [{"role": "user", "parts": [{"text": report_prompt}]}] }
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_json_string = response_text.strip().replace("```json", "").replace("```", "").strip()
        report_json = json.loads(cleaned_json_string)
        return jsonify(report_json)

    except requests.exceptions.HTTPError as http_err:
        error_info = http_err.response.json()
        return jsonify({"error": f"API Hatası: {error_info.get('error', {}).get('message', 'Bilinmeyen API hatası')}"}), http_err.response.status_code
    except Exception as e:
        return jsonify({"error": f"Sunucuda beklenmedik bir hata oluştu: {str(e)}"}), 500

@app.route('/api/schema', methods=['POST'])
def handle_schema():
    """Sohbet geçmişini alır ve Mermaid.js formatında bir argüman haritası oluşturur."""
    try:
        data = request.json
        if not data:
            return jsonify({"error": "Geçersiz istek: JSON verisi bulunamadı."}), 400

        lang = data.get('lang', 'tr')
        messages = data.get('messages', [])
        conversation_history = "\\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])

        schema_prompt = prompts[lang]["schema_system"].format(conversation_history=conversation_history)

        payload = { "contents": [{"role": "user", "parts": [{"text": schema_prompt}]}] }
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_schema_string = response_text.strip().replace("```mermaid", "").replace("```", "").strip()
        
        return jsonify({"schema": cleaned_schema_string})

    except requests.exceptions.HTTPError as http_err:
        error_info = http_err.response.json()
        return jsonify({"error": f"API Hatası: {error_info.get('error', {}).get('message', 'Bilinmeyen API hatası')}"}), http_err.response.status_code
    except Exception as e:
        return jsonify({"error": f"Sunucuda beklenmedik bir hata oluştu: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
