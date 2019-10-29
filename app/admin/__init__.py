from flask import Blueprint

admin = Blueprint('admin', __name__)

from . import views, forms
from ..models import (User, Role, Strand, Module, Chapter, Lesson, Page,
                      PageType, Permission, Tag, db, Post, QuizAttempt, Class,
                      ClassStudent, Assignment, StudentAssignment,
                      ProblemMistake, ProblemMistakeType, QuestionAnswer)

model_singulars = {'Strands': 'strand', 'Modules': 'module',
    'Chapters': 'chapter', 'Lessons': 'lesson', 'Pages': 'page',
    'Quizzes': 'quiz', 'Glossaries': 'glossary', 'Questions': 'question',
    'Projects': 'project', 'Skills': 'skill'}

@admin.app_context_processor
def inject_models():
    return dict(User=User, Role=Role, Strand=Strand, Module=Module, Chapter=Chapter, Lesson=Lesson,
        Tag=Tag, db=db, Page=Page, PageType=PageType, Post=Post,
        Permission=Permission, QuizAttempt=QuizAttempt, Class=Class,
        ClassStudent=ClassStudent, Assignment=Assignment,
        StudentAssignment=StudentAssignment, ProblemMistake=ProblemMistake,
        ProblemMistakeType=ProblemMistakeType, QuestionAnswer=QuestionAnswer,
        model_singulars=model_singulars)