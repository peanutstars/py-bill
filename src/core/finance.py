# -*- coding: utf-8 -*-

import datetime
import os

from pysp.sbasic import SSingleton, SFile
from pysp.sconf import SConfig
from pysp.ssql import SSimpleDB

from core.interface import Http
from core.model import *


class FHelper:
    @staticmethod
    def filter_out(argv):
        argc = len(argv)
        if argc == 1:
            try:
                int(argv[0])
            except:
                return []
            return argv
        if argc > 2:
            try:
                int(argv[1])
            except:
                return []
        return argv if argv[-1] else argv[:-1]

    @classmethod
    def get_day_url(cls, sp, page):
        return cls.URL['day'].format(code=sp.code, page=page)


class FDaum(FHelper):
    URL = {
        'day': 'http://finance-service.daum.net/item/quote_yyyymmdd.daum?code={code}&page={page}',
    }
    SEPERATOR   = '|'
    CLENGTH     = 8
    IDX_STAMP   = 0
    IDX_START   = 1
    IDX_END     = 4
    IDX_HIGH    = 2
    IDX_LOW     = 3
    IDX_VOLUME  = 7

    @classmethod
    def modify_stamp(cls, stamp):
        arr = stamp.split('.')
        yy = '19' if int(arr[0]) >= 60 else '20'
        return yy + stamp

    @classmethod
    def parse_day(cls, sp, chunk):
        days = []
        day = []
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            arr = [ x.strip() for x in l.split('|')]
            arr = cls.filter_out(arr)
            day += arr
            if len(day) == cls.CLENGTH:
                print(day)

                days.append(StockDay(
                    finance=sp.name,
                    stamp=cls.modify_stamp(day[cls.IDX_STAMP]),
                    start=int(day[cls.IDX_START]),
                    end=int(day[cls.IDX_END]),
                    high=int(day[cls.IDX_HIGH]),
                    low=int(day[cls.IDX_LOW]),
                    volume=int(day[cls.IDX_VOLUME])))
                day = []
        for day in days:
            print(day)
        return days


class FNaver(FHelper):
    URL = {
        'day': 'https://finance.naver.com/item/sise_day.nhn?code={code}&page={page}',
    }
    SEPERATOR   = '|'
    CLENGTH     = 7
    IDX_STAMP   = 0
    IDX_START   = 3
    IDX_END     = 1
    IDX_HIGH    = 4
    IDX_LOW     = 5
    IDX_VOLUME  = 6

    @classmethod
    def parse_day(cls, sp, chunk):
        days = []
        day = []
        for line in chunk.split('\n'):
            l = line.strip().replace(',','')
            if not l:
                continue
            arr = [ x.strip() for x in l.split('|')]
            arr = cls.filter_out(arr)
            day += arr
            if len(day) == cls.CLENGTH:
                print(day)
                days.append(StockDay(
                    finance=sp.name,
                    stamp=day[cls.IDX_STAMP],
                    start=int(day[cls.IDX_START]),
                    end=int(day[cls.IDX_END]),
                    high=int(day[cls.IDX_HIGH]),
                    low=int(day[cls.IDX_LOW]),
                    volume=int(day[cls.IDX_VOLUME])))
                day = []
        for day in days:
            print(day)
        return days


class FinUnknown:
    @classmethod
    def get_day_url(cls, sp, page):
        return PyJoyousError('Undefined Day URL')

    @classmethod
    def parse_day(cls, sp, chunk):
        raise PyJoyousError('Undefined Parser')


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
                'volume': d.volume
            }
            param = {
                'data': data,
                'only_insert': True
            }
            if self.upsert('stock_day', **param) is False:
                if i == 0:
                    continue
                return False
        return True


class Finance(Http):
    PROVIDER = {
        'daum':     FDaum,
        'naver':    FNaver,
    }
    def __init__(self):
        pass

    def get_day_url(self, sp, page):
        return self.PROVIDER.get(sp.name, FinUnknown).get_day_url(sp, page)

    def parse_day_data(self, sp, chunk):
        fin = self.PROVIDER.get(sp.name, FinUnknown)
        return fin.parse_day(sp, chunk)

    def fill_day_candle(self, sp):
        sidb = StockItemDB.factory(sp.code)
        page = 0
        loop = True
        while loop:
            page += 1
            chunk = self.get(self.get_day_url(sp, page), text=True)
            days = self.parse_day_data(sp, chunk)
            loop = sidb.update_candle(days)
