from flask import abort, current_app, flash, g, render_template, redirect, request, url_for
from flask_login import current_user, login_required
from datetime import datetime
from ..models import db, Post, Tag
from .forms import PostForm, SearchForm
from . import announcements

@announcements.before_request
def addSearchForm():
    g.post_search_form = SearchForm()

# Get Tag objects from a list of Tag ids
def parseMultiplePost(form):
    # Gather ids
    num_list = form.tags.data

    # Set initial value of list of Tag objects
    return_list = []

    # Iterate through whole list of ids
    for i in num_list:
        # Turn id into an object
        tag = Tag.query.filter_by(id=i).first()

        # Add that on to the list of Tag objects
        return_list.append(tag)
    
    # Return the list of objects back to the caller
    return return_list

# Do the reverse of the above
def unparseMultiplePost(post):
    # Set initial value of list of Tag ids
    return_list = []

    # Iterate through the list of objects
    for i in post.tags:
        # Add the id of the tag to the list of ids
        return_list.append(i.id)
    
    # Return the list of ids back to the caller
    return return_list

@announcements.route('/', methods=['GET', 'POST'])
def index():
    # Get the pagination page. If no page is specified the default page number (1) is used.
    page = request.args.get("page", 1, type=int)
    form = PostForm()

    posts = Post.query.filter(db.or_(Post.published == True, Post.author_id == current_user.id, current_user.is_admin())).order_by(Post.date_posted.desc())

    pagination = posts.paginate(
        page, per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=True)

    posts = pagination.items

    if form.validate_on_submit():
        # Get the actual tag objects by parsing the ids using a function that I defined earlier
        tags = parseMultiplePost(form)

        # Create a post object
        post = Post(title=form.title.data, body=form.body.data, summary=form.summary.data, author=current_user._get_current_object(), tags=tags, published=form.published.data)

        # Add the post to the database session
        db.session.add(post)

        # Commit the database session to write the post to the database
        db.session.commit()

        # Issue a redirect to the home page
        return redirect(url_for('.index'))
    
    # Render the announcements/index.html template
    return render_template("announcements/index.html", title="Announcements", form=form, posts=posts, pagination=pagination)

# Render a full post/announcement on its own
@announcements.route('/<int:id>', methods=['GET', 'POST'])
def permalink(id):
    # Retrieve the post and if id doesn't exist yet, return a 404 status code.
    post = Post.query.get_or_404(id)
    
    # If the post isn't public and the author is not the current user
    if post.published == False and post.author != current_user and not current_user.is_admin():
        # Return a 403 status code (forbidden)
        abort(403)

    # Render template
    return render_template("announcements/permalink.html", title="Announcement - " + post.title, post=post)

@announcements.route('/tag/<int:id>')
def tag(id):
    # Get the pagination page. If no page is specified the default page number (1) is used.
    page = request.args.get("page", 1, type=int)

    tag = Tag.query.get_or_404(id)
    posts = tag.posts.filter(db.or_(Post.published == True, Post.author_id == current_user.id,
                current_user.is_admin())).order_by(Post.date_posted.desc())

    pagination = posts.paginate(
        page, per_page=current_app.config["POSTS_PER_PAGE"],
        error_out=True)

    posts = pagination.items

    return render_template("announcements/tag.html", title="Tag - " + tag.name, tag=tag, posts=posts, pagination=pagination)

# Make a post public
@announcements.route('/public/<int:id>')
@login_required        # Protect the route so that only logged in users can view it
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
@announcements.route('/draft/<int:id>')
@login_required        # Protect the route so that only logged in users can view it
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
@announcements.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required        # Protect the route so that only logged in users can view it
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
        post.tags = parseMultiplePost(form)
        post.published = form.published.data
        post.date_posted = datetime.utcnow()

        # Redirect the user to the page with the post in it
        return redirect(url_for('.permalink', id=id))
    
    # Set initial values of the fields with the post data
    form.title.data = post.title
    form.body.data = post.body
    form.summary.data = post.summary

    # Get list of tag ids by calling the unparseMultiplePost function (it was defined earlier)
    form.tags.data = unparseMultiplePost(post)
    form.published.data = post.published

    # Render edit page template
    return render_template("announcements/edit.html", title="Edit Announcement - " + post.title, post=post, form=form)