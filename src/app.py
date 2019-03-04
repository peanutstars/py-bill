import os
from flask_debugtoolbar import DebugToolbarExtension
from werkzeug.security import generate_password_hash
from pysp.sbasic import SFile

from web import app, db, login_manager
from web.model import User
from web.view_index import index
from web.view_account import account
from web.view_billdashboard import bill_dashboard
from core.finance import BillConfig



cur_dir = os.path.dirname(os.path.abspath(__file__))
db_file = f'{cur_dir}/db.sqlite3'

app.config['SECRET_KEY'] = 'Thisissupposedtobesecret!'
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_file}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'account_login'

bcfg = BillConfig()
bcfg.set_value('folder.config', cur_dir+'/config/')
SFile.mkdir(bcfg.get_value('folder.user_config'))


if __name__ == '__main__':
    app.debug = True
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    DebugToolbarExtension(app)

    if not os.path.exists(db_file):
        with app.app_context():
            db.create_all()
            admin = User(email='admin', username='Supervisor',
                            password=generate_password_hash('admin'))
            db.session.add(admin)
            db.session.commit()

    app.run(host='0.0.0.0', port=8888)
