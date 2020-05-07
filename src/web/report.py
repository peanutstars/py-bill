import datetime
import json

from web import app
from web.model import Notify, User, MStock
from flask import render_template
from core.finalgo import IterAlgo
from core.finance import BillConfig
from core.gmail import Gmail

from pysp.serror import SCDebug
from pysp.sbasic import SSingleton, Dict


class ComputeAlgo(Dict, metaclass=SSingleton):
    def __init__(self, *args, **kwargs):
        super(ComputeAlgo, self).__init__(*args, **kwargs)
        self.stamp = datetime.datetime.now()

    def _key(self, code, index):
        return f'{code}:{index}'

    def compute(self, code, index):
        key = self._key(code, index)
        data = self.get(key, None)
        if data:
            return data
        self[key] = IterAlgo.compute_index_chart(code, index)
        del self[key]['fields']
        return self[key]

    def _compute_with_user(self):
        self.clear()
        self.stamp = datetime.datetime.now()
        for user in User.query.all():
            if not user.is_authorized('STOCK'):
                continue
            for stock in MStock.list(user.id, order='code'):
                # print(user.username, stock.code)
                index = None
                m = MStock.query.filter_by(user_id=1, code=stock.code).first()
                if m and m.algo_index:
                    index = m.algo_index
                if index:
                    # print(user.id, stock.code, index)
                    self.compute(stock.code, index)

    def compute_all(self):
        with app.app_context():
            self._compute_with_user()
    

computealgo = ComputeAlgo()



class Notice(SCDebug):
    def __init__(self):
        super(Notice, self).__init__()
        self.cache = computealgo

    def __call__(self):
        return self.dispatch()

    def compute_algo(self, user):
        items = {}
        for stock in MStock.list(user.id, order='code'):
            algo_index = None
            m = MStock.query.filter_by(user_id=1, code=stock.code).first()
            if m and m.algo_index:
                algo_index = m.algo_index
            if algo_index:
                # print(user.id, stock.code, algo_index)
                item = self.cache.compute(stock.code, algo_index)
                item.name = stock.name
                items[stock.code] = item
        return items
    
    def stamp(self):
        return self.cache.stamp

    def render_html(self, items, user):
        # Convert CSS to inline CSS
        # Refer to https://templates.mailchimp.com/resources/inline-css/
        
        def url_for(endpoint, **kwargs):
            fn = kwargs.get('filename', None)
            url = BillConfig().get_value('user.url', '')
            if endpoint and endpoint[0] == '.':
                endpoint = endpoint.split('.')[-1]
            return url+(endpoint if fn is None else (endpoint+'/'+fn))
        
        def format_number(num):
            return f'{num:,}'

        context = Dict()
        context.function.url_for = url_for
        context.function.format_number = format_number
        context.now = datetime.datetime.now()
        context.items = items
        context.user = user
        return render_template('report/notice.html', **context) 

    def dispatch(self):
        with app.app_context():
            for user in User.query.all():
                if not user.is_authorized('STOCK'):
                    continue
                if user.notify == 0:
                    continue

                send_mode = 0
                items = self.compute_algo(user)
                if not items:
                    # The user has no list, who no visit during 45 days.
                    continue

                html = self.render_html(items, user)
                email = user.email
                if user.email == 'admin':
                    email = BillConfig().get_value('admin.email', None)

                if Notify.has_notify('STOCK_EVENT', user.notify):
                    for k, v in items.items():
                        # print('@@@', json.dumps(v, indent=2))
                        if v.chart.today.bpoint or v.chart.today.spoint:
                            send_mode = 2
                if send_mode == 0 and Notify.has_notify('STOCK_ALL', user.notify):
                    send_mode = 1
                app.logger.debug(f'@@@ {user.username}, {email}, {user.notify}, {send_mode}')
                self.dprint(f'@@@ {user.username}, {email}, {user.notify}, {send_mode}')

                if send_mode > 0:
                    title = {
                        1: 'Be Happy !! - Stock Daily Report',
                        2: '[Alarm] Be Happy !! - Stock Event'
                    }
                    Gmail.send(email, title.get(send_mode), html)


# notice = Notice()