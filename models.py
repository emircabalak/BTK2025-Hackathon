from database import db
from datetime import datetime


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    debates = db.relationship('Debate', backref='user', lazy=True)
    learning_paths = db.relationship('LearningPath', backref='user', lazy=True)


class Debate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    report_data = db.Column(db.Text, nullable=False)  # JSON string
    schema_data = db.Column(db.Text, nullable=False)  # JSON string


class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String(100), nullable=False)
    question = db.Column(db.Text, nullable=False)
    options = db.Column(db.Text, nullable=False)  # JSON array of options
    correct_answer = db.Column(db.Integer, nullable=False)  # Index of correct option
    difficulty = db.Column(db.String(20), nullable=False)  # beginner, entry, mid, senior, master
    explanation = db.Column(db.Text, nullable=True)  # Explanation for the correct answer
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class LearningPath(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(100), nullable=False)  # Topic ID (python, javascript, etc.)
    title = db.Column(db.String(200), nullable=False)  # Generated path title
    description = db.Column(db.Text, nullable=True)  # Path description
    estimated_duration = db.Column(db.String(50), nullable=True)  # e.g., "4-6 weeks"
    user_level = db.Column(db.String(20), nullable=False)  # beginner, entry, mid, senior, master
    quiz_score = db.Column(db.Integer, nullable=True)  # Score from assessment quiz
    path_data = db.Column(db.Text, nullable=False)  # JSON containing sections, tasks, projects
    progress_data = db.Column(db.Text, nullable=False, default='{}')  # JSON for tracking task completion
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

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