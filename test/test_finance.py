# -*- coding: utf-8 -*-

import hexdump
import unittest

from core.finance import DataCollection, BillConfig, FDaum, FNaver
from core.connect import Http
from core.model import *


class TestFinance(unittest.TestCase):
    spd = ServiceProvider(name='daum', codename='카카오', code='035720')
    spn = ServiceProvider(name='naver', codename='카카오', code='035720')
    spk = ServiceProvider(name='krx', codename='카카오', code='035720')

    def test_collect_data(self):
        # FNaver.DEBUG = True

        f = DataCollection()
        # f.collect_candle(self.spd)
        f.collect_candle(self.spn)
        f.collect_investor(self.spn)
        f.collect_shortstock(self.spk)

    def test_billconfig(self):
        bconfig = BillConfig()
        cvalue = bconfig.get_value('folder.user.config')
        self.assertTrue(cvalue == '/var/pybill/usr/config')
        self.assertTrue( bconfig is BillConfig())
