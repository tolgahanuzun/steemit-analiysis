import os
from collections import Counter

from flask import Flask, url_for, redirect, request, render_template, abort

from flask_admin import helpers, expose
from flask_admin.contrib import sqla
from flask_sqlalchemy import SQLAlchemy
from wtforms import form, fields, validators
from flask_admin import base
from sqlalchemy import UniqueConstraint

import flask_admin as admin
import flask_login as login
from datetime import datetime

from werkzeug.security import generate_password_hash, check_password_hash

from steemit import get_url, vesting_calculator, ff_count, vote_count, blog_list, convert, deconvert

app = Flask(__name__)

app.config['SECRET_KEY'] = 'steemit'


app.config['DATABASE_FILE'] = 'steemit.sqlite'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + app.config['DATABASE_FILE']
app.config['SQLALCHEMY_ECHO'] = False
db = SQLAlchemy(app)


class Steemit_User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    steem_name = db.Column(db.String(200))
    post_key = db.Column(db.String(200))

    def __str__(self):
        return str(self.steem_name)

    def __repr__(self):
        return '<Steemit_User %r>' % (self.steem_name)

    def get_users(self, user_id):
        return self.query.filter_by(steem_name=user_id).first() or False


class Analiysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    #
    steemit_user_id = db.Column(db.Integer(), db.ForeignKey(Steemit_User.id))
    steemit_user = db.relationship(Steemit_User)
    #
    start_date = db.Column(db.DateTime)
    end_date = db.Column(db.DateTime, default=datetime.utcnow)
    #
    following = db.Column(db.Integer())
    followers = db.Column(db.Integer())
    post = db.Column(db.Integer())
    #
    sp = db.Column(db.Integer())
    #
    blog = db.Column(db.String())
    tittle = db.Column(db.String())
    category = db.Column(db.String())
    votes = db.Column(db.String())
    price = db.Column(db.String())

    __table_args__ = (
        UniqueConstraint("id", "end_date"),
    )


    def __str__(self):
        return str(self.id)

    def __repr__(self):
        return '<Analiysis %r - %r>' % (self.id, self.steemit_user)

    def get_blog(self, blog):
        return self.query.filter_by(post=blog).first() or False

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    login = db.Column(db.String(80), unique=True)
    email = db.Column(db.String(120))
    password = db.Column(db.String(64))

    # Flask-Login integration
    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False

    def get_id(self):
        return self.id

    # Required for administrative interface
    def __unicode__(self):
        return self.username


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        user = self.get_user()

        if user is None:
            raise validators.ValidationError('Invalid user')

        if not check_password_hash(user.password, self.password.data):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(login=self.login.data).first()


class RegistrationForm(form.Form):
    login = fields.StringField(validators=[validators.required()])
    email = fields.StringField()
    password = fields.PasswordField(validators=[validators.required()])

    def validate_login(self, field):
        if db.session.query(User).filter_by(login=self.login.data).count() > 0:
            raise validators.ValidationError('Duplicate username')


# Initialize flask-login
def init_login():
    login_manager = login.LoginManager()
    login_manager.init_app(app)

    # Create user loader function
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.query(User).get(user_id)


# Create customized model view class
class MyModelView(sqla.ModelView):

    def is_accessible(self):
        return login.current_user.is_authenticated


# Create customized index view class that handles login & registration
class MyAdminIndexView(base.AdminIndexView):

    @expose('/')
    def index(self):
        if not login.current_user.is_authenticated:
            return redirect(url_for('.login_view'))
        return super(MyAdminIndexView, self).index()

    @expose('/login/', methods=('GET', 'POST'))
    def login_view(self):
        # handle user login
        form = LoginForm(request.form)
        if helpers.validate_form_on_submit(form):
            user = form.get_user()
            login.login_user(user)

        if login.current_user.is_authenticated:
            return redirect(url_for('.index'))
        link = ''
        self._template_args['form'] = form
        self._template_args['link'] = link
        return super(MyAdminIndexView, self).index()

    @expose('/logout/')
    def logout_view(self):
        login.logout_user()
        return redirect(url_for('.index'))
    
# Flask views
@app.route('/admin')
def admin():
    return redirect(url_for('admin.login_view'))

@app.route('/')
def index():
    if request.query_string and request.args.get('account'):
        return redirect('/' + request.args.get('account'))
    
    return render_template('base.html')


@app.route('/<username>')
def details(username):

    if username.startswith("@"):
        username = username.replace("@", "")
    status, response = get_url(username)
    if not status:
        return redirect('/')
    
    if Steemit_User().get_users(username):
        return redirect('/{}/analiysis/1'.format(username))
    else:
        #
        user = Steemit_User()
        user.steem_name = username
        #
        session = Analiysis()
        session.steemit_user = user

        session.sp = vesting_calculator(response['user'])
        session.post = response['user']['post_count'] 
        session.start_date = datetime.strptime(response['user']['created'], '%Y-%m-%dT%H:%M:%S')
        session.end_date = datetime.now()
        session.followers, session.following  = ff_count(username)
        
        blog_result = blog_list(username)
        blog_text = convert(blog_result)
        session.blog = blog_text['blog']
        session.tittle = blog_text['tittle']
        session.category = blog_text['category']
        session.votes = blog_text['votes'] 
        session.price = blog_text['price']

        db.session.add(session)
        db.session.add(user)
        db.session.commit()

    return redirect('/{}/analiysis/1'.format(username))


@app.route('/<username>/analiysis/', defaults={'count': 1})
@app.route('/<username>/analiysis/<int:count>')
def analiysis(username, count):
    if username.startswith("@"):
        username = username.replace("@", "")
    user = Steemit_User().get_users(username)
    if not user:
        abort(404)

    analiysis = Analiysis.query.filter_by(steemit_user=user).all()[count-1]

    result = {
        "blog": deconvert(analiysis.blog),
        "tittle": deconvert(analiysis.tittle),
        "category": deconvert(analiysis.category),
        "votes": [float(x) for x in deconvert(analiysis.votes)],
        "price": [float(x) for x in deconvert(analiysis.price)],
        "end_date": analiysis.end_date,
        "start_date": analiysis.start_date,
        "sp": analiysis.sp,
        "followers": analiysis.followers,
        "following": analiysis.following,
        "all_post": analiysis.post,
        "sum_votes": sum([float(x) for x in deconvert(analiysis.votes)]),
        "sum_price": sum([float(x) for x in deconvert(analiysis.price)]),
        "sum_blog": len(deconvert(analiysis.blog))
    }

    result['votes_max_id'] = result['votes'].index(max(result['votes']))
    result['price_max_id'] = result['price'].index(max(result['price']))

    counter = Counter(result['category'])
    result['cetegory_uniqe'] = counter.keys()
    result['cetegory_max'] = max(result['cetegory_uniqe'])
    result['cetegory_max_int'] = counter[result['cetegory_max']]
    
    return render_template('index.html', result=result)
# Initialize flask-login
init_login()

# Create admin
admin = base.Admin(app, 'Bot', index_view=MyAdminIndexView(), base_template='my_master.html')

# Add view
admin.add_view(MyModelView(Steemit_User, db.session))
admin.add_view(MyModelView(Analiysis, db.session))
admin.add_view(MyModelView(User, db.session))

def build_sample_db():
    db.drop_all()
    db.create_all()

    test_user = User(login="test", password=generate_password_hash("test"))
    db.session.add(test_user)
    db.session.commit()
    return
if __name__ == '__main__':
    # Build a sample db on the fly, if one does not exist yet.
    app_dir = os.path.realpath(os.path.dirname(__file__))
    database_path = os.path.join(app_dir, app.config['DATABASE_FILE'])
    if not os.path.exists(database_path):
        build_sample_db()
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)