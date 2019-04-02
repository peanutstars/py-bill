# -*- coding: utf-8 -*-

import copy
import datetime
import os
import re
import sqlalchemy
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_

from pysp.sbasic import SFile
from pysp.sconf import SConfig
# from pysp.serror import SDebug
from pysp.ssql import SSimpleDB

from core.config import BillConfig
from core.connect import FDaum, FNaver, FKrx, FUnknown
from core.model import (StockDay, StockDayInvestor, StockDayShort,
                        ServiceProvider, QueryData)


class StockItemDB(SSimpleDB):
    class Error(Exception):
        pass
    # SQL_ECHO = True

    def __init__(self, **kwargs):
        self.db_file = kwargs.get('db_file')
        db_config = kwargs.get('db_config')
        super(StockItemDB, self).__init__(self.db_file, SConfig(db_config))

    @classmethod
    def factory(cls, code):
        bcfg = BillConfig()
        db_file = '{folder}/{code}.sqlite3'.format(
            folder=bcfg.get_value('_config.db.stock_folder'), code=code)
        SFile.mkdir(os.path.dirname(db_file))
        db_config = bcfg.get_value('_config.db.stock_yml')
        return cls(db_file=db_file, db_config=db_config)

    def update_candle(self, days):
        if len(days) == 0:
            return False
        data = []
        for i, d in enumerate(days):
            if type(d) is list:
                d = StockDay(*d)
            item = {
                'stamp': datetime.date(*[int(x) for x in d.stamp.split('.')]),
                'finance':  d.finance,
                'start':    d.start,
                'end':      d.end,
                'high':     d.high,
                'low':      d.low,
                'volume':   d.volume,
            }
            data.append(item)
        param = {
            'data': data,
            'only_insert': True,
        }
        return self.upsert_array('stock_day', **param)

    def update_investor(self, days):
        if len(days) == 0:
            return False
        data = []
        for i, d in enumerate(days):
            if type(d) is list:
                d = StockDayInvestor(*d)
            item = {
                'stamp': datetime.date(*[int(x) for x in d.stamp.split('.')]),
                'foreigner':    d.foreigner,
                'frate':        d.frate,
                'institute':    d.institute,
                'person':       d.person,
            }
            if i == 0:
                cols = ['stamp', 'foreigner', 'frate', 'institute', 'person']
                options = {
                    'wheres': {'stamp': item.get('stamp')}
                }
                rv = self.query('stock_day', *cols, **options)
                if not rv:
                    emsg = 'No Data, day field: {}'.format(item.get('stamp'))
                    raise StockItemDB.Error(emsg)
                inv = StockDayInvestor(*rv[0])
                if inv.foreigner == d.foreigner and inv.person == d.person:
                    return False
            data.append(item)
        return self.upsert_array('stock_day', data=data)

    def update_shortstock(self, days):
        if len(days) == 0:
            return False
        data = []
        for i, d in enumerate(days):
            if type(d) is list:
                d = StockDayShort(*d)
            item = {
                'stamp': datetime.date(*[int(x) for x in d.stamp.split('/')]),
                'short':       d.short,
                'shortamount': d.shortamount,
            }
            if i == 0:
                columns = ['stamp', 'short', 'shortamount']
                options = {
                    'wheres': {'stamp': item.get('stamp')}
                }
                rv = self.query('stock_day', *columns, **options)
                ds = StockDayShort(*rv[0])
                if ds.short is not None:
                    return False
            data.append(item)
        return self.upsert_array('stock_day', data=data)


class DataCollection:
    class Error(Exception):
        pass

    PROVIDER = {
        'daum':     FDaum,
        'naver':    FNaver,
        'krx':      FKrx,
    }

    def __init__(self):
        super(DataCollection, self).__init__()

    def get_provider(self, sp):
        return self.PROVIDER.get(sp.name, FUnknown)

    def collect_candle(self, sp, **kwargs):
        page = 0
        loop = True
        provider = self.get_provider(sp)
        sidb = StockItemDB.factory(sp.code)
        while loop:
            page += 1
            chunk = provider.get_chunk('day', code=sp.code, page=page)
            loop = sidb.update_candle(chunk)

    def collect_investor(self, sp, **kwargs):
        page = 0
        loop = True
        provider = self.get_provider(sp)
        sidb = StockItemDB.factory(sp.code)
        while loop:
            page += 1
            chunk = provider.get_chunk('dayinvestor', code=sp.code, page=page)
            loop = sidb.update_investor(chunk)

    def collect_shortstock(self, sp, **kwargs):
        page = 0
        loop = True
        provider = self.get_provider(sp)
        sidb = StockItemDB.factory(sp.code)
        codepool = provider.get_chunk('list')
        shortcode = 'A'+sp.code
        fullcode = provider.get_fullcode(codepool, shortcode)
        while loop:
            page += 1
            params = {
                'fcode': fullcode,
                'scode': shortcode,
                'page':  page,
            }
            chunk = provider.get_chunk('shortstock', **params)
            loop = sidb.update_shortstock(chunk)

    @classmethod
    def factory_provider(cls, code, pname):
        items = FKrx.get_chunk('list')
        acode = 'A'+str(code)
        if pname not in cls.PROVIDER:
            cls.Error(f'Not Exist Provider Name: {pname}')
        for item in items:
            if acode == item['short_code']:
                return ServiceProvider(name=pname,
                                       codename=item['codeName'], code=code)
        raise cls.Error(f'Not Exist Code: {code}')

    def collect(self, code):
        sp = self.factory_provider(code, 'naver')
        self.collect_candle(sp)
        self.collect_investor(sp)
        sp = self.factory_provider(code, 'krx')
        self.collect_shortstock(sp)


class StockQuery:
    class Error(Exception):
        pass

    class TradingAccumulator:
        def __init__(self, items, colnames):
            '''
            @param items    It is accumulator List to use,
                            the first one is not accumulated and
                            the last one is the tread amount of short stock
            @param colnames It is the column names of the field.
            '''
            self.ilist = []
            for iname in items:
                self.ilist.append(colnames.index(iname))
            self.rows = None
            self.amount = None

        def update(self, field):
            if self.rows:
                rows = [r for i, r in enumerate(field) if i in self.ilist]
                # print('!!', rows)
                for i, r in enumerate(rows[:-1]):
                    if i == 0:
                        self.rows[i] = rows[i]
                        continue
                    self.rows[i] += rows[i]
                # print('##', self.rows, rows)
                if rows[-1]:
                    if self.rows[-1]:
                        self.rows[-1] += (rows[-1] - self.amount)
                    else:
                        self.rows[-1] = (rows[-1] - self.amount)
                    self.amount = field[self.ilist[-1]]
                else:
                    self.rows[-1] = None
            else:
                rows = [r for i, r in enumerate(field) if i in self.ilist[:-1]]
                rows.append(None)
                # print('##', rows)
                self.amount = field[self.ilist[-1]]
                self.rows = rows
            # print('  ', self.rows)
            return copy.deepcopy(self.rows)

    PATTERN_DATE = re.compile(r'([\d]{4})\D*([\d]{1,2})\D*([\d]{1,2})')

    @classmethod
    def to_datetime(cls, date):
        m = cls.PATTERN_DATE.match(date)
        if m.lastindex == 3:
            datelist = [int(m.group(x)) for x in range(1, 4)]
            return datetime.datetime(*datelist)
        raise cls.Error(f'Unknown Date Format: {date}')

    @classmethod
    def to_strfdate(cls, odate=None, **kwargs):
        '''
            param @ format      String format of date, default is '%Y%m%d'
        '''
        format = kwargs.get('format', '%Y-%m-%d')
        if odate is None:
            return datetime.datetime.now().strftime(format)
        if isinstance(odate, datetime.datetime):
            return odate.strftime(format)
        raise cls.Error('Unknown object: {}'.format(odate.__class__.__name__))

    @classmethod
    def raw_data(cls, sidb, **kwargs):
        '''
        @param sdate        Start date, default is current local time.
                            Format is YYYY-MM-DD, YYYY.MM.DD or YYYYMMDD.
        @param edate        End date, default is current local time.
                            Format is YYYY-MM-DD, YYYY.MM.DD or YYYYMMDD.
        @param months       The past duration time, unit is month.
                            Default is 3 months.
        @return             List of list.
        '''
        start_date = kwargs.get('sdate', cls.to_strfdate())
        end_date = kwargs.get('edate', None)
        months = kwargs.get('months', 3)
        date_end = cls.to_datetime(start_date)
        if end_date:
            date_start = cls.to_datetime(end_date)
        else:
            date_start = date_end - relativedelta(months=months)
        if (date_start-date_end).days >= 0:
            date_start, date_end = date_end, date_start
        # print('##', date_start, date_end)

        tablename = 'stock_day'
        colnames = sidb.get_colnames(tablename)
        table = sidb.get_table(tablename)
        sql = sqlalchemy.sql.select(table.c).where(
            and_(cls.to_strfdate(date_start) <= table.c.stamp,
                 table.c.stamp <= cls.to_strfdate(date_end))).\
            order_by(table.c.stamp.asc())
        strsql = sidb.to_sql(sql)
        try:
            fields = sidb.session.query(sql).all()
        except Exception as e:
            raise cls.Error(f'{e}')
        return QueryData(colnames=colnames,
                         fields=[list(x) for x in fields], sql=strsql)

    @classmethod
    def get_investor_trading_trand(cls, sidb, **kwargs):
        qdata = cls.raw_data(sidb, **kwargs)
        items = ['stamp', 'foreigner', 'institute', 'person', 'shortamount']
        tradedata = QueryData(colnames=items, sql=qdata.sql)
        tacc = cls.TradingAccumulator(tradedata.colnames, qdata.colnames)
        for field in qdata.fields:
            fieldacc = tacc.update(field)
            tradedata.fields.append(fieldacc)
        # print(tradedata.colnames)
        # print(tradedata.fields)
        # print(tradedata.sql)
        return tradedata
