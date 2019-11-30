from flask import Blueprint

admin = Blueprint('admin', __name__)

from ..models import (Announcement, Assignment, Chapter, Class, ClassStudent,
                      Lesson, Module, Page, PageType, Permission, Post,
                      PostCategory, ProblemMistake, ProblemMistakeType,
                      QuestionAnswer, QuizAttempt, Role, Strand,
                      StudentAssignment, Tag, User, UserAnswer, db)
from . import forms, views


model_singulars = {'Strands': 'strand', 'Modules': 'module',
    'Chapters': 'chapter', 'Lessons': 'lesson', 'Pages': 'page',
    'Quizzes': 'quiz', 'Glossaries': 'glossary', 'Questions': 'question',
    'Projects': 'project', 'Skills': 'skill'}

@admin.app_context_processor
def inject_models():
    return dict(User=User, Role=Role, Strand=Strand, Module=Module, Chapter=Chapter, Lesson=Lesson,
        Tag=Tag, db=db, Page=Page, PageType=PageType, Post=Post,
        PostCategory=PostCategory, Announcement=Announcement, Permission=Permission,
        QuizAttempt=QuizAttempt, Class=Class, ClassStudent=ClassStudent,
        Assignment=Assignment, StudentAssignment=StudentAssignment,
        ProblemMistake=ProblemMistake, ProblemMistakeType=ProblemMistakeType,
        QuestionAnswer=QuestionAnswer, UserAnswer=UserAnswer,
        model_singulars=model_singulars)