from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import sqlalchemy.dialects.postgresql as pg
from pgvector.sqlalchemy import Vector

db = SQLAlchemy()

class User(db.Model):
    user_id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False, unique=True)

    prompts = relationship("Prompt", back_populates="user", cascade="all, delete-orphan")
    entries = relationship("Entry", back_populates="user", cascade="all, delete-orphan")


class Prompt(db.Model):
    prompt_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey("user.user_id"), nullable=False)
    prompt_text = db.Column(db.Text, nullable=False)
    embedding_vector = db.Column(Vector(1536), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = relationship("User", back_populates="prompts")
    entries = relationship("Entry", back_populates="prompt", cascade="all, delete-orphan")


class Entry(db.Model):
    entry_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, ForeignKey("user.user_id"), nullable=False)
    prompt_id = db.Column(db.Integer, ForeignKey("prompt.prompt_id"), nullable=True)
    entry_text = db.Column(db.Text, nullable=True)
    theme = db.Column(db.Text, nullable=True)
    embedding_vector = db.Column(Vector(1536), nullable=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    user = relationship("User", back_populates="entries")
    prompt = relationship("Prompt", back_populates="entries")