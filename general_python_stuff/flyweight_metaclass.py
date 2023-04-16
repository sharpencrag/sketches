class FlyWeight_Meta(type):
    """METACLASS: Implements (a version of) the flyweight pattern.

    An instance cache will be added to every class that is modified by
    this metaclass, and if the passed arguments are the same as a
    cached object, that object will be returned.

    All arguments of the class's __init__ must be hashable.
    """
    def __new__(mcs, name, superclasses, kwargs):
        return super(FlyWeight_Meta, mcs).__new__(mcs, name, superclasses,
                                                  kwargs)

    def __init__(cls, name, bases, dct):
        cls.__inst_cache = {}
        super(FlyWeight_Meta, cls).__init__(name, bases, dct)

    def __call__(cls, *args, **kwargs):
        lookup = (args, tuple(kwargs.items()))
        cache = cls.__inst_cache
        return cache.setdefault(lookup, type.__call__(cls, *args, **kwargs))
