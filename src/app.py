
import logging
import os
import sys

from logging.handlers import RotatingFileHandler
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.security import generate_password_hash
from pysp.sbasic import SFile

from web import app, db, login_manager
from web.model import User
from web.view_index import index
from web.view_account import account
from web.view_billdashboard import bill_dashboard
from core.finance import BillConfig
from core.manager import Collector


_DEBUG = False
if 'DEBUG_PYTHON' in os.environ:
    _DEBUG = True


def init_logger(app):
    log_dir = BillConfig().get_value('folder.log')
    log_file = 'web-app-log'
    log_level = logging.DEBUG
    log_format = '%(asctime)s] %(message)s'
    log_bytes = 5*1024*1024
    log_count = 10

    hdl = RotatingFileHandler(log_dir+log_file,
                              maxBytes=log_bytes, backupCount=log_count)
    hdl.setFormatter(logging.Formatter(log_format))
    # hdl.setLevel(log_level)

    log = logging.getLogger()
    log.addHandler(hdl)
    log.setLevel(log_level)
    app.logger.info("===== web application start =====")


cur_dir = os.path.dirname(os.path.abspath(__file__))
# db_file = f'{cur_dir}/db.sqlite3'
db_file = '/var/pybill/db.sqlite3'

# Configure Flask
app.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure DB
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'account_login'

bcfg = BillConfig()
bcfg.set_value('folder.config', cur_dir+'/config/')
SFile.mkdir(bcfg.get_value('folder.user_config'))

# Create a admin account
if not os.path.exists(db_file):
    with app.app_context():
        db.create_all()
        admin = User(email='admin',
                     username='Supervisor',
                     password=generate_password_hash('admin'),
                     active=True,
                     role="ADMIN")
        db.session.add(admin)
        db.session.commit()


if _DEBUG is False:
    init_logger(app)

# Manager
# XXX: Issue One
# Collector has thread and it is executed in the initialization process.
# If executed the user thread before uwsgi is to done initialization.
# The user thread is something wrong, it is as if two objects were created.
# XXX: Issue Two
# Value of option threads of uwsgi is to set 1 over,
# the Collector object is created as much as that vlaue.
# Collector()


if __name__ == '__main__':
    if _DEBUG is True:
        app.debug = True
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        DebugToolbarExtension(app)

    try:
        app.run(host='0.0.0.0', port=8000, use_reloader=False)
    finally:
        Collector().quit()
