# Import the template rendering, redirecting, dynamic url generator and the aborting with a status code function
# Also import the request and session dictionary to check the endpoint and to save things globally respectively
from datetime import datetime
from flask import (abort, current_app, flash, g, redirect, render_template,
                   request, session, url_for)
from flask_login import current_user

from ..models import Permission, Post, PostCategory, User, db
from . import teacher_blog
from .forms import PostForm, SearchForm

# Get PostCategory objects from a list of PostCategory ids
def parseMultiplePost(form):
    # # Gather ids
    # num_list = form.categories.data

    # # Set initial value of list of PostCategory objects
    # return_list = []

    # # Iterate through whole list of ids
    # for i in num_list:
    #     # Turn id into an object
    #     category = PostCategory.query.filter_by(id=i).first()

    #     # Add that on to the list of PostCategory objects
    #     return_list.append(category)
    
    # # Return the list of objects back to the caller
    # return return_list

    return [PostCategory.query.get(category_id) for category_id in form.categories.data]

# Do the reverse of the above
def unparseMultiplePost(post):
    # Set initial value of list of PostCategory ids
    return_list = []

    # Iterate through the list of objects
    for i in post.categories:
        # Add the id of the category to the list of ids
        return_list.append(i.id)
    
    # Return the list of ids back to the caller
    return return_list

@teacher_blog.before_request
def before_teacher_blog_request():
    if not current_user.is_authenticated or not current_user.can(Permission.MANAGE_CLASS):
        abort(403)
    g.post_search_form = SearchForm()

@teacher_blog.route('/', methods=["GET", "POST"])
def index():
    posts = Post.query.filter(db.or_(Post.published == True, Post.author_id == current_user.id, current_user.is_admin())).order_by(Post.date_posted.desc())
    page = request.args.get('page', 1, int)
    form = PostForm()
    pagination = posts.paginate(
        page, per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=True)
    posts = pagination.items

    if form.validate_on_submit():
        # Get the actual category objects by parsing the ids using a function that I defined earlier
        categories = parseMultiplePost(form)

        post = Post(title=form.title.data, body=form.body.data, summary=form.summary.data, author=current_user._get_current_object(), categories=categories, published=form.published.data)

        db.session.add(post)

        return redirect(url_for('.index'))
    return render_template('teacher_blog/index.html', title='Blog', form=form, posts=posts, pagination=pagination)

@teacher_blog.route('/search')
def search():
    if not g.post_search_form.validate():
        abort(404)
    q = g.post_search_form.q.data
    g.search_form.q.data = ""
    page = request.args.get('page', 1, type=int)
    posts, total = Post.search(q, page, current_app.config["POSTS_PER_PAGE"])
    next_url = url_for('.search', q=q, page=page + 1) \
        if total > page * current_app.config["POSTS_PER_PAGE"] else None
    prev_url = url_for('.search', q=q, page=page - 1) \
        if page > 1 else None
    return render_template('teacher_blog/search_results.html', title="Search results for \"{0}\"".format(q), q=q, posts=posts.all(), total=total, prev_url=prev_url, next_url=next_url)

# Render a full post on its own
@teacher_blog.route('/<int:id>', methods=['GET', 'POST'])
def permalink(id):
    # Retrieve the post and if id doesn't exist yet, return a 404 status code.
    post = Post.query.get_or_404(id)
    
    # If the post isn't public and the author is not the current user
    if post.published == False and post.author != current_user and not current_user.is_admin():
        # Return a 403 status code (forbidden)
        abort(403)

    # Render template
    return render_template("teacher_blog/permalink.html", title="Post - " + post.title, post=post)

# Make a post public
@teacher_blog.route('/public/<int:id>')
def public(id):
    # Retrieve post from database (issue 404 error is post doesn't exist)
    post = Post.query.get_or_404(id)

    # Issue a 403 (forbidden) error if post author is not the logged in user
    if post.author.username != current_user.username and not current_user.is_admin():
        abort(403)

    # Change status of post
    post.published = True

    # Flash a message that says that the post is public.
    flash("Your post is now public.", 'info')

    return redirect(url_for('.index'))

# Make a post private or a draft
@teacher_blog.route('/draft/<int:id>')
def draft(id):
    # Retrieve post from database (issue 404 error is post doesn't exist)
    post = Post.query.get_or_404(id)

    # Issue a 403 (forbidden) error if post author is not the logged in user
    if post.author.username != current_user.username and not current_user.is_admin():
        abort(403)

    # Change status of post
    post.published = False

    # Flash a message that says that the post is a draft
    flash("Your post is now a draft.", 'info')

    return redirect(url_for('.index'))

# Editing a post
@teacher_blog.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    # Retrieve post from database (issue 404 error is post doesn't exist)
    post = Post.query.get_or_404(id)

    # Create form object
    form = PostForm()

    # Issue a 403 (forbidden) error if post author is not the logged in user
    if current_user.username != post.author.username and not current_user.admin():
        abort(403)

    # If request method is POST (a form was submitted)
    if form.validate_on_submit():
        post.title = form.title.data
        post.body = form.body.data
        post.summary = form.summary.data
        post.categories = parseMultiplePost(form)
        post.published = form.published.data
        post.date_posted = datetime.utcnow()

        # Redirect the user to the page with the post in it
        return redirect(url_for('.permalink', id=id))
    
    # Set initial values of the fields with the post data
    form.title.data = post.title
    form.body.data = post.body
    form.summary.data = post.summary

    # Get list of tag ids by calling the unparseMultiplePost function (it was defined earlier)
    form.categories.data = unparseMultiplePost(post)
    form.published.data = post.published

    # Render edit page template
    return render_template("teacher_blog/edit.html", title="Edit Post - " + post.title, post=post, form=form)

@teacher_blog.route('/category/<int:id>')
def category(id):
    # Get the pagination page. If no page is specified the default page number (1) is used.
    page = request.args.get("page", 1, type=int)

    category = PostCategory.query.get_or_404(id)
    posts = category.posts.filter(db.or_(Post.published == True, Post.author_id == current_user.id,
                current_user.is_admin())).order_by(Post.date_posted.desc())

    pagination = posts.paginate(
        page, per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=True)

    posts = pagination.items

    return render_template("teacher_blog/category.html", title="Category - " + category.name, category=category, posts=posts, pagination=pagination)