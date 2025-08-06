from database import db
from datetime import datetime


# Replace the existing model definitions in your app.py with these corrected versions

# Database Models (corrected)
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
    def calculate_progress(self):
        """Calculate overall progress percentage for this learning path"""
        import json
        try:
            path_data = json.loads(self.path_data)
            progress_data = json.loads(self.progress_data) if self.progress_data else {}

            total_tasks = 0
            completed_tasks = 0

            for section_idx, section in enumerate(path_data.get('sections', [])):
                section_tasks = len(section.get('tasks', []))
                total_tasks += section_tasks

                section_progress = progress_data.get(str(section_idx), {})
                completed_tasks += sum(1 for task_completed in section_progress.values() if task_completed)

            return (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        except:
            return 0

    def get_section_progress(self, section_index):
        """Get progress for a specific section"""
        import json
        try:
            path_data = json.loads(self.path_data)
            progress_data = json.loads(self.progress_data) if self.progress_data else {}

            section = path_data['sections'][section_index]
            total_tasks = len(section.get('tasks', []))

            section_progress = progress_data.get(str(section_index), {})
            completed_tasks = sum(1 for task_completed in section_progress.values() if task_completed)

            return (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
        except:
            return 0