import datetime

from dateutil.relativedelta import relativedelta
from flask import jsonify, request
from flask_login import UserMixin

from . import db
from core.helper import DateTool


class Role:
    TYPE = {
        'ADMIN':    100,
        'STOCK':    300,
        'BOOKMARK': 600,
        'NONE':     900,
    }

    @classmethod
    def is_authorized(cls, required, user):
        return cls.TYPE.get(required, 'NONE') >= cls.TYPE.get(user)


class User(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True)
    username = db.Column(db.String(32))
    password = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=False)
    role = db.Column(db.String(32), default="BOOKMARK")
    registered_date = db.Column(db.DateTime, default=datetime.datetime.now)
    stocks = db.relationship('MStock', backref='author', lazy=True)

    @property
    def is_active(self):
        return self.active

    def is_authorized(self, required):
        return Role.is_authorized(required, self.role)

    @classmethod
    def info(cls, id):
        user = User.query.get(int(id))
        if user:
            info = {}
            for k, v in vars(user).items():
                if k[0] == '_' or k == 'password':
                    continue
                info[k] = v
            return info
        raise KeyError(f'ID={id} Is Not Exist.')

    @classmethod
    def update(cls, id, **kwargs):
        id = int(id)
        if id == 1:
            raise KeyError(f'Permission Error')
        user = User.query.get(int(id))
        for k, v in kwargs.items():
            if k in ['password', 'email']:
                KeyError(f'"{k}" Column Is Not Allowed.')
            if hasattr(user, k):
                setattr(user, k, v)
                continue
            raise KeyError(f'"{k}" Is Not Member.')
        db.session.commit()

    @classmethod
    def delete(cls, id):
        id = int(id)
        if id == 1:
            raise KeyError(f'Permission Error.')
        user = User.query.get(int(id))
        if user:
            db.session.delete(user)
            db.session.commit()
            return
        raise KeyError(f'ID={id} Is Not Exist.')


class MStock(db.Model):

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(8))
    name = db.Column(db.String(32))
    atime = db.Column(db.DateTime, default=datetime.datetime.now)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    algo_index = db.Column(db.Integer)
    __table_args__ = (db.UniqueConstraint('user_id', 'code',
                                          name='_user_id_code'),)

    @classmethod
    def delete(cls, user_id, code):
        item = MStock.query.filter_by(user_id=int(user_id), code=code).first()
        if item:
            db.session.delete(item)
            db.session.commit()
            return
        raise KeyError(f'Not Matched - USER ID={user_id} and CODE={code}')

    @classmethod
    def update(cls, user_id, code, name):
        user_id = int(user_id)
        item = MStock.query.filter_by(user_id=user_id, code=code).first()
        if item:
            item.atime = datetime.datetime.now()
        else:
            item = MStock(code=code, name=name, user_id=user_id)
        # try:
        db.session().add(item)
        db.session().commit()
        return item

    @classmethod
    def mark(cls, user_id, code, index):
        user_id = int(user_id)
        item = MStock.query.filter_by(user_id=user_id, code=code).first()
        if item:
            item.algo_index = None if index == 'null' else int(index)
            db.session().add(item)
            db.session().commit()
            return
        raise KeyError(f'Not Matched - USER ID={user_id} and CODE={code}')

    @classmethod
    def list(cls, user_id):
        now = datetime.datetime.now()
        from_date = DateTool.to_strfdate(now - relativedelta(days=30))
        query = MStock.query.filter_by(user_id=int(user_id))
        return query.filter(MStock.atime >= from_date)\
                    .order_by(MStock.atime.desc()).all()


class Reply:
    @classmethod
    def Success(cls, **kwargs):
        data = {}
        data['success'] = kwargs.get('success', True)
        data['message'] = kwargs.get('message', None)
        data['value'] = kwargs.get('value', None)
        return jsonify(data)

    @classmethod
    def Fail(cls, **kwargs):
        data = {}
        data['success'] = kwargs.get('success', False)
        data['message'] = kwargs.get('message', 'Failed')
        data['value'] = kwargs.get('value', None)
        return jsonify(data)

    @classmethod
    def Data(cls, data):
        if isinstance(data, dict):
            data['request'] = {}
            data['request']['url'] = request.url
            data['request']['path'] = request.path
            data['request']['method'] = request.method
        return data
