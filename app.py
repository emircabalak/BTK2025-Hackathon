import os
import json
import requests
from flask import Flask, request, jsonify, render_template, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# Initialize Flask app FIRST
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///debate_arena.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# API Configuration
API_KEY = os.getenv("GOOGLE_API_KEY", "AIzaSyDVeO8QiLTgSV9AbQedlMtSN7LFVd1BWK4")
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={API_KEY}"


# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    debates = db.relationship('Debate', backref='user', lazy=True)
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)
    learning_paths = db.relationship('LearningPath', backref='user', lazy=True)


class Debate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    report_data = db.Column(db.Text, nullable=False)
    schema_data = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class LearningTopic(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    questions = db.relationship('Question', backref='topic', lazy=True)


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic_id = db.Column(db.Integer, db.ForeignKey('learning_topic.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  # JSON array
    correct_answer = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(20), nullable=False)
    explanation = db.Column(db.Text)


class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('learning_topic.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    level = db.Column(db.String(20), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class LearningPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey('learning_topic.id'), nullable=False)
    roadmap_data = db.Column(db.Text, nullable=False)  # JSON
    progress = db.Column(db.Text, nullable=False, default='{}')  # JSON for task completion
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


# Prompts - FIXED: Separated learning prompts from debate prompts
prompts = {
    'tr': {
        'debate_system': "Sen bir münazara yapay zekasısın. Konu: '{topic}'. Senin görevin bu konuyu '{stance}' pozisyonundan savunmak. Kullanıcının argümanlarına mantıklı ve ikna edici karşı argümanlar sun.",
        'report_system': """Aşağıdaki münazara geçmişini analiz et ve JSON formatında bir performans raporu oluştur. 

        ÖNEMLİ: Sadece kullanıcının gerçekten söylediği cümleleri kullan. Hiçbir cümleyi uydurma veya değiştirme.

        Münazara Geçmişi:
        {conversation_history}

        Rapor formatı:
        {{
          "enGucluArguman": "Kullanıcının en güçlü argümanını özetle",
          "gelistirilmesiGerekenNokta": {{
            "tespitEdilenHataTuru": "Mantık hatası türü",
            "hataTanimi": "Hatanın açıklaması", 
            "ornekCumle": "Kullanıcının TAM OLARAK söylediği cümle - hiçbir değişiklik yapma",
            "onerilenGelistirme": "Somut geliştirme önerisi"
          }},
          "kanitKullanimi": "Kanıt kullanımı değerlendirmesi",
          "iknaEdicilikPuani": 7,
          "genelYorum": "Genel performans yorumu"
        }}""",
        'schema_system': """Aşağıdaki münazara geçmişine dayanarak, mermaid.js `graph TD;` formatında bir argüman haritası oluştur.

        ÖNEMLİ KURALLAR:
        1. Sadece `graph TD;` ile başlayan geçerli bir mermaid.js şeması döndür.
        2. Düğüm metinlerinde (node text) boşluk veya özel karakterler varsa, metnin tamamını çift tırnak içine al. Örnek: `A["Bu bir düğüm metnidir"] --> B["Bu da başka bir metin"]`.
        3. Asla tırnak içinde olmayan ayrı metin parçaları bırakma. Örnek: `YANLIŞ: A["Metin" Parça]`, `DOĞRU: A["Metin Parçası"]`.
        4. Çıktının başına veya sonuna "```mermaid" veya "```" gibi işaretler ekleme. Sadece saf şema kodunu döndür.

        Münazara Geçmişi:
        {conversation_history}""",
        'profile_system': "Aşağıdaki münazara özet verilerine dayanarak bir münazır profili analizi yap: {summary_data}",
        'quiz_system': """Konu: {topic}

        Bu konu hakkında {question_count} adet çoktan seçmeli soru oluştur. Sorular {level} seviyesinde olmalı ve kullanıcının bu konudaki yetkinlik seviyesini belirlemek için kullanılacak.

        ÖNEMLI: Sorular sadece "{topic}" konusu ile ilgili olmalı, münazara ile ilgili olmamalı.

        JSON formatında döndür:
        {{
          "questions": [
            {{
              "question": "Soru metni",
              "options": ["A seçeneği", "B seçeneği", "C seçeneği", "D seçeneği"],
              "correct": 0,
              "difficulty": "beginner|entry|mid|senior|master",
              "explanation": "Doğru cevabın açıklaması"
            }}
          ]
        }}""",
        'roadmap_system': """KONU: {topic}
        KULLANICI SEVİYESİ: {level}

        Bu kullanıcı için "{topic}" konusunda {level} seviyesine uygun detaylı bir öğrenme yolu oluştur.

        ÖNEMLI KURALLAR:
        1. Sadece "{topic}" konusu ile ilgili olmalı
        2. Münazara ile ilgili hiçbir içerik olmamalı
        3. {level} seviyesine uygun pratik görevler olmalı
        4. Gerçekçi projeler öner

        JSON formatında döndür:
        {{
          "title": "{topic} Öğrenme Yolu - {level} Seviyesi",
          "sections": [
            {{
              "title": "Bölüm Başlığı ({topic} ile ilgili)",
              "description": "Bölüm açıklaması",
              "tasks": [
                "Praktik görev 1",
                "Pratik görev 2"
              ]
            }}
          ],
          "projects": {{
            "micro": {{
              "title": "{topic} Mikro Proje",
              "description": "Küçük ölçekli proje açıklaması"
            }},
            "main": {{
              "title": "{topic} Ana Proje", 
              "description": "Ana proje açıklaması"
            }}
          }}
        }}"""
    },
    'en': {
        'debate_system': "You are a debate AI. The topic is: '{topic}'. Your role is to argue from the '{stance}' stance. Provide logical and persuasive counter-arguments to the user's points.",
        'report_system': """Analyze the following debate history and create a performance report in JSON format.

        IMPORTANT: Only use sentences that the user actually said. Do not fabricate or modify any sentences.

        Debate History:
        {conversation_history}

        Report format: (same as Turkish version)""",
        'schema_system': """Based on the following debate history, create an argument map in mermaid.js `graph TD;` format.

        IMPORTANT RULES:
        1. Only return a valid mermaid.js diagram starting with `graph TD;`.
        2. If node text contains spaces or special characters, enclose the entire text in double quotes. Example: `A["This is node text"] --> B["This is other text"]`.
        3. Never leave separate unquoted text fragments. Example: `WRONG: A["Text" Fragment]`, `CORRECT: A["Text Fragment"]`.
        4. Do not include markers like "```mermaid" or "```" at the beginning or end of the output. Return only the raw diagram code.

        Debate History:
        {conversation_history}""",
        'profile_system': "Based on the following summary data, perform a debater profile analysis: {summary_data}",
        'quiz_system': """Topic: {topic}

        Create {question_count} multiple choice questions about {topic}. Questions should be at {level} level and used to determine user competency in this topic.

        IMPORTANT: Questions should only be about "{topic}", not about debate.

        JSON format: (same as Turkish)""",
        'roadmap_system': """TOPIC: {topic}
        USER LEVEL: {level}

        Create a detailed learning path for "{topic}" suitable for {level} level.

        IMPORTANT RULES:
        1. Should only be about "{topic}"
        2. No debate-related content
        3. Practical tasks suitable for {level} level
        4. Suggest realistic projects

        JSON format: (same as Turkish but in English)"""
    }
}


# Helper Functions
def extract_user_sentences(conversation_history):
    """Extract only user sentences from conversation history"""
    user_sentences = []
    lines = conversation_history.split('\n')
    for line in lines:
        if line.strip().startswith('User:'):
            sentence = line.replace('User:', '').strip()
            if sentence:
                user_sentences.append(sentence)
    return user_sentences


def validate_report_sentences(report_data, user_sentences):
    """Validate that report only contains actual user sentences"""
    if 'gelistirilmesiGerekenNokta' in report_data and 'ornekCumle' in report_data['gelistirilmesiGerekenNokta']:
        example_sentence = report_data['gelistirilmesiGerekenNokta']['ornekCumle']

        # Check if the example sentence actually exists in user sentences
        found = False
        for user_sentence in user_sentences:
            if example_sentence.lower().strip() in user_sentence.lower().strip() or \
                    user_sentence.lower().strip() in example_sentence.lower().strip():
                found = True
                break

        if not found:
            # Replace with a generic message if no matching sentence found
            report_data['gelistirilmesiGerekenNokta']['ornekCumle'] = "Genel argüman yapısında gözlemlenen durum"

    return report_data


# ==================== ROUTES ====================

# Main page route
@app.route('/')
def index():
    return render_template('index.html')


# Learning paths route - ENSURE THIS IS PROPERLY REGISTERED
@app.route('/ogrenme-yollari')
def learning_paths():
    """Learning paths main page"""
    return render_template('learning_paths.html')


# API Routes
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

        conversation_history = "\n".join(
            [f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
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
    except Exception as e:
        print(f"Debate error: {e}")
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

        # Extract user sentences for validation
        user_sentences = extract_user_sentences(conversation_history)

        report_prompt = prompts[lang]["report_system"].format(conversation_history=conversation_history)

        payload = {"contents": [{"role": "user", "parts": [{"text": report_prompt}]}]}
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_json_string = response_text.strip().replace("```json", "").replace("```", "").strip()
        report_json = json.loads(cleaned_json_string)

        # Validate and fix report sentences
        report_json = validate_report_sentences(report_json, user_sentences)

        if 'user_id' in session:
            schema_prompt = prompts[lang]["schema_system"].format(conversation_history=conversation_history)
            schema_payload = {"contents": [{"role": "user", "parts": [{"text": schema_prompt}]}]}
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
        print(f"Report error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/schema', methods=['POST'])
def handle_schema():
    try:
        data = request.json
        lang = data.get('lang', 'tr')
        messages = data.get('messages', [])
        conversation_history = "\n".join(
            [f"{'User' if m['author'] == 'user' else 'AI Debater'}: {m['text']}" for m in messages])
        schema_prompt = prompts[lang]["schema_system"].format(conversation_history=conversation_history)

        payload = {"contents": [{"role": "user", "parts": [{"text": schema_prompt}]}]}
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_schema_string = response_text.strip().replace("```mermaid", "").replace("```", "").strip()
        return jsonify({"schema": cleaned_schema_string})
    except Exception as e:
        print(f"Schema error: {e}")
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


# ==================== LEARNING PATHS API ROUTES ====================

@app.route('/api/learning-topics', methods=['GET'])
def get_learning_topics():
    """Get all available learning topics"""
    topics = LearningTopic.query.all()
    return jsonify([{
        'id': topic.id,
        'name': topic.name,
        'description': topic.description
    } for topic in topics])


@app.route('/api/quiz/<int:topic_id>', methods=['POST'])
def generate_quiz(topic_id):
    """Generate or fetch quiz questions for a topic"""
    try:
        topic = LearningTopic.query.get_or_404(topic_id)
        lang = request.json.get('lang', 'tr')

        # Get existing questions for this topic
        existing_questions = Question.query.filter_by(topic_id=topic_id).all()
        questions_data = []

        if len(existing_questions) >= 5:
            # Use existing questions
            for q in existing_questions[:10]:
                questions_data.append({
                    'question': q.question_text,
                    'options': json.loads(q.options),
                    'correct': q.correct_answer,
                    'difficulty': q.difficulty,
                    'explanation': q.explanation
                })
        else:
            # Generate new questions with Gemini - FIXED: Use topic.name instead of generic
            needed_questions = 10 - len(existing_questions)
            quiz_prompt = prompts[lang]['quiz_system'].format(
                topic=topic.name,  # Use actual topic name
                question_count=needed_questions,
                level="mixed"
            )

            payload = {"contents": [{"role": "user", "parts": [{"text": quiz_prompt}]}]}
            response = requests.post(GEMINI_API_URL, json=payload)
            response.raise_for_status()
            response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
            cleaned_json = response_text.strip().replace("```json", "").replace("```", "").strip()
            quiz_data = json.loads(cleaned_json)

            # Add existing questions
            for q in existing_questions:
                questions_data.append({
                    'question': q.question_text,
                    'options': json.loads(q.options),
                    'correct': q.correct_answer,
                    'difficulty': q.difficulty,
                    'explanation': q.explanation
                })

            # Add new generated questions and save them
            for q_data in quiz_data['questions']:
                questions_data.append(q_data)

                new_question = Question(
                    topic_id=topic_id,
                    question_text=q_data['question'],
                    options=json.dumps(q_data['options']),
                    correct_answer=q_data['correct'],
                    difficulty=q_data['difficulty'],
                    explanation=q_data.get('explanation', '')
                )
                db.session.add(new_question)

            db.session.commit()

        return jsonify({'questions': questions_data[:10]})

    except Exception as e:
        print(f"Quiz generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/quiz-result', methods=['POST'])
def submit_quiz_result():
    """Submit quiz result and determine user level"""
    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    try:
        data = request.json
        topic_id = data['topic_id']
        score = data['score']

        # Determine level based on score
        if score >= 9:
            level = 'master'
        elif score >= 7:
            level = 'senior'
        elif score >= 5:
            level = 'mid'
        elif score >= 3:
            level = 'entry'
        else:
            level = 'beginner'

        # Save quiz result
        quiz_result = QuizResult(
            user_id=session['user_id'],
            topic_id=topic_id,
            score=score,
            level=level
        )
        db.session.add(quiz_result)
        db.session.commit()

        return jsonify({'level': level, 'score': score})

    except Exception as e:
        print(f"Quiz result error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/learning-path/<int:topic_id>', methods=['POST'])
def generate_learning_path(topic_id):
    """Generate personalized learning path"""
    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    try:
        data = request.json
        level = data['level']
        lang = data.get('lang', 'tr')
        topic = LearningTopic.query.get_or_404(topic_id)

        # FIXED: Generate roadmap with correct topic-specific prompt
        roadmap_prompt = prompts[lang]['roadmap_system'].format(
            topic=topic.name,  # Use actual topic name
            level=level
        )

        payload = {"contents": [{"role": "user", "parts": [{"text": roadmap_prompt}]}]}
        response = requests.post(GEMINI_API_URL, json=payload)
        response.raise_for_status()
        response_text = response.json()['candidates'][0]['content']['parts'][0]['text']
        cleaned_json = response_text.strip().replace("```json", "").replace("```", "").strip()
        roadmap_data = json.loads(cleaned_json)

        # Save learning path
        learning_path = LearningPath(
            user_id=session['user_id'],
            topic_id=topic_id,
            roadmap_data=json.dumps(roadmap_data),
            progress=json.dumps({})
        )
        db.session.add(learning_path)
        db.session.commit()

        return jsonify(roadmap_data)

    except Exception as e:
        print(f"Learning path generation error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/learning-paths', methods=['GET'])
def get_user_learning_paths():
    """Get user's learning paths"""
    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    # FIXED: Join with LearningTopic to get topic names
    paths = db.session.query(LearningPath, LearningTopic).join(
        LearningTopic, LearningPath.topic_id == LearningTopic.id
    ).filter(LearningPath.user_id == session['user_id']).all()

    result = []

    for path, topic in paths:
        result.append({
            'id': path.id,
            'topic_name': topic.name,
            'roadmap': json.loads(path.roadmap_data),
            'progress': json.loads(path.progress),
            'timestamp': path.timestamp.strftime('%d-%m-%Y')
        })

    return jsonify(result)


@app.route('/api/update-progress', methods=['POST'])
def update_progress():
    """Update learning path progress"""
    if 'user_id' not in session:
        return jsonify({'error': 'Login required'}), 401

    try:
        data = request.json
        path_id = data['path_id']
        progress = data['progress']

        learning_path = LearningPath.query.filter_by(
            id=path_id,
            user_id=session['user_id']
        ).first_or_404()

        learning_path.progress = json.dumps(progress)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        print(f"Progress update error: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== INITIALIZATION FUNCTIONS ====================

def init_sample_data():
    """Initialize sample learning topics"""
    try:
        if LearningTopic.query.count() == 0:
            topics = [
                ("Python Programlama",
                 "Python dilinde temel ve ileri seviye programlama konularını öğrenin. Veri yapıları, algoritma tasarımı ve modern Python tekniklerini kapsayan kapsamlı bir yol."),
                ("Web Geliştirme",
                 "HTML, CSS, JavaScript ile modern web uygulamaları geliştirmeyi öğrenin. Frontend ve backend teknolojileri ile tam yığın geliştirici olma yolculuğu."),
                ("Veri Bilimi",
                 "Veri analizi, makine öğrenmesi ve istatistiksel modelleme tekniklerini öğrenin. Python/R ile veri bilimi projelerinde uzmanlaşın."),
                ("Mobil Uygulama",
                 "iOS ve Android platformları için native ve cross-platform mobil uygulama geliştirme tekniklerini öğrenin."),
                ("Veritabanı Yönetimi",
                 "SQL ve NoSQL veritabanı sistemlerini öğrenin. Veri modelleme, optimizasyon ve büyük veri yönetimi konularında uzmanlaşın."),
                ("DevOps & Cloud",
                 "Deployment, CI/CD, container teknolojileri ve bulut mimarisi konularında expertise kazanın."),
                ("UI/UX Tasarım",
                 "Kullanıcı deneyimi tasarımı, arayüz geliştirme ve tasarım düşüncesi metodolojilerini öğrenin."),
                ("Yapay Zeka & ML",
                 "Machine Learning, Deep Learning ve yapay zeka uygulamaları geliştirme konularında uzmanlaşın."),
                ("Blockchain",
                 "Blockchain teknolojisi, kripto para sistemleri ve akıllı kontrat geliştirme konularını öğrenin."),
                ("Siber Güvenlik",
                 "Güvenlik testleri, penetrasyon testleri ve siber güvenlik risk yönetimi konularında uzmanlaşın."),
                ("Proje Yönetimi", "Agile, Scrum metodolojileri ve modern proje yönetimi tekniklerini öğrenin."),
                ("Grafik Tasarım",
                 "Adobe Creative Suite ve modern tasarım araçları ile profesyonel grafik tasarım teknikleri.")
            ]

            for name, desc in topics:
                topic = LearningTopic(name=name, description=desc)
                db.session.add(topic)

            db.session.commit()
            print(f"✅ {len(topics)} sample learning topics added!")
        else:
            print("ℹ️  Learning topics already exist.")
    except Exception as e:
        print(f"❌ Error initializing sample data: {e}")


# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return jsonify({"error": "Page not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


# ==================== DEBUG ROUTE ====================

@app.route('/debug/routes')
def list_routes():
    """Debug route to list all available routes"""
    import urllib.parse
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = urllib.parse.unquote("{:50s} {:20s} {}".format(rule.endpoint, methods, rule))
        output.append(line)

    return '<br>'.join(sorted(output))


# ==================== MAIN APPLICATION RUNNER ====================

if __name__ == '__main__':
    # Create application context
    with app.app_context():
        try:
            # Create all database tables
            db.create_all()
            print("✅ Database tables created successfully!")

            # Initialize sample data
            init_sample_data()

            # Print available routes for debugging
            print("\n🔗 Available routes:")
            print("   Main page: http://localhost:5001/")
            print("   Learning paths: http://localhost:5001/ogrenme-yollari")
            print("   Debug routes: http://localhost:5001/debug/routes")

        except Exception as e:
            print(f"❌ Initialization error: {e}")

    # Run the application on port 5001 instead of 5000
    print("\n🚀 Starting Flask application on port 5001...")
    app.run(debug=True, port=5001, host='0.0.0.0') 