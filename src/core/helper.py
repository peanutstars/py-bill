
from pysp.serror import SDebug


class _LineParser(SDebug):
    # DEBUG = True
    COLCNT = 8
    SEPERATOR = '|'
    MARK_CLAUSE = '##'
    MARK_CTITLE = 'Key Word'

    def __init__(self):
        self.clause = False
        self.data = []

    def get_columns(self):
        data = self.data
        self.data = []
        return data

    def input(self, line):
        self.dprint(self.clause, line)
        if line.find(self.MARK_CLAUSE) >= 0:
            self.clause = True if line.find(self.MARK_CTITLE) > 0 else False
            return False
        if self.clause is False:
            return False

        arr = line.strip().split(self.SEPERATOR)
        arr = arr if arr[-1] else arr[:-1]
        arr = arr[1:] if not arr[0] else arr
        if not self.data and len(arr[0].split('.')) != 3:
            return False

        self.data += arr
        dlen = len(self.data)
        if dlen == self.COLCNT:
            return True
        elif dlen > self.COLCNT:
            # drop data
            self.data = []
        return False


class _LP_DaumDay(_LineParser):
    COLCNT = 8
    SEPERATOR = '|'
    MARK_CLAUSE = '##'
    MARK_CTITLE = '일자별 주가'


class _LP_NaverDay(_LineParser):
    COLCNT = 7
    SEPERATOR = '|'
    MARK_CLAUSE = '##'
    MARK_CTITLE = '일별 시세'


class _LP_NaverInvestor(_LineParser):
    COLCNT = 9
    SEPERATOR = '|'
    MARK_CLAUSE = '##'
    MARK_CTITLE = '순매매 거래량'


class Helper:
    class LineParser:
        DaumDay = _LP_DaumDay
        NaverInvestor = _LP_NaverInvestor
        NaverDay = _LP_NaverDay
