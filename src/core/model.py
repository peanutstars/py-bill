# -*- coding: utf-8 -*-


class DictHelper(dict):
    COLUMNS = []

    class Error(Exception):
        pass

    @classmethod
    def cast(cls, data):
        if type(data) is cls:
            return data
        if type(data) is dict:
            return cls(**data)
        # sub-casting in list
        if type(data) is list:
            cdata = []
            if data and type(data[0]) is cls:
                return data
            for row in data:
                cdata.append(cls.cast(row))
            return cdata
        raise cls.Error('Not Supported CAST')

    @classmethod
    def from_list(cls, *args):
        if len(args) == len(cls.COLUMNS):
            return cls(**dict(zip(cls.COLUMNS, args)))
        raise cls.Error('Not Support Format')

    def __getattr__(self, name):
        return self[name]


class ServiceProvider(DictHelper):
    COLUMNS = ['name', 'codename', 'code']

    def __init__(self, **kwargs):
        super(ServiceProvider, self).__init__()
        self['name'] = kwargs.get('name')
        self['codename'] = kwargs.get('codename')
        self['code'] = kwargs.get('code')


class StockDayInvestor(DictHelper):
    COLUMNS = ['stamp', 'foreigner', 'frate', 'institute', 'person']

    def __init__(self, **kwargs):
        super(StockDayInvestor, self).__init__()
        self['stamp'] = kwargs.get('stamp')
        self['foreigner'] = kwargs.get('foreigner')
        self['frate'] = kwargs.get('frate')
        self['institute'] = kwargs.get('institute')
        self['person'] = kwargs.get('person')


class StockDayShort(DictHelper):
    COLUMNS = ['stamp', 'short', 'shortamount']

    def __init__(self, **kwargs):
        super(StockDayShort, self).__init__()
        self['stamp'] = kwargs.get('stamp')
        self['short'] = kwargs.get('short')
        self['shortamount'] = kwargs.get('shortamount')


class StockDay(DictHelper):
    COLUMNS = ['finance', 'stamp', 'start', 'end', 'high', 'low', 'volume']

    def __init__(self, **kwargs):
        super(StockDay, self).__init__()
        self['finance'] = kwargs.get('finance')
        self['stamp'] = kwargs.get('stamp')
        self['start'] = kwargs.get('start')
        self['end'] = kwargs.get('end')
        self['high'] = kwargs.get('high')
        self['low'] = kwargs.get('low')
        self['volume'] = kwargs.get('volume')


class QueryData(DictHelper):
    def __init__(self, **kwargs):
        super(QueryData, self).__init__()
        self['colnames'] = kwargs.get('colnames', [])
        self['fields'] = kwargs.get('fields', [])
        self['sql'] = kwargs.get('sql', None)
