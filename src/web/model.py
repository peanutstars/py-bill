import datetime

from flask_login import UserMixin
from . import db


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(32))
    password = db.Column(db.String(100))
    registered_date = db.Column(db.DateTime, default=datetime.datetime.now)
