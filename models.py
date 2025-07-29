from database import db # DÜZELTME: db nesnesini app.py yerine database.py'dan alıyoruz.
from datetime import datetime

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    debates = db.relationship('Debate', backref='user', lazy=True)

class Debate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    timestamp = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    report_data = db.Column(db.Text, nullable=False) # JSON string
    schema_data = db.Column(db.Text, nullable=False) # JSON string
