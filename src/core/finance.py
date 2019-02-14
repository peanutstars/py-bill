# -*- coding: utf-8 -*-

import datetime
import os

from pysp.sbasic import SSingleton, SFile
from pysp.sconf import SConfig
from pysp.serror import SDebug
from pysp.ssql import SSimpleDB

from core.helper import Helper
from core.interface import Http
from core.model import *


class FHelper(SDebug):
    # DEBUG = True
    URL = {}

    @classmethod
    def stamp_yy_to_yyyy(cls, stamp):
        arr = stamp.split('.')
        yy = '19' if int(arr[0]) >= 60 else '20'
        return yy + stamp

    @classmethod
    def get_url(cls, key, sp, page):
        return cls.URL.get(key).format(code=sp.code, page=page)

    @classmethod
    def do_parser(cls, key, sp, chunk):
        raise NotImplementedError('Verify Implemented Function: do_parser')


class FDaum(FHelper):
    URL = {
        'day': 'http://finance-service.daum.net/item/quote_yyyymmdd.daum?code={code}&page={page}',
    }

    @classmethod
    def do_parser(cls, key, sp, chunk):
        PARSER = {
            'day': cls.parse_day,
        }
        return PARSER.get(key)(sp, chunk)

    @classmethod
    def parse_day(cls, sp, chunk):
        class ColIdx:
            SEPERATOR   = '|'
            COL_LENGTH  = 8
            IDX_STAMP   = 0
            IDX_START   = 1
            IDX_END     = 4
            IDX_HIGH    = 2
            IDX_LOW     = 3
            IDX_VOLUME  = 7

        days = []
        day = []
        p = Helper.LineParser.DaumDay()
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            if p.input(l):
                day = [x.strip() for x in p.get_columns()]
                cls.dprint(day)
                days.append(StockDay(
                    finance=sp.name,
                    stamp=cls.stamp_yy_to_yyyy(day[ColIdx.IDX_STAMP]),
                    start=int(day[ColIdx.IDX_START]),
                    end=int(day[ColIdx.IDX_END]),
                    high=int(day[ColIdx.IDX_HIGH]),
                    low=int(day[ColIdx.IDX_LOW]),
                    volume=int(day[ColIdx.IDX_VOLUME])))
                day = []
        for day in days:
            cls.dprint(day)
        return days


class FNaver(FHelper):
    BASE_URL = 'https://finance.naver.com/item'
    URL = {
        'day':          BASE_URL+'/sise_day.nhn?code={code}&page={page}',
        'dayinvestor': BASE_URL+'/frgn.nhn?code={code}&page={page}'
    }

    @classmethod
    def do_parser(cls, key, sp, chunk):
        PARSER = {
            'day':          cls.parse_day,
            'dayinvestor':  cls.parser_dayinvestor,
        }
        return PARSER.get(key)(sp, chunk)

    @classmethod
    def parse_day(cls, sp, chunk):
        class ColIdx:
            SEPERATOR   = '|'
            COL_LENGTH  = 7
            IDX_STAMP   = 0
            IDX_START   = 3
            IDX_END     = 1
            IDX_HIGH    = 4
            IDX_LOW     = 5
            IDX_VOLUME  = 6

        days = []
        day = []
        p = Helper.LineParser.NaverDay()
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            if p.input(l):
                day = [x.strip() for x in p.get_columns()]
                cls.dprint(day)
                days.append(StockDay(
                    finance=sp.name,
                    stamp=day[ColIdx.IDX_STAMP],
                    start=int(day[ColIdx.IDX_START]),
                    end=int(day[ColIdx.IDX_END]),
                    high=int(day[ColIdx.IDX_HIGH]),
                    low=int(day[ColIdx.IDX_LOW]),
                    volume=int(day[ColIdx.IDX_VOLUME])))
                day = []
        for day in days:
            cls.dprint(day)
        return days

    @classmethod
    def parser_dayinvestor(cls, sp, chunk):
        class ColIdx:
            COL_LENGTH      = 9
            IDX_STAMP       = 0
            IDX_FOREIGNER   = 6
            IDX_FOREIGN_RATE = 8
            IDX_INSTITUTE   = 5

        days = []
        day = []
        p = Helper.LineParser.NaverInvestor()
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            if p.input(l):
                day = [x.strip() for x in p.get_columns()]
                cls.dprint(day)
                foreigner = int(day[ColIdx.IDX_FOREIGNER])
                institute = int(day[ColIdx.IDX_INSTITUTE])
                person = -(foreigner+institute)
                days.append(StockDayInvestor(
                    stamp=day[ColIdx.IDX_STAMP],
                    foreigner=foreigner,
                    frate=float(day[ColIdx.IDX_FOREIGN_RATE][:-1]),
                    institute=institute,
                    person=person))
        for day in days:
            cls.dprint(day)
        return days


class FinUnknown:
    class Error(Exception):
        pass

    @classmethod
    def get_url(cls, key, sp, page):
        return cls.Error(f'Unknown {key} URL')

    @classmethod
    def do_parser(cls, key, sp, chunk):
        return cls.Error('Unknown {key} Function')


class BillConfig(SConfig, metaclass=SSingleton):
    def __init__(self):
        folder = os.path.dirname(os.path.abspath(__file__))
        self.config_folder = f'{folder}/../config/'
        configyml = f'{self.config_folder}/config.yml'
        super(BillConfig, self).__init__(yml_file=configyml)
        self.init_variables()

    def init_variables(self):
        stock_yml = f'{self.config_folder}/db/stock.yml'
        self.set_value('_config.db.stock_yml', stock_yml)
        stock_folder = self.get_value('folder.user.stock', './')
        self.set_value('_config.db.stock_folder', stock_folder)


class StockItemDB(SSimpleDB):
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
        SFile.mkdir(db_file)
        db_config = bcfg.get_value('_config.db.stock_yml')
        return cls(db_file=db_file, db_config=db_config)

    def update_candle(self, days):
        if len(days) == 0:
            return False
        for i, d in enumerate(days):
            data = {
                'stamp': datetime.date(*[int(x) for x in d.stamp.split('.')]),
                'finance': d.finance,
                'start': d.start,
                'end': d.end,
                'high': d.high,
                'low': d.low,
                'volume': d.volume,
            }
            param = {
                'data': data,
                'only_insert': True,
            }
            if self.upsert('stock_day', **param) is False:
                if i == 0:
                    continue
                return False
        return True

    def update_investor(self, days):
        if len(days) == 0:
            return False
        for i, d in enumerate(days):
            data = {
                'stamp': datetime.date(*[int(x) for x in d.stamp.split('.')]),
                'foreigner': d.foreigner,
                'frate': d.frate,
                'institute': d.institute,
                'person': d.person,
            }
            if i == 0:
                columns = ['stamp', 'foreigner', 'frate', 'institute', 'person']
                options = {
                    'wheres': {'stamp': data.get('stamp')}
                }
                rv = self.query('stock_day', *columns, **options)
                inv = StockDayInvestor(*rv[0])
                if inv.foreigner == d.foreigner and inv.person == d.person:
                    return False
            if self.upsert('stock_day', data=data) is False:
                return False
        return True


class DataCollection:
    class Error(Exception):
        pass

    PROVIDER = {
        'daum':     FDaum,
        'naver':    FNaver,
    }
    def __init__(self):
        super(DataCollection, self).__init__()

    def get_url(self, key, sp, page):
        if page  > 0:
            return self.PROVIDER.get(sp.name, FinUnknown).get_url(key, sp, page)
        raise self.Error('Invalied page Range is 0 over.')

    def parse_chunk(self, key, sp, chunk):
        fin = self.PROVIDER.get(sp.name, FinUnknown)
        return fin.do_parser(key, sp, chunk)

    def collect_candle(self, sp, **kwargs):
        sidb = StockItemDB.factory(sp.code)
        page = 0
        loop = True
        while loop:
            page += 1
            chunk = Http.get(self.get_url('day', sp, page), text=True)
            days = self.parse_chunk('day', sp, chunk)
            loop = sidb.update_candle(days)

    def collect_investor(self, sp, **kwargs):
        sidb = StockItemDB.factory(sp.code)
        page = 0
        loop = True
        while loop:
            page += 1
            chunk = Http.get(self.get_url('dayinvestor', sp, page), text=True)
            days = self.parse_chunk('dayinvestor', sp, chunk)
            loop = sidb.update_investor(days)
