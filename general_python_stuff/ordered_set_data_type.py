from collections.abc import MutableSet

__all__ = ["OrderedSet"]


class OrderedSet(MutableSet):

    """Uses an ordered dict to establish the membership of the set.
    Original recipe by Raymond Hettinger
    """

    def __init__(self, values=()):
        self._ordered_dict = dict().fromkeys(values)

    def __len__(self):
        return len(self._ordered_dict)

    def __iter__(self):
        return iter(self._ordered_dict)

    def __contains__(self, value):
        return value in self._ordered_dict

    def add(self, value):
        self._ordered_dict[value] = None

    def discard(self, value):
        self._ordered_dict.pop(value, None)

    def __getitem__(self, index):
        return tuple(self)[index]

    def __repr__(self):
        return "{type_name}{tuple_repr}".format(
            type_name=type(self).__name__,
            tuple_repr=tuple(self)
        )
