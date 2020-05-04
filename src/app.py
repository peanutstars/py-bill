
import logging
import os
import sys

from logging.handlers import RotatingFileHandler
from flask_debugtoolbar import DebugToolbarExtension
from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from werkzeug.security import generate_password_hash
from pysp.sbasic import SFile

from web import app, db, login_manager
from web.model import User
from web.view_index import index
from web.view_account import account
from web.view_billdashboard import bill_dashboard
from web.report import computealgo, Notice
from core.finance import BillConfig
from core.manager import Collector


def init_logger(app):
    log_level = logging.DEBUG
    log_format = '%(asctime)s] %(message)s'
    # log_dir = BillConfig().get_value('folder.log')
    # log_file = 'web-app-log'
    # log_bytes = 5*1024*1024
    # log_count = 10

    # hdl = RotatingFileHandler(log_dir+log_file,
    #                           maxBytes=log_bytes, backupCount=log_count)
    # hdl.setFormatter(logging.Formatter(log_format))
    # # hdl.setLevel(log_level)

    hdl = logging.StreamHandler()
    hdl.setFormatter(logging.Formatter(log_format))

    log = logging.getLogger()
    log.handers = []
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

migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

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

computealgo.compute_all()

init_logger(app)


if __name__ == '__main__':
    # run test this
    # uwsgi --ini uwsgi.debug.ini

    # run test this with debug
    # DEBUG=1 uwsgi --ini uwsgi.debug.ini

    # run cli command for db migrate
    manager.run()
else:
    # Manager
    # XXX: Issue One
    # Collector has thread and it is executed in the initialization process.
    # If executed the user thread before uwsgi is to done initialization.
    # The user thread is something wrong, it is as if two objects were created.
    # XXX: Issue Two
    # Value of option threads of uwsgi is to set 1 over,
    # the Collector object is created as much as that vlaue.
    # Solved Issue - run uwsgi with lazy-apps option.
    Collector()

    # Debug Mode
    if 'DEBUG' in os.environ:
        app.debug = True
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        DebugToolbarExtension(app)      
