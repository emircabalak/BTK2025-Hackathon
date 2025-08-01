import os
import json
import requests
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

prompts = {
    'tr': {
        'debate_system': "Sen bir münazara yapay zekasısın. Konu: '{topic}'. Senin görevin bu konuyu '{stance}' pozisyonundan savunmak. Kullanıcının argümanlarına mantıklı ve ikna edici karşı argümanlar sun.",
        'report_system': "Aşağıdaki münazara geçmişini analiz et ve JSON formatında bir performans raporu oluştur: {conversation_history}",
        'schema_system': "Aşağıdaki münazara geçmişine dayanarak mermaid.js formatında bir argüman haritası oluştur: {conversation_history}",
        'profile_system': "Aşağıdaki münazara özet verilerine dayanarak bir münazır profili analizi yap. Analizin şu alanları içermeli: en sık yapılan mantık hatası ve bu hatadan kaçınmak için bir tavsiye, genel münazara stili, en güçlü yönü ve geliştirilmesi gereken yönü. Yanıtını, sağlanan JSON şemasına tam olarak uyacak şekilde formatla: {summary_data}"
    },
    'en': {
        'debate_system': "You are a debate AI. The topic is: '{topic}'. Your role is to argue from the '{stance}' stance. Provide logical and persuasive counter-arguments to the user's points.",
        'report_system': "Analyze the following debate history and create a performance report in JSON format: {conversation_history}",
        'schema_system': "Create an argument map in mermaid.js format based on the following debate history: {conversation_history}",
        'profile_system': "Based on the following summary data, perform a debater profile analysis. The analysis must include: the most common logical fallacy with advice to avoid it, the overall debate style, the main strength, and the area for improvement. Format your response to exactly match the provided JSON schema: {summary_data}"
    }
}

db = SQLAlchemy()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///debate_arena.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    debates = db.relationship('Debate', backref='user', lazy=True)

class Debate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    report_data = db.Column(db.Text, nullable=False)
    schema_data = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_API_KEY_HERE")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"

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

@app.route('/api/debate', methods=['POST'])
def handle_debate():
    try:
        data = request.json
        lang = data.get('lang', 'tr')
        topic = data.get('topic')
        stance_key = data.get('stance')
        stance = "savunuyorum" if stance_key == "savunuyorum" else "karşı çıkıyorum"
        messages = data.get('messages', [])
        
        conversation_history = "\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
        system_prompt = prompts[lang]["debate_system"].format(topic=topic, stance=stance)
        full_prompt = f"{system_prompt}\n\n---SOHBET GEÇMİŞİ---\n{conversation_history}\n\nYapay Zeka Münazırının sıradaki yanıtı:"
        
        payload = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}]}
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if 'candidates' not in result or not result['candidates']:
            return jsonify({"reply": "Yanıt alınamadı. Güvenlik ayarları nedeniyle engellenmiş olabilir."}), 200

        reply = result['candidates'][0]['content']['parts'][0]['text']
        return jsonify({"reply": reply})
    except requests.exceptions.HTTPError as e:
        error_details = e.response.json()
        print(f"API Hatası: {error_details}")
        return jsonify({"error": f"API Hatası: {error_details.get('error', {}).get('message', str(e))}"}), 500
    except Exception as e:
        print(f"Sunucu Hatası: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/report', methods=['POST'])
def handle_report():
    try:
        data = request.json
        lang = data.get('lang', 'tr')
        messages = data.get('messages', [])
        topic = data.get('topic')
        conversation_history = "\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
        report_prompt = prompts[lang]["report_system"].format(conversation_history=conversation_history)
        
        payload = { "contents": [{"role": "user", "parts": [{"text": report_prompt}]}] }
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_json_string = response_text.strip().replace("```json", "").replace("```", "").strip()
        report_json = json.loads(cleaned_json_string)

        if 'user_id' in session:
            schema_prompt = prompts[lang]["schema_system"].format(conversation_history=conversation_history)
            schema_payload = { "contents": [{"role": "user", "parts": [{"text": schema_prompt}]}] }
            schema_response_req = requests.post(GEMINI_API_URL, json=schema_payload)
            schema_response_req.raise_for_status()
            schema_response_text = schema_response_req.json()['candidates'][0]['content']['parts'][0]['text']
            cleaned_schema_string = schema_response_text.strip().replace("```mermaid", "").replace("```", "").strip()
            schema_data = {"schema": cleaned_schema_string}

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
        conversation_history = "\n".join([f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
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
    debates = Debate.query.filter_by(user_id=user_id).order_by(Debate.timestamp.asc()).all()
    
    history_data = [
        {
            "id": debate.id,
            "topic": debate.topic,
            "timestamp": debate.timestamp.strftime("%d-%m-%Y"),
            "report": json.loads(debate.report_data),
            "schema": json.loads(debate.schema_data)
        } for debate in debates
    ]
    return jsonify(history_data)

@app.route('/api/profile', methods=['GET'])
def get_profile():
    if 'user_id' not in session:
        return jsonify({"error": "Giriş yapılmamış."}), 401

    user_id = session['user_id']
    debates = Debate.query.filter_by(user_id=user_id).all()

    if len(debates) < 3:
        return jsonify({"error": "Profil analizi için en az 3 münazara tamamlamanız gerekmektedir."}), 400

    scores = []
    fallacies = {}
    
    for debate in debates:
        report = json.loads(debate.report_data)
        scores.append(report.get('iknaEdicilikPuani', 0))
        fallacy = report.get('gelistirilmesiGerekenNokta', {}).get('tespitEdilenHataTuru')
        if fallacy:
            fallacies[fallacy] = fallacies.get(fallacy, 0) + 1

    summary_data = f"Puanlar: {scores}, En sık yapılan hatalar: {fallacies}"
    lang = request.args.get('lang', 'tr')
    
    profile_prompt = prompts[lang]["profile_system"].format(summary_data=summary_data)
    
    payload = {
        "contents": [{"role": "user", "parts": [{"text": profile_prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "enSikHata": {
                        "type": "OBJECT",
                        "properties": {
                            "hataTuru": {"type": "STRING"},
                            "tavsiye": {"type": "STRING"}
                        }
                    },
                    "munazaraStili": {"type": "STRING"},
                    "gucluYon": {"type": "STRING"},
                    "gelistirilecekYon": {"type": "STRING"}
                }
            }
        }
    }
    
    response = requests.post(GEMINI_API_URL, json=payload)
    response.raise_for_status()
    response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
    profile_analysis = json.loads(response_text)

    return jsonify(profile_analysis)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5000)
