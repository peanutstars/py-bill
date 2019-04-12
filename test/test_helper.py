import datetime
import unittest

from core.helper import DateTool


class TestHelper(unittest.TestCase):

    def test_datetool(self):
        date1_forms = ['2019. 3. 4', '2019.3.4',  '2019-03-04', '20190304']
        date2_forms = ['2019. 3.14', '2019.3.14', '2019-03-14', '20190314']
        date1_expected = DateTool.to_strfdate(datetime.datetime(2019, 3, 4))
        date2_expected = DateTool.to_strfdate(datetime.datetime(2019, 3, 14))
        for form in date1_forms:
            rv = DateTool.to_strfdate(DateTool.to_datetime(form))
            self.assertEqual(rv, date1_expected)
        for form in date2_forms:
            rv = DateTool.to_strfdate(DateTool.to_datetime(form))
            self.assertEqual(rv, date2_expected)
