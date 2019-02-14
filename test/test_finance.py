# -*- coding: utf-8 -*-

import hexdump
import unittest

from core.finance import DataCollection, BillConfig, FDaum, FNaver
from core.interface import Http
from core.model import *


class TestFinance(unittest.TestCase):
    spd = ServiceProvider(name='daum', codename='카카오', code='035720')
    spn = ServiceProvider(name='naver', codename='카카오', code='035720')

    def test_collect_data(self):
        # FNaver.DEBUG = True

        f = DataCollection()
        # f.collect_candle(self.spd)
        f.collect_candle(self.spn)
        f.collect_investor(self.spn)

    def test_billconfig(self):
        bconfig = BillConfig()
        cvalue = bconfig.get_value('folder.user.config')
        self.assertTrue(cvalue == '/var/pybill/usr/config')
        self.assertTrue( bconfig is BillConfig())

    def test_fdaum_day(self):
        # FDaum.DEBUG = True
        page = 1
        chunk = Http.get(FDaum.get_url('day', self.spd, page), text=True)
        data = FDaum.parse_day(self.spd, chunk)
        self.assertTrue(len(data) == 10)

    def test_fnaver_day(self):
        # FNaver.DEBUG = True
        page = 1
        chunk = Http.get(FNaver.get_url('day', self.spn, page), text=True)
        data = FNaver.parse_day(self.spn, chunk)
        self.assertTrue(len(data) == 10)

    def test_fnaver_dayinvestor(self):
        # FNaver.DEBUG = True
        page = 1
        chunk = Http.get(
                    FNaver.get_url('dayinvestor', self.spn, page), text=True)
        data = FNaver.do_parser('dayinvestor', self.spn, chunk)
        self.assertTrue(len(data) == 20)
