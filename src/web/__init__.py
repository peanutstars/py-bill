from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
db = SQLAlchemy(app)
login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):
    from .view_account import load_user
    return load_user(user_id)
