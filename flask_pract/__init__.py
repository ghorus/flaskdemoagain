import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_mail import Mail

import os
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dbc761867601a6df37da071b55b8128d'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL")

db= SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True

app.config['MAIL_USERNAME'] = os.environ.get('EMAIL')
app.config['MAIL_PASSWORD'] = os.environ.get('PW')
mail=Mail(app)
from flask_pract import routes

