# import codecs
# import os
#
from flask import render_template, abort
from flask_login import login_required

from . import app
from .model import Reply
# from core.finance import BillConfig
from core.connect import FKrx
from core.finance import DataCollection, StockItemDB, StockQuery
from core.manager import Collector


@app.route('/bill/dashboard')
@login_required
def bill_dashboard():
    return render_template('pages/bill_dashboard.html')


@app.route('/bill/stock/', defaults={"code": None})
@app.route('/bill/stock/<code>')
@login_required
def bill_stock(code):
    if code is None:
        return render_template('pages/bill_stock.html')
    try:
        provider = DataCollection.factory_provider(code, 'krx')
    except DataCollection.Error:
        abort(404)
    extra_info = {'code': code,
                  'codename': provider.codename}
    return render_template('pages/bill_stock_code.html', extra_info=extra_info)


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
