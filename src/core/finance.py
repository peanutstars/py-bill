# -*- coding: utf-8 -*-

import copy
import datetime
import os
import sqlalchemy
from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, Column

from pysp.sbasic import SFile
from pysp.sconf import SConfig
# from pysp.serror import SDebug
from pysp.ssql import SSimpleDB

from core.helper import DateTool
from core.cache import FCache
from core.config import BillConfig
from core.connect import FDaum, FNaver, FKrx, FUnknown
from core.model import (StockDayInvestor, StockDayShort, ServiceProvider, QueryData)


class DataETF(dict):
    '''
    ETF List
    '''
    def __init__(self, *args, **kwargs):
        super(DataETF, self).__init__(*args, **kwargs)
        self['069500'] = ServiceProvider(name='naver', codename='KODEX200',   code='069500')
        self['114800'] = ServiceProvider(name='naver', codename='KODEX인버스', code='114800')
    
    def get(self, name, defval):
        for code in self:
            item = self[code]
            if name == item.code or name == item.codename:
                return item
        return defval


_DataETF = DataETF()


class StockItemDB(SSimpleDB):
    '''
    Stock Item Database - It manage the db.
    '''
    class Error(Exception):
        pass
    # SQL_ECHO = True

    def __init__(self, **kwargs):
        self.db_file = kwargs.get('db_file')
        db_config = kwargs.get('db_config')
        super(StockItemDB, self).__init__(self.db_file, SConfig(db_config))

    @classmethod
    def factory(cls, code):
        '''Get handler of the db of Stock Code.'''
        bcfg = BillConfig()
        db_file = '{folder}/{code}.sqlite3'.format(
            folder=bcfg.get_value('config.db.stock.folder'), code=code)
        SFile.mkdir(os.path.dirname(db_file))
        db_config = bcfg.get_value('config.db.stock.yml')
        return cls(db_file=db_file, db_config=db_config)

    def update_candle(self, days):
        '''
        Update the candle data of stock.
        The columns are stamp, finance, start, end, high, low and volume.
            stamp - YYYY-MM-DD
            finance - Company name of finance.
            start - Start Price
            end - End Price
            high - High Price
            low - Low Price
            volume - Trading Volume
        '''
        if len(days) == 0:
            return False
        data = []
        for i, d in enumerate(days):
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
        '''
        Update the investor data of stock.
        The columns are stamp, foreigner, frate, institute and person.
            stamp - YYYY-MM-DD
            foreigner - Trading volume of Foreigner
            frate - The retention rate of Foreigner in the whole, Unit is percent.
            institute - Trading volume of Institute
            person - Trading volume of Person
        '''
        if len(days) == 0:
            return False
        data = []
        for i, d in enumerate(days):
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
                    emsg = f'No Data, day field: {item.get("stamp")} - {self.db_file}'
                    raise StockItemDB.Error(emsg)
                inv = StockDayInvestor.from_list(*rv[0])
                if inv.foreigner == d.foreigner and inv.person == d.person:
                    return False
            data.append(item)
        return self.upsert_array('stock_day', data=data)

    def update_shortstock(self, days):
        '''
        Update short-stock data.
        The columns are stamp, short and shortamount.
            stamp - YYYY-MM-DD
            short - Trading volume of Short-Stock
            shortamount - Accumulation amount of Short-Stock
        '''
        if len(days) == 0:
            return False
        data = []
        for i, d in enumerate(days):
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
                ds = StockDayShort.from_list(*rv[0])
                if ds.short is not None:
                    return False
            data.append(item)
        return self.upsert_array('stock_day', data=data)

    def adjust_split_stock(self, ratio, sdate, **kwargs):
        '''
        Modify/Adjust each Stock columns due to stock split.

        Args
            :ratio integer/float: Split ratio
            :sdate string-date: Splitted date, YYYY-MM-DD

        Stock A is 1000 won yesterday, but now is 100 won, the whole volume increased 10 times.
        ratio is 10, sdate is YYYY-MM-DD

        start, end, high, low 
            - Divide a ratio value to each columns which applied before YYYY-MM-DD date.
        volume, foreigner, institute, person, short, shortamount 
            - Multiply a ratio value to each columns which applied before YYYY-MM-DD date.
        '''
        def adjust_data(idivs, imuls, field):
            for i in range(len(field)):
                if i in idivs:
                    if field[i]:
                        field[i] = int(field[i]/ratio)
                if i in imuls:
                    if field[i]:
                        field[i] = int(field[i]*ratio)
            return field
        
        edate = kwargs.get('edate', '1970-01-01')
        divcolnames = ['start', 'end', 'high', 'low',]
        mulcolnames = ['volume', 'foreigner', 'institute', 'person', 'short', 'shortamount']
        date_start = DateTool.to_datetime(sdate)
        date_end =  DateTool.to_datetime(edate)
        if (date_start-date_end).days >= 0:
            date_start, date_end = date_end, date_start

        # print('@@', ratio, date_start, date_end, )
        tablename = 'stock_day'
        # colnames = self.get_colnames(tablename)
        colnames = ['stamp'] + list(set(divcolnames+mulcolnames))
        columns = [Column(x) for x in colnames]
        table = self.get_table(tablename)
        sql = sqlalchemy.sql.select(columns).where(
            and_(DateTool.to_strfdate(date_start) <= table.c.stamp,
                 table.c.stamp <= DateTool.to_strfdate(date_end))).\
            order_by(table.c.stamp.asc())
        try:
            fields = self.session.query(sql).all()
        except Exception as e:
            # print('@@', 'Query Error')
            raise StockItemDB.Error(f'{e}')
        
        idivs = [colnames.index(x) for x in divcolnames]
        imuls = [colnames.index(x) for x in mulcolnames]
        data = []
        # print('@@', 'Query', len(fields), len(data))
        for i, v in enumerate(fields):
            # print(i, v, end=':')
            v = adjust_data(idivs, imuls, list(v))
            # print(v)
            data.append(dict(zip(colnames, v)))
        # print(str(data))
        rv = self.upsert_array(tablename, data=data)
        FCache().clear()
        return rv


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

    @classmethod
    def get_provider(cls, sp):
        return cls.PROVIDER.get(sp.name, FUnknown)

    @classmethod
    def collect_candle(cls, sp, **kwargs):
        '''
        Collecting the candle data table from the web page.
        The index of table is started from 1 to end of page or until duplicate data.

        Args
            :sp object: DataCollection.PROVIDER element
        Kwargs
            :wkstate object: worker state object - in case call this function by worker.
        '''
        page = 0
        loop = True
        wkstate = kwargs.get('wkstate', None)
        provider = cls.get_provider(sp)
        sidb = StockItemDB.factory(sp.code)
        while loop:
            if wkstate and wkstate.is_run() is False:
                break
            page += 1
            chunk = provider.get_chunk('day', code=sp.code, page=page)
            if page == 1 and not chunk:
                print(f'[[FAIL]] Getting Day Data of Stock')
            loop = sidb.update_candle(chunk)

    @classmethod
    def collect_investor(cls, sp, **kwargs):
        '''
        Collecting the investor data table from the web page.
        The index of table is started from 1 to end of page or until duplicate data.

        Args
            :sp object: DataCollection.PROVIDER element
        Kwargs
            :wkstate object: worker state object - in case call this function by worker.
        '''
        page = 0
        loop = True
        wkstate = kwargs.get('wkstate', None)
        provider = cls.get_provider(sp)
        sidb = StockItemDB.factory(sp.code)
        while loop:
            if wkstate and wkstate.is_run() is False:
                break
            page += 1
            chunk = provider.get_chunk('dayinvestor', code=sp.code, page=page)
            loop = sidb.update_investor(chunk)

    @classmethod
    def collect_shortstock(cls, sp, **kwargs):
        '''
        Collecting the short-stock data table from the web page.
        The index of table is started from 1 to end of page or until duplicate data.

        Args
            :sp object: DataCollection.PROVIDER element
        Kwargs
            :wkstate object: worker state object - in case call this function by worker.
        '''
        if _DataETF.get(sp.code, None):
            # ETF have not the short stock.
            return
        page = 0
        loop = True
        wkstate = kwargs.get('wkstate', None)
        provider = cls.get_provider(sp)
        sidb = StockItemDB.factory(sp.code)
        codepool = provider.get_chunk('list')
        shortcode = sp.code # 'A'+sp.code
        fullcode = provider.get_fullcode(codepool, shortcode)
        codename = provider.get_codeName(codepool, shortcode)
        while loop:
            if wkstate and wkstate.is_run() is False:
                break
            page += 1
            params = {
                'fcode': fullcode,
                'scode': shortcode,
                'codeName': codename,
                'page':  page,
            }
            chunk = provider.get_chunk('shortstock', **params)
            if page == 1 and not chunk:
                print(f'[[FAIL]] Getting Day Data of Short Stock')
            loop = sidb.update_shortstock(chunk)


    @classmethod
    def factory_provider(cls, code, pname):
        '''
        Return ServiceProvider with code and provider name.

        Args
            :code String: String number of Stock Code or Stock Name
            :pname String: Provider name
        '''

        provider = _DataETF.get(code, None)
        if provider:
            return provider

        ## Number Form : 001800
        items = FKrx.get_chunk('list')
        # acode = 'A'+str(code)
        acode = str(code)
        if pname not in cls.PROVIDER:
            cls.Error(f'Not Exist Provider Name: {pname}')
        print(f"######## CODE {code}")
        for item in items:
            ## item 2019.     : {'full_code': 'KR7001800002', 'short_code': 'A001800', 'codeName': '오리온홀딩스', 'marketName': 'KOSPI'}
            ## item 2021.1.17 : {'full_code': 'KR7030200000', 'short_code': '030200',  'codeName': 'KT', 'marketCode': 'STK', 'marketName': 'KOSPI'}
            if acode == item['short_code']:
                return ServiceProvider(name=pname, codename=item['codeName'], code=code)
            if code == item['codeName']:
                # return ServiceProvider(name=pname, codename=item['codeName'], code=item['short_code'][1:])
                return ServiceProvider(name=pname, codename=item['codeName'], code=item['short_code'])
        
        raise cls.Error(f'Not Exist Code: {code}')


    @classmethod
    def get_name_of_code(cls, code):
        '''Convert the code number to the code name(Stock Name).'''
        sp = cls.factory_provider(code, 'krx')
        provider = cls.get_provider(sp)
        shortcode = code # 'A'+code
        for item in provider.get_chunk('list'):
            if item['short_code'] == shortcode:
                return item['codeName']
        return None

    @classmethod
    def collect(cls, code, **kwargs):
        '''Collecting Data of Stock Code to all data or until duplicate data.'''
        print('@@ S', code)
        sp = cls.factory_provider(code, 'naver')
        cls.collect_candle(sp, **kwargs)
        cls.collect_investor(sp, **kwargs)
        sp = cls.factory_provider(code, 'krx')
        cls.collect_shortstock(sp, **kwargs) ## debug
        print('@@ E', code)
        return code

    @classmethod
    def multiprocess_collect(cls, param):
        '''Calling DataCollection.collect function to use in multiprocess mode.'''
        return cls.collect(param.code, **param.kwargs)


class StockQuery:
    class Error(Exception):
        pass

    class ExceptionEndOfData(Exception):
        pass

    class AccumulVary:
        '''
        AccumulVary use to convert data - Accmulating and Variation

        Example)
            Convert the trands of investors to show trends for foreigner, institute and person.
                         None     Acc          Acc          Acc       Very           None
            colnames = ['stamp', 'foreigner', 'institute', 'person', 'shortamount', 'end']
            varycolname = 'shortamount'

        '''
        def __init__(self, colns, fieldcolns, **kwargs):
            '''
            :param colns:  Column names of field
                                the first one is not accumulated and
                                the last one is the tread amount of short stock
            :param fieldcolns:  Column names of field
            --------------------------------------------------------
            example) varycolname = 'D'
                original:               Result:
                                             Acc  Acc  Acc  Very
                A  B  C  D  E  F        A    B    C    D    E    F
                S1,1, 2, 3, 4, 5        S1,  1,   2,   3,   N,   5
                S2,1, 1, 1, 3, 8        S1,  2,   3,   4,  -1,   8
                S3,-1,0, 1, 6, 7        S1,  1,   3,   5,   2,   7
            '''
            self.val_ilist = []
            varycolname = kwargs.get('varycolname', None)
            self.amount_idx = len(colns) - 1
            if varycolname is not None:
                self.amount_idx = colns.index(varycolname)
            # print('amount_idx @', self.amount_idx)
            for name in colns:
                self.val_ilist.append(fieldcolns.index(name))
            self.rows = None
            self.amount_value = None

        def update(self, field):
            if self.rows:
                rows = [r for i, r in enumerate(field) if i in self.val_ilist]
                if rows.count(None) >= 2:
                    raise StockQuery.ExceptionEndOfData()
                # print('!!', rows)
                for i, r in enumerate(rows):
                    if i == self.amount_idx:
                        continue
                    if i == 0 or i > self.amount_idx:
                        self.rows[i] = rows[i]
                        continue
                    self.rows[i] += rows[i]
                # print('##', self.rows, rows)
                if rows[self.amount_idx]:
                    if self.rows[self.amount_idx]:
                        avalue = rows[self.amount_idx] - self.amount_value
                        self.rows[self.amount_idx] += avalue
                    else:
                        if self.amount_value:
                            avalue = rows[self.amount_idx] - self.amount_value
                        else:
                            avalue = rows[self.amount_idx]
                        self.rows[self.amount_idx] = avalue
                    self.amount_value = field[self.val_ilist[self.amount_idx]]
                else:
                    self.rows[self.amount_idx] = None
            else:
                rows = [r for i, r in enumerate(field) if i in self.val_ilist]
                self.amount_value = rows[self.amount_idx]
                rows[self.amount_idx] = None
                # print('##', rows)
                self.rows = rows
            # print('  ', self.rows)
            return copy.deepcopy(self.rows)

    @classmethod
    def raw_data(cls, sidb, **kwargs):
        '''
        :param colnames:    list of Column name
        :param sdate:       Start date, default is current local time.
                            Format is YYYY-MM-DD, YYYY.MM.DD or YYYYMMDD.
        :param edate:       End date, default is current local time.
                            Format is YYYY-MM-DD, YYYY.MM.DD or YYYYMMDD.
        :param months:      The past duration time, unit is month.
                            Default is 3 months.
        :return:            List of list.
        '''
        start_date = kwargs.get('sdate', DateTool.to_strfdate())
        end_date = kwargs.get('edate', None)
        months = kwargs.get('months', 3)
        date_end = DateTool.to_datetime(start_date)
        if end_date:
            date_start = DateTool.to_datetime(end_date)
        else:
            date_start = date_end - relativedelta(months=months)
        if (date_start-date_end).days >= 0:
            date_start, date_end = date_end, date_start
        # print('##', date_start, date_end)

        tablename = 'stock_day'
        colnames = kwargs.get('colnames', sidb.get_colnames(tablename))
        if not colnames:
            colnames = sidb.get_colnames(tablename)
        columns = [Column(x) for x in colnames]
        table = sidb.get_table(tablename)
        sql = sqlalchemy.sql.select(columns).where(
            and_(DateTool.to_strfdate(date_start) <= table.c.stamp,
                 table.c.stamp <= DateTool.to_strfdate(date_end))).\
            order_by(table.c.stamp.asc())
        sqlquery = sidb.to_sql(sql)

        def gathering():
            try:
                fields = sidb.session.query(sql).all()
            except Exception as e:
                raise StockQuery.Error(f'{e}')
            return QueryData(colnames=colnames,
                             fields=[list(x) for x in fields], sql=sqlquery)

        cachekey = sidb.db_file+':'+sqlquery
        return FCache().caching(cachekey, gathering,
                                duration=900, cast=QueryData.cast)

    @classmethod
    def raw_data_of_each_colnames(cls, sidb, colnames, **kwargs):
        '''
        :param colnames (dict): Column name
        :param sdate (str):     Start date, default is current local time.
                                Format is YYYY-MM-DD, YYYY.MM.DD or YYYYMMDD.
        :param edate (str):     End date, default is current local time.
                                Format is YYYY-MM-DD, YYYY.MM.DD or YYYYMMDD.
        :param months (int):    The past duration time, unit is month.
                                Default is 3 months.
        :param accmulator (bool): Return the data with operating to accmulate.
        :return (list):         List of list.
        '''
        qdata = cls.raw_data(sidb, colnames=colnames, **kwargs)
        if kwargs.get('accmulator', False):
            tradedata = QueryData(colnames=colnames, sql=qdata.sql)
            tacc = cls.AccumulVary(tradedata.colnames, qdata.colnames,
                                   varycolname='shortamount')
            for field in qdata.fields:
                try:
                    tradedata.fields.append(tacc.update(field))
                except StockQuery.ExceptionEndOfData:
                    pass
            return tradedata
        return qdata
