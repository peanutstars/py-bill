# import codecs
import os
import datetime

from flask import render_template, flash, abort, session, request
from flask_login import login_required

from . import app, db
from .account import role_required
from .model import User, MStock, Reply
# from core.finance import BillConfig
from core.model import Dict
from core.config import BillConfig
from core.connect import FKrx, Http
from core.finance import DataCollection, StockItemDB, StockQuery
from core.finalgo import IterAlgo
from core.manager import Collector


_algo_folder = BillConfig().get_value('config.db.stock.folder') + '/algo/'


@app.route('/bill/dashboard')
@login_required
@role_required('STOCK')
def bill_dashboard():
    recent_stocks = MStock.list(session['user_id'])
    return render_template('pages/bill_dashboard.html',
                           recent_stocks=recent_stocks)


@app.route('/bill/stock/', defaults={"code": None})
@app.route('/bill/stock/<code>')
@login_required
@role_required('STOCK')
def bill_stock(code):
    if code is None:
        recent_stocks = MStock.list(session['user_id'])
        return render_template('pages/bill_stock.html',
                               recent_stocks=recent_stocks)
    try:
        provider = DataCollection.factory_provider(code, 'krx')
    except DataCollection.Error:
        abort(404)

    algo_index = None
    m = MStock.query.filter_by(user_id=1, code=code).first()
    if m and m.algo_index:
        algo_index = m.algo_index

    try:
        m = MStock.update(session['user_id'], code, provider.codename)
        if m and m.algo_index:
            algo_index = m.algo_index
    except Exception as e:
        flash(f'DB Error - {e}')

    extra_info = {
        'code': code,
        'codename': provider.codename,
        'algo': os.path.exists(_algo_folder+f'{code}.brief'),
        'algo_index': algo_index,
        }
    recent_stocks = MStock.list(session['user_id'])
    return render_template('pages/bill_stock_code.html',
                           extra_info=extra_info, recent_stocks=recent_stocks)


@app.route('/ajax/stock/list', methods=['GET', 'POST'])
@login_required
@role_required('STOCK')
def ajax_stock_list():
    return Reply.Success(value=FKrx.get_chunk('list'))


@app.route('/ajax/stock/item/<code>', methods=['DELETE'])
@login_required
@role_required('STOCK')
def ajax_stock_item(code):
    if request.method == 'DELETE':
        try:
            MStock.delete(session['user_id'], code)
            return Reply.Success(value={'code': code})
        except Exception as e:
            return Reply.Fail(message=str(e))
    return Reply.Fail(message=f'Not Support Method[{request.method}]')


@app.route('/ajax/stock/item/<code>/adjust-stock-split', methods=['POST'])
@login_required
@role_required('ADMIN')
def ajax_stock_adjust_stock_split(code):
    collector = Collector()
    # colnames = request.get_json().get('colnames', [])
    with collector.lock:
        if collector.is_working(code):
            return Reply.Fail(message="Not Ready, Still be Collecting Data.")
        try:
            sidb = StockItemDB.factory(code)
            options = Dict()
            ratio = float(request.get_json().get('ratio'))
            sdate = request.get_json().get('sdate')
            if 'edate' in request.get_json():
                options.edate = request.get_json().get('edate')
            rv = sidb.adjust_split_stock(ratio, sdate, **options)
            app.logger.debug(f'adjust_split_stock rv={rv} code={code} ratio={ratio} sdate={sdate}')
        except Exception as e:
            return Reply.Fail(message=f"Error adjust_split_stock, {e}")
        if rv:
            return Reply.Success()
        return Reply.Fail(message='No Data or Failed to adjust')


@app.route('/ajax/stock/item/<code>/algo-brief', methods=['POST'])
@login_required
@role_required('STOCK')
def ajax_stock_algo_brief(code):
    algo = os.path.exists(_algo_folder+f'{code}.brief')
    if algo is False:
        return Reply.Fail(message='No Data of Algo Brief')
    data = IterAlgo.load_brief(code, folder=_algo_folder)
    return Reply.Success(value=Reply.Data(data))


@app.route('/ajax/stock/item/<code>/algo-index-mark/<index>', methods=['POST'])
@login_required
@role_required('STOCK')
def ajax_stock_algo_index_mark(code, index):
    try:
        MStock.mark(session['user_id'], code, index)
    except Exception as e:
        emsg = f'DB Error - {e}'
        flash(emsg)
        return Reply.Fail(message=emsg)
    return Reply.Success()


@app.route('/ajax/stock/item/<code>/columns/<month>', methods=['GET', 'POST'])
@login_required
@role_required('STOCK')
def ajax_stock_query_columns(code, month):
    collector = Collector()
    # colnames = request.get_json().get('colnames', [])
    with collector.lock:
        if collector.is_working(code):
            return Reply.Fail(message="Not Ready, Still be Collecting Data.")
        try:
            sidb = StockItemDB.factory(code)
            tdata = StockQuery.raw_data_of_each_colnames(
                                sidb, months=int(month), **request.get_json())
            if len(tdata.fields) == 0:
                raise Exception
        except Exception:
            collector.collect(code)
            return Reply.Fail(message="Collector is Gathering Data.")
        return Reply.Success(value=Reply.Data(tdata))


# @app.route('/ajax/stock/item/<code>/simulation/<month>', methods=['GET', 'POST'])
# @login_required
# @role_required('STOCK')
# def ajax_stock_simulation_table(code, month):
#     collector = Collector()
#     with collector.lock:
#         if collector.is_working(code):
#             return Reply.Fail(message="Not Ready, Still be Collecting Data.")
#         try:
#             # colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
#             sidb = StockItemDB.factory(code)
#             tdata = StockQuery.raw_data_of_each_colnames(
#                                 sidb, months=int(month), **request.get_json())
#             if len(tdata.fields) == 0:
#                 raise Exception
#             algo = AlgoTable(tdata)
#             pdata = algo.process()
#         except Exception:
#             collector.collect(code)
#             return Reply.Fail(message="Collector is Gathering Data.")
#         return Reply.Success(value=Reply.Data(pdata))        


@app.route('/ajax/stock/item/<code>/simulation/<index>', methods=['POST'])
@login_required
@role_required('STOCK')
def ajax_stock_simulation_table(code, index):
    collector = Collector()
    with collector.lock:
        if collector.is_working(code):
            return Reply.Fail(message="Not Ready, Still be Collecting Data.")
        try:
            # colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
            pdata = IterAlgo.compute_index(code, index, **request.get_json())
            # sidb = StockItemDB.factory(code)
            # tdata = StockQuery.raw_data_of_each_colnames(
            #                     sidb, months=int(month), **request.get_json())
            # if len(tdata.fields) == 0:
            #     raise Exception
            # algo = AlgoTable(tdata)
            # pdata = algo.process()
        except Exception:
            collector.collect(code)
            return Reply.Fail(message="Collector is Gathering Data.")
        return Reply.Success(value=Reply.Data(pdata))        


@app.route('/ajax/stock/item/<code>/simulation-chart/<index>', methods=['POST'])
@login_required
@role_required('STOCK')
def ajax_stock_simulation_chart(code, index):
    collector = Collector()
    with collector.lock:
        if collector.is_working(code):
            return Reply.Fail(message="Not Ready, Still be Collecting Data.")
        try:
            # colnames = ['stamp', 'start', 'low', 'high', 'end', 'volume']
            pdata = IterAlgo.compute_index_chart(code, index, **request.get_json())
            # sidb = StockItemDB.factory(code)
            # tdata = StockQuery.raw_data_of_each_colnames(
            #                     sidb, months=int(month), **request.get_json())
            # if len(tdata.fields) == 0:
            #     raise Exception
            # algo = AlgoTable(tdata)
            # pdata = algo.process()
        except Exception:
            collector.collect(code)
            return Reply.Fail(message="Collector is Gathering Data.")
        return Reply.Success(value=Reply.Data(pdata))        


@app.route('/ajax/proxy', methods=['POST'])
@login_required
def ajax_proxy():
    _data_type = {
        'json': {'json': True},
        'text': {'text': True},
    }
    reqjson = request.get_json()
    url = reqjson.get('url')
    method = reqjson.get('method', 'GET')
    datatype = reqjson.get('datatype', None)
    # Init Parameters
    kwargs = {
        'headers':  reqjson.get('headers', {}),
        'params':   reqjson.get('params', {}),
    }
    kwargs.update(_data_type.get(datatype, {}))
    if 'duration' in reqjson:
        kwargs['duration'] = reqjson.get('duration')
    # Request
    try:
        rv = Http.proxy(method, url, **kwargs)
        return Reply.Success(value=rv)
    except Exception as e:
        return Reply.Fail(message=str(e))
