import os
import secrets
from PIL import Image
#for resizing large images
from flask import render_template, url_for, flash, redirect, request, abort
#request is for GET or POST methods
from flask_pract import app, bcrypt, db, mail
from flask_pract.reg_forms import Reg_Form, Login_Form, UpdateAccountForm, PostForm,RequestResetForm,ResetPasswordForm
from flask_pract.models import User,Post
from flask_login import login_user, current_user, logout_user, login_required
from flask_mail import Message

@app.route("/")
def home():
    page = request.args.get('page', 1, type = int)
    posts = Post.query.order_by(Post.date_posted.desc()).paginate(page=page,per_page=3)
    return render_template('home.html', posts = posts)

@app.route("/about")
def about():
    return render_template('about.html',title="About")

@app.route("/register", methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = Reg_Form()
    username_check = User.query.filter_by(username = form.username.data).first()
    email_check = User.query.filter_by(email = form.email.data).first()
    if username_check:
        flash('Username already taken')
    elif email_check:
        flash('Email already taken')
    elif form.validate_on_submit() and not username_check and not email_check:   
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username = form.username.data, email=form.email.data, password = hashed_pw)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been successfully created! You are now able to log in.')
        return redirect(url_for('login'))

    return render_template('register.html',title="Register", form = form)

@app.route("/login", methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = Login_Form()
    if form.validate_on_submit():
        user = User.query.filter_by(email = form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user,remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('account'))
        else:
            flash(f'Login unsuccessful. Please check your email and password')
    return render_template('login.html',title="Login", form = form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    #underscore to throw away unused variable, os.path returns a file name and its extension
    pic_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics',pic_fn)
    output_size = (125,125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    return pic_fn

@app.route("/account",methods=['GET','POST'])
@login_required
def account():
    form = UpdateAccountForm()
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    username_check = User.query.filter_by(username = form.username.data).first()
    email_check = User.query.filter_by(email = form.email.data).first()
    if username_check and current_user.username != form.username.data:
        flash('Username already taken')
    if email_check and current_user.email != form.email.data:
        flash('Email already taken')
    if form.validate_on_submit() and not username_check and not email_check: 
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Account updated!')
    if form.validate_on_submit() and not username_check:   
        current_user.username = form.username.data
        db.session.commit()
        flash("Account username updated!")
    if form.validate_on_submit() and not email_check:   
        current_user.email = form.email.data
        db.session.commit()
        flash("Account email updated!")
    if form.validate_on_submit() and form.picture.data:
        pic_file = save_picture(form.picture.data)
        current_user.image_file = pic_file
        db.session.commit()
        flash("Account picture updated!")
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.picture.data = current_user.image_file
    return render_template('account.html', title ='Account',image_file=image_file, form=form )

@app.route("/post/new",methods=['GET','POST'])
@login_required
def new_post():
     form = PostForm()
     if form.validate_on_submit():
         post = Post(title=form.title.data, content = form.content.data, author=current_user)
         db.session.add(post)
         db.session.commit()
         return redirect(url_for('home'))
     return render_template('create_post.html', title ='New Post', form = form,legend = 'New Post')

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title= post.title,post = post)

@app.route("/post/<int:post_id>/update",methods=['GET','POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
        #forbidden route that can be customized
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title= "Update Post",form = form, legend = 'Upddate Your Post')

@app.route("/post/<int:post_id>/delete",methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
        #forbidden route that can be customized
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!')
    return redirect(url_for('home'))

@app.route("/user/<string:username>")
def user_posts(username):
    page = request.args.get('page', 1, type = int)
    user = User.query.filter_by(username = username).first_or_404()
    posts = Post.query.filter_by(author=user)\
                .order_by(Post.date_posted.desc())\
                .paginate(page=page,per_page=3)
    return render_template('user_posts.html', posts = posts, user=user)

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Password Reset Request', sender='noreply@demo.com', recipients=[user.email])
    msg.body=f''' To reset your password, visit the following link: {url_for('reset_token',token=token,_external=True)}
    If you did not make this request then simply ignore this email and no changes will be made.
    '''
    mail.send(msg)


@app.route("/reset_password", methods=['GET','POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('An email has been sent with instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title = 'Reset Password', form = form)

@app.route("/reset_password/<token>", methods=['GET','POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = User.verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():   
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user.password = hashed_pw
        db.session.commit()
        flash('Your password has been successfully updated!')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title = 'Reset Password', form = form)