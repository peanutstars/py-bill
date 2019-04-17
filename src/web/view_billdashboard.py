# import codecs
# import os
import datetime

from dateutil.relativedelta import relativedelta
from flask import render_template, flash, abort, session, request
from flask_login import login_required

from . import app, db
from .model import MStock, Reply
# from core.finance import BillConfig
from core.helper import DateTool
from core.connect import FKrx, Http
from core.finance import DataCollection, StockItemDB, StockQuery
from core.manager import Collector


def get_recent_stocks():
    if 'user_id' not in session:
        return []
    now = datetime.datetime.now()
    # to_date = DateTool.to_strfdate(now)
    from_date = DateTool.to_strfdate(now - relativedelta(days=30))
    recent_stock = MStock.query.filter_by(user_id=session['user_id'])
    recent_stock = recent_stock.filter(MStock.atime >= from_date)\
                               .order_by(MStock.atime.desc()).all()
    # for recent in recent_stock:
    #     print(recent.name, recent.code, recent.atime)
    return recent_stock


def marking_recent_stock(code, name):
    recent = MStock.query.filter_by(
                user_id=session['user_id'], code=code).first()
    if recent:
        recent.atime = datetime.datetime.now()
    else:
        recent = MStock(code=code, name=name, user_id=int(session['user_id']))
    dbss = db.session()
    try:
        dbss.add(recent)
        dbss.commit()
    except Exception as e:
        flash(f'DB Error - {e}')


@app.route('/bill/dashboard')
@login_required
def bill_dashboard():
    recent_stocks = get_recent_stocks()
    return render_template('pages/bill_dashboard.html',
                           recent_stocks=recent_stocks)


@app.route('/bill/stock/', defaults={"code": None})
@app.route('/bill/stock/<code>')
@login_required
def bill_stock(code):
    if code is None:
        recent_stocks = get_recent_stocks()
        return render_template('pages/bill_stock.html',
                               recent_stocks=recent_stocks)
    try:
        provider = DataCollection.factory_provider(code, 'krx')
    except DataCollection.Error:
        abort(404)
    extra_info = {'code': code,
                  'codename': provider.codename}
    marking_recent_stock(code, provider.codename)
    recent_stocks = get_recent_stocks()
    return render_template('pages/bill_stock_code.html',
                           extra_info=extra_info, recent_stocks=recent_stocks)


@app.route('/ajax/stock/list', methods=['GET', 'POST'])
@login_required
def ajax_stock_list():
    return Reply.Success(value=FKrx.get_chunk('list'))


@app.route('/ajax/stock/item/<code>/investor/<month>', methods=['GET', 'POST'])
@login_required
def ajax_stock_item_investor(code, month):
    collector = Collector()
    with collector.lock:
        if collector.is_working(code):
            return Reply.Fail(message="Not Ready, Still Be Collecting Data.")
        try:
            sidb = StockItemDB.factory(code)
            tdata = StockQuery.get_investor_trading_trand(
                                                    sidb, months=int(month))
            if len(tdata.fields) == 0:
                print('QueryData.fields == 0')
                raise
        except Exception:
            collector.collect(code)
            return Reply.Fail(message="Requested Collector To Collect Data.")
        return Reply.Success(value=Reply.Data(tdata))


@app.route('/ajax/proxy', methods=['POST'])
@login_required
def ajax_proxy():
    url = request.get_json().get('url')
    method = request.get_json().get('method', 'GET')
    datatype = request.get_json().get('datatype', None)
    # Select a method function
    http = Http.get
    if method == 'POST':
        http = Http.post
    # Select a data type
    params = {}
    if datatype == 'json':
        params['json'] = True
    if datatype == 'text':
        params['text'] = True
    # Request
    try:
        rv = http(url, **params)
        return Reply.Success(value=rv)
    except Exception as e:
        return Reply.Fail(message=str(e))
