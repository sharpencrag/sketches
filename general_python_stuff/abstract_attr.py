class AbstractAttribute(object):
    """An abstract class attribute.

    Use this in an abstract base class when an attribute MUST be overridden by
    subclasses, and is not intended to be used as a property.
    """

    __isabstractmethod__ = True

    def __init__(self, doc=""):
        self.__doc__ = doc

    def __get__(self, obj, cls):
        return self