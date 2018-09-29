from flask import Blueprint

admin = Blueprint('admin', __name__)

from . import views, forms
from ..models import Topic, Strand, Module, Lesson, Permission, Tag, db, Post

model_singulars = {'Topics': 'topic', 'Strands': 'strand', 'Modules': 'module', 'Lessons': 'lesson', 'Pages': 'page', 'Quizzes': 'quiz', 'Glossaries': 'glossary', 'Questions': 'question', 'Projects': 'project'}

@admin.app_context_processor
def inject_permissions():
    return dict(Topic=Topic, Strand=Strand, Module=Module, Lesson=Lesson, Tag=Tag, db=db, Post=Post, Permission=Permission, model_singulars=model_singulars)