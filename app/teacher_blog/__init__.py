from flask import Blueprint

teacher_blog = Blueprint('teacher_blog', __name__)

from . import views, forms