
import time
import unittest

from core.cache import FCache
from pysp.sbasic import SSingleton


class TestCache(unittest.TestCase):

    def test_file_cache(self):
        # Create
        cache = FCache()
        cache.set_cache('1', 'first', duration=6)
        cache.set_cache('2', 'second', duration=6)
        cache.cleanup()
        del SSingleton._instances[FCache]
        del cache
        # Load from file
        cache = FCache()
        self.assertTrue('first' == cache.get_cache('1'))
        cache.set_cache('3', 'three', duration=2)
        cache.cleanup()
        del SSingleton._instances[FCache]
        del cache
        # Expired
        time.sleep(2.1)
        cache = FCache()
        self.assertTrue(cache.get_cache('3') == cache.NO_DATA)
        self.assertTrue('first' == cache.get_cache('1'))
        self.assertTrue('second' == cache.get_cache('2'))
        cache.cleanup()
        del SSingleton._instances[FCache]
        del cache
        # Clean up
        time.sleep(5)
        FCache().cleanup()
        del SSingleton._instances[FCache]
