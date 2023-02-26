from app.main import bp
from flask import render_template, flash, redirect, url_for, request, current_app
from flask_login import current_user, login_required
from datetime import datetime
from app import db, headersPages
from app.models import Post, User
from app.main.forms import PostForm

from guess_language import guess_language

print('main')


@bp.before_app_request
def before_request():
    if current_user.is_authenticated:  # type: ignore
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@bp.route('/')
@bp.route('/about-us')
def about_us():
    headers = [x[:] for x in headersPages]
    headers[1][1] = True
    return render_template('about-us.html', headers=headers)


@bp.route('/news', methods=['GET', 'POST'])
@login_required
def news():
    headers = [x[:] for x in headersPages]
    headers[2][1] = True
    form = PostForm()
    if form.validate_on_submit():
        language = guess_language(form.post.data)
        if language == 'UNKNOWN' or len(language) > 5:  # type: ignore
            language = ''
        post = Post(body=form.post.data, author=current_user, language=language)
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('main.news'))
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(  # type: ignore
        page=page, per_page=current_app._get_current_object(  # type: ignore
        ).config['POSTS_PER_PAGE'], error_out=False)
    next_url = url_for('main.news', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('main.news', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template("news.html", form=form,
                           posts=posts.items, headers=headers, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/index')
@login_required
def index():
    headers = [x[:] for x in headersPages]
    headers[0][1] = True
    users = User.query.all()
    return render_template('index.html', headers=headers, users=users)


@bp.route('/profile/<username>')
@login_required
def user(username):
    user = User.query.filter_by(username=username).first_or_404()
    page = request.args.get('page', 1, type=int)
    posts = user.posts.order_by(Post.timestamp.desc()).paginate(
        page=page, per_page=current_app._get_current_object(  # type: ignore
        ).config['POSTS_PER_PAGE'], error_out=False)
    headers = [x[:] for x in headersPages]
    next_url = url_for('main.user', username=current_user.username,  # type: ignore
                       page=posts.next_num) if posts.has_next else None
    prev_url = url_for('main.user', username=current_user.username,  # type: ignore
                       page=posts.prev_num) if posts.has_prev else None
    headers[3][1] = True
    return render_template('user.html', user=user, posts=posts.items,
                           headers=headers, next_url=next_url,
                           prev_url=prev_url)


@bp.route('/follow/<username>')
@login_required
def follow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot follow yourself!')
        return redirect(url_for('main.user', username=username))
    current_user.follow(user)  # type: ignore
    db.session.commit()
    flash('You are following {}!'.format(username))
    return redirect(url_for('main.user', username=username))


@bp.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        flash('User {} not found.'.format(username))
        return redirect(url_for('main.index'))
    if user == current_user:
        flash('You cannot unfollow yourself!')
        return redirect(url_for('main.user', username=username))
    current_user.unfollow(user)  # type: ignore
    db.session.commit()
    flash('You are not following {}.'.format(username))
    return redirect(url_for('main.user', username=username))
