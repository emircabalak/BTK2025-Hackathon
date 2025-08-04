import os
import json
import requests
import time  # Hız limitini aşmamak için time modülünü ekliyoruz
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Prompts remain the same, focusing on specific output from the AI.
prompts = {
    'tr': {
        'debate_system': "Sen bir münazara yapay zekasısın. {personality_description} Konu: '{topic}'. Senin görevin bu konuyu '{stance}' pozisyonundan savunmak. Kullanıcının argümanlarına mantıklı ve ikna edici karşı argümanlar sun.",
        'report_system': "Aşağıdaki münazara geçmişini analiz et ve JSON formatında bir performans raporu oluştur: {conversation_history}",
        'schema_system': "Aşağıdaki münazara geçmişini analiz et ve SADECE mermaid.js formatında bir argüman haritası kodu çıktısı ver. Başka hiçbir açıklama veya metin ekleme. Çıktın doğrudan 'graph TD;' veya benzeri bir mermaid koduyla başlamalıdır. İşte geçmiş: {conversation_history}",
        'profile_system': "Aşağıdaki münazara özet verilerine dayanarak bir münazır profili analizi yap. Analizin şu alanları içermeli: en sık yapılan mantık hatası ve bu hatadan kaçınmak için bir tavsiye, genel münazara stili, en güçlü yönü ve geliştirilmesi gereken yönü. Yanıtını, sağlanan JSON şemasına tam olarak uyacak şekilde formatla: {summary_data}"
    },
    'en': {
        'debate_system': "You are a debate AI. {personality_description} The topic is: '{topic}'. Your role is to argue from the '{stance}' stance. Provide logical and persuasive counter-arguments to the user's points.",
        'report_system': "Analyze the following debate history and create a performance report in JSON format: {conversation_history}",
        'schema_system': "Analyze the following debate history and provide ONLY the argument map code in mermaid.js format. Do not add any other explanations or text. Your output should start directly with 'graph TD;' or similar mermaid code. Here is the history: {conversation_history}",
        'profile_system': "Based on the following summary data, perform a debater profile analysis. The analysis must include: the most common logical fallacy with advice to avoid it, the overall debate style, the main strength, and the area for improvement. Format your response to exactly match the provided JSON schema: {summary_data}"
    }
}

personalities = {
    'tr': {
        'standard': "Standart bir münazır gibi davran.",
        'academic': "Akademik bir dil kullan, argümanlarını bilimsel kanıtlara ve verilere dayandır.",
        'aggressive': "Agresif ve iddialı bir üslup benimse, karşı tarafın argümanlarındaki zayıf noktalara sert bir şekilde saldır.",
        'calm': "Sakin ve mantıklı bir şekilde konuş, duygusal tepkilerden kaçın ve soğukkanlılığını koru."
    },
    'en': {
        'standard': "Act like a standard debater.",
        'academic': "Use an academic tone, base your arguments on scientific evidence and data.",
        'aggressive': "Adopt an aggressive and assertive style, harshly attacking the weak points in the opponent's arguments.",
        'calm': "Speak in a calm and logical manner, avoid emotional reactions, and maintain your composure."
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
TTS_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key={API_KEY}"


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
        personality_key = data.get('personality', 'standard')

        personality_description = personalities[lang].get(personality_key, personalities[lang]['standard'])

        conversation_history = "\n".join(
            [f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
        system_prompt = prompts[lang]["debate_system"].format(
            topic=topic,
            stance=stance,
            personality_description=personality_description
        )
        full_prompt = f"{system_prompt}\n\n---SOHBET GEÇMİŞİ---\n{conversation_history}\n\nYapay Zeka Münazırının sıradaki yanıtı:"

        text_payload = {"contents": [{"role": "user", "parts": [{"text": full_prompt}]}]}
        text_response = requests.post(GEMINI_API_URL, json=text_payload)
        text_response.raise_for_status()
        result = text_response.json()

        if 'candidates' not in result or not result['candidates']:
            return jsonify({"reply": "Yanıt alınamadı. Güvenlik ayarları nedeniyle engellenmiş olabilir."}), 200

        reply_text = result['candidates'][0]['content']['parts'][0]['text']

        return jsonify({"reply": reply_text})

    except requests.exceptions.HTTPError as e:
        error_details = e.response.json()
        print(f"API Hatası: {error_details}")
        return jsonify({"error": f"API Hatası: {error_details.get('error', {}).get('message', str(e))}"}), 500
    except Exception as e:
        print(f"Sunucu Hatası: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/tts', methods=['POST'])
def handle_tts():
    try:
        data = request.json
        text_to_speak = data.get('text')
        if not text_to_speak:
            return jsonify({"error": "Metin gerekli."}), 400

        tts_payload = {
            "contents": [{"parts": [{"text": text_to_speak}]}],
            "generationConfig": {"responseModalities": ["AUDIO"]},
            "model": "gemini-2.5-flash-preview-tts"
        }

        tts_response = requests.post(TTS_API_URL, json=tts_payload)
        tts_response.raise_for_status()
        tts_result = tts_response.json()

        audio_part = tts_result['candidates'][0]['content']['parts'][0]
        audio_data = audio_part['inlineData']['data']
        mime_type = audio_part['inlineData']['mimeType']

        return jsonify({
            "audioData": audio_data,
            "mimeType": mime_type
        })
    except Exception as e:
        print(f"TTS Hatası: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/report', methods=['POST'])
def handle_report():
    try:
        data = request.json
        lang = data.get('lang', 'tr')
        messages = data.get('messages', [])
        topic = data.get('topic')
        conversation_history = "\n".join(
            [f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])

        # 1. Generate Report
        report_prompt = prompts[lang]["report_system"].format(conversation_history=conversation_history)
        report_payload = {
            "contents": [{"role": "user", "parts": [{"text": report_prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": {
                    "type": "OBJECT",
                    "properties": {
                        "iknaEdicilikPuani": {"type": "NUMBER"},
                        "enGucluArguman": {"type": "STRING"},
                        "gelistirilmesiGerekenNokta": {
                            "type": "OBJECT",
                            "properties": {
                                "tespitEdilenHataTuru": {"type": "STRING"},
                                "hataTanimi": {"type": "STRING"},
                                "ornekCumle": {"type": "STRING"},
                                "onerilenGelistirme": {"type": "STRING"}
                            }
                        },
                        "kanitKullanimi": {"type": "STRING"},
                        "genelYorum": {"type": "STRING"}
                    }
                }
            }
        }
        report_response = requests.post(GEMINI_API_URL, json=report_payload)
        report_response.raise_for_status()
        report_text = report_response.json()['candidates'][0]['content']['parts'][0]['text']
        report_json = json.loads(report_text)

        time.sleep(1)

        # 2. Generate Schema
        schema_prompt = prompts[lang]["schema_system"].format(conversation_history=conversation_history)
        schema_payload = {"contents": [{"role": "user", "parts": [{"text": schema_prompt}]}]}
        schema_response = requests.post(GEMINI_API_URL, json=schema_payload)
        schema_response.raise_for_status()
        schema_text = schema_response.json()['candidates'][0]['content']['parts'][0]['text']

        # --- MORE ROBUST CLEANING LOGIC ---
        cleaned_schema_string = schema_text.strip()

        if "```mermaid" in cleaned_schema_string:
            start = cleaned_schema_string.find("```mermaid") + len("```mermaid")
            end = cleaned_schema_string.rfind("```")
            if end > start:
                cleaned_schema_string = cleaned_schema_string[start:end].strip()
        elif "```" in cleaned_schema_string:
            start = cleaned_schema_string.find("```") + len("```")
            end = cleaned_schema_string.rfind("```")
            if end > start:
                cleaned_schema_string = cleaned_schema_string[start:end].strip()
        else:
            mermaid_keywords = ["graph", "flowchart", "sequenceDiagram", "gantt", "classDiagram", "stateDiagram"]
            start_index = -1
            for keyword in mermaid_keywords:
                index = cleaned_schema_string.find(keyword)
                if index != -1:
                    if start_index == -1 or index < start_index:
                        start_index = index

            if start_index != -1:
                cleaned_schema_string = cleaned_schema_string[start_index:]

        cleaned_schema_string = cleaned_schema_string.strip()
        schema_data = {"schema": cleaned_schema_string}

        # 3. Save to DB if user is logged in
        if 'user_id' in session:
            new_debate = Debate(
                user_id=session['user_id'],
                topic=topic,
                report_data=json.dumps(report_json),
                schema_data=json.dumps(schema_data)
            )
            db.session.add(new_debate)
            db.session.commit()

        # 4. Return both report and schema
        return jsonify({
            "report": report_json,
            "schema": schema_data
        })
    except Exception as e:
        print(f"Report/Schema Generation Error: {e}")
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