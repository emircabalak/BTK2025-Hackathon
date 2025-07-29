import os
import json
import requests
from flask import Flask, request, jsonify, render_template, session
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from prompts import prompts
from database import db # Yeni database.py dosyasından db nesnesini import et

# --- FLASK UYGULAMASINI BAŞLATMA ---
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///debate_arena.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Veritabanını uygulama ile ilişkilendir
db.init_app(app)
migrate = Migrate(app, db)

# DÜZELTME: Import işlemini, db nesnesi tanımlandıktan sonra yapıyoruz.
from models import User, Debate 

# --- GEMINI API AYARLARI ---
API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# --- ANA SAYFA VE KULLANICI İŞLEMLERİ ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Kullanıcı adı ve şifre gerekli."}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Bu kullanıcı adı zaten alınmış."}), 409

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Kullanıcı başarıyla oluşturuldu."}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        session['username'] = user.username
        return jsonify({"message": "Giriş başarılı.", "username": user.username}), 200

    return jsonify({"error": "Geçersiz kullanıcı adı veya şifre."}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return jsonify({"message": "Çıkış başarılı."}), 200

@app.route('/api/status', methods=['GET'])
def status():
    if 'user_id' in session:
        return jsonify({"logged_in": True, "username": session.get('username')})
    return jsonify({"logged_in": False})

# --- MÜNAZARA VE RAPOR İŞLEMLERİ ---
@app.route('/api/debate', methods=['POST'])
def handle_debate():
    try:
        data = request.json
        lang = data.get('lang', 'tr')
        topic = data.get('topic')
        stance_key = data.get('stance')
        stance = "for" if stance_key == "savunuyorum" else "against"
        messages = data.get('messages', [])
        conversation_history = "\\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
        
        system_prompt = prompts[lang]["debate_system"].format(topic=topic, stance=stance)
        full_prompt = f"{system_prompt}\\n\\n---CHAT HISTORY---\\n{conversation_history}\\n\\nAI Debater's next response:"
        
        payload = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}]}
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        reply = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": reply})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/report', methods=['POST'])
def handle_report():
    try:
        data = request.json
        lang = data.get('lang', 'tr')
        messages = data.get('messages', [])
        topic = data.get('topic')
        conversation_history = "\\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
        report_prompt = prompts[lang]["report_system"].format(conversation_history=conversation_history)
        
        payload = { "contents": [{"role": "user", "parts": [{"text": report_prompt}]}] }
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_json_string = response_text.strip().replace("```json", "").replace("```", "").strip()
        report_json = json.loads(cleaned_json_string)

        if 'user_id' in session:
            schema_response = requests.post(f"{request.url_root}api/schema", json=data)
            schema_data = schema_response.json()
            
            new_debate = Debate(
                user_id=session['user_id'],
                topic=topic,
                report_data=json.dumps(report_json),
                schema_data=json.dumps(schema_data)
            )
            db.session.add(new_debate)
            db.session.commit()

        return jsonify(report_json)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/schema', methods=['POST'])
def handle_schema():
    try:
        data = request.json
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/history', methods=['GET'])
def get_history():
    if 'user_id' not in session:
        return jsonify({"error": "Giriş yapılmamış."}), 401
    
    user_id = session['user_id']
    debates = Debate.query.filter_by(user_id=user_id).order_by(Debate.timestamp.desc()).all()
    
    history_data = [
        {
            "id": debate.id,
            "topic": debate.topic,
            "timestamp": debate.timestamp.strftime("%d-%m-%Y %H:%M"),
            "report": json.loads(debate.report_data),
            "schema": json.loads(debate.schema_data)
        } for debate in debates
    ]
    return jsonify(history_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
