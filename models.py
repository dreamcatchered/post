from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from slugify import slugify
import uuid

db = SQLAlchemy()

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    author_name = db.Column(db.String(128))
    content = db.Column(db.Text, nullable=False) # Храним HTML
    slug = db.Column(db.String(255), unique=True, nullable=False)
    owner_uuid = db.Column(db.String(64), nullable=False) # Идентификатор автора
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_unique_slug(title):
        base_slug = slugify(title) if title else "untitled"
        date_part = datetime.now().strftime("%m-%d")
        full_slug = f"{base_slug}-{date_part}"
        
        # Проверка на уникальность (добавляем число, если занято)
        counter = 1
        unique_slug = full_slug
        while Post.query.filter_by(slug=unique_slug).first():
            counter += 1
            unique_slug = f"{full_slug}-{counter}"
        return unique_slug



