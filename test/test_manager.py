# -*- coding: utf-8 -*-

import time
import unittest

from pysp.sbasic import SSingleton

from core.manager import Collector


class TestManager(unittest.TestCase):

    def test_collector_1(self):
        Collector.DEBUG = True
        cm = Collector('NONE')
        cm.collect('035720')
        time.sleep(1)
        cm.quit()
        del SSingleton._instances[Collector]

    def test_collector_2(self):
        cm = Collector()
        cm.collect('009150')
