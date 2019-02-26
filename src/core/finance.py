# -*- coding: utf-8 -*-

import datetime
import os

from pysp.sbasic import SSingleton, SFile
from pysp.sconf import SConfig
from pysp.serror import SDebug
from pysp.ssql import SSimpleDB

from core.connect import Http, FDaum, FNaver, FKrx, FUnknown
from core.model import *



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
        stock_folder = self.get_value('folder.stock', './')
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
        SFile.mkdir(os.path.dirname(db_file))
        db_config = bcfg.get_value('_config.db.stock_yml')
        return cls(db_file=db_file, db_config=db_config)

    def update_candle(self, days):
        if len(days) == 0:
            return False
        data = []
        for i, d in enumerate(days):
            item = {
                'stamp': datetime.date(*[int(x) for x in d.stamp.split('.')]),
                'finance': d.finance,
                'start': d.start,
                'end': d.end,
                'high': d.high,
                'low': d.low,
                'volume': d.volume,
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
            item = {
                'stamp': datetime.date(*[int(x) for x in d.stamp.split('.')]),
                'foreigner': d.foreigner,
                'frate': d.frate,
                'institute': d.institute,
                'person': d.person,
            }
            if i == 0:
                columns = ['stamp', 'foreigner', 'frate', 'institute', 'person']
                options = {
                    'wheres': {'stamp': item.get('stamp')}
                }
                rv = self.query('stock_day', *columns, **options)
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

    def __init__(self):
        super(DataCollection, self).__init__()

    def get_provider(self, sp):
        PROVIDER = {
            'daum':     FDaum,
            'naver':    FNaver,
            'krx':      FKrx,
        }
        return PROVIDER.get(sp.name, FUnknown)

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
