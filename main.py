from flask import Flask, render_template, redirect, url_for, flash,abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from functools import wraps
from flask_migrate import Migrate
from datetime import datetime


app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
ckeditor = CKEditor(app)
Bootstrap(app)

##CONNECT TO DB
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
login_manager = LoginManager()
login_manager.init_app(app)
db = SQLAlchemy(app)

migrate = Migrate(app, db)

year = datetime.now().date().year

##CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    author_ = relationship('User',back_populates='blogs')
    comment = relationship('Comment',back_populates='post')



class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(300), nullable=False)
    name = db.Column(db.String(250), nullable=False)
    blogs = relationship('BlogPost',back_populates='author_')
    comment = relationship('Comment',back_populates='text_')

class Comment(db.Model):
    __tablename__='comments'
    id = db.Column(db.Integer,primary_key= True)
    text = db.Column(db.String(300),nullable=False)
    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))
    post_id = db.Column(db.Integer,db.ForeignKey('blog_posts.id'))
    post = relationship('BlogPost',back_populates='comment')
    text_ = relationship('User',back_populates='comment')




with app.app_context():
    db.create_all()


def admin_only(fun):
    @wraps(fun)
    def wrapper(*args,**kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return fun(*args,**kwargs)
        else:
            return abort(403)
    return wrapper


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    return render_template("index.html", all_posts=posts,year=year)



@app.route('/register', methods=['POST', 'GET'])
def register():
    register_form = RegisterForm()
    new_user = User()
    if new_user.query.filter_by(email=register_form.email.data).first():
        flash("Email already registered login instead")
        return redirect(url_for('login'))
    if register_form.validate_on_submit():
        new_user.email = register_form.email.data
        new_user.password = generate_password_hash(register_form.password.data, 'pbkdf2:sha256', 8)
        new_user.name = register_form.name.data
        db.session.add(new_user)
        db.session.commit()
        new_user = User.query.filter_by(email=register_form.email.data).first()

        login_user(new_user)
        return redirect(url_for('get_all_posts'))

    return render_template("register.html", form=register_form,year=year)


@app.route('/login', methods=['POST', 'GET'])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit():
        user_email = login_form.email.data
        user_password = login_form.password.data
        user = User.query.filter_by(email=user_email).first()
        if user and check_password_hash(user.password, user_password):
            login_user(user)
            return redirect(url_for('get_all_posts'))
        elif not user:
            flash('Email not found,please Register instead')
            return redirect(url_for('register'))
        else:
            flash('Incorrect Password')
            return redirect(url_for('login'))
    return render_template("login.html", form=login_form,year=year)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>",methods=['POST','GET'])
def show_post(post_id):
    requested_post = BlogPost.query.get(post_id)
    comments = Comment.query.filter_by(post_id=post_id).all()

    comment_form = CommentForm()
    if current_user.is_authenticated and comment_form.validate_on_submit():
        new_comment = Comment(text=comment_form.comment.data,
                user_id = current_user.id,
                post_id = post_id)
        db.session.add(new_comment)
        db.session.commit()
    elif comment_form.validate_on_submit() and not current_user.is_authenticated:
        flash('Login to save a comment')
        return redirect(url_for('login'))

    return render_template("post.html",
                           post=requested_post,year=year,
                           comment_form=comment_form,comments=comments)


@app.route("/about")
def about():
    return render_template("about.html",year=year)


@app.route("/contact")
def contact():
    return render_template("contact.html",year=year)


@app.route("/new-post",methods=['GET','POST'])
@admin_only
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=form.author.data,
            date=date.today().strftime("%B %d, %Y"),
            user_id = current_user.id

        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form,year=year)


@app.route("/edit-post/<int:post_id>")
@admin_only
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = edit_form.author.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form,year=year)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))  # Fallback to 5000 if PORT is not set
    app.run(host='0.0.0.0', port=port)
