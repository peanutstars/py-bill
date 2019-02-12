# -*- coding: utf-8 -*-

import hexdump
import unittest

from core.finance import Finance, BillConfig
from core.model import *


class TestFinance(unittest.TestCase):

    def test_finance(self):
        sp_daum = ServiceProvider(name='daum', codename='카카오', code='035720')
        sp_naver = ServiceProvider(name='naver', codename='카카오', code='035720')

        f = Finance()
        # f.fill_day_candle(sp_daum)
        f.fill_day_candle(sp_naver)

    def test_billconfig(self):
        bconfig = BillConfig()
        cvalue = bconfig.get_value('folder.user.config')
        self.assertTrue(cvalue == '/var/pybill/usr/config')
        self.assertTrue( bconfig is BillConfig())
