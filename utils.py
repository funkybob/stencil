
class Int(object):
    '''
    Hepler to provide literal ints in templates
    '''
    def __getitem__(self, key):
        return int(key)


class _float(float):
    def __getitem__(self, key):
        return self + (float(key) / 10 ** len(key))


class Float(object):
    '''
    Helper to provide literal floats in templates
    '''
    def __getitem__(self, key):
        return _float(key)


class String(object):
    def __getitem__(self, key):
        return key


literal = {
    'int': Int(),
    'float': Float(),
    'str': String(),
}
