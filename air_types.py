
class TypeNode:
    def is_compatible(self, other):
        return super() == other


class IntegerType:
    def __eq__(self, other):
        return isinstance(other, IntegerType)

    def __str__(self):
        return "int"


class DoubleType:
    def __eq__(self, other):
        return isinstance(other, DoubleType)

    def __str__(self):
        return "double"


class BooleanType:
    def __eq__(self, other):
        return isinstance(other, BooleanType)

    def __str__(self):
        return "bool"


class NullType:
    def __eq__(self, other):
        return isinstance(other, NullType)

    def __str__(self):
        return "null"


class StringType:
    def __eq__(self, other):
        return isinstance(other, StringType)

    def __str__(self):
        return "string"


class AnyType:
    def __eq__(self, other):
        return isinstance(other, AnyType)

    def __str__(self):
        return "any"


class ListType:
    def __eq__(self, other):
        if isinstance(other, ListType):
            return self.base == other.base
        return False

    def __init__(self, base):
        self.base = base

    def __str__(self):
        return "list<{}>".format(self.base)


class DictType:
    def __eq__(self, other):
        if isinstance(other, DictType):
            return self.base == other.base
        return False

    def __init__(self, base):
        self.base = base

    def __str__(self):
        return "dict<{}>".format(self.base)


class RecordType:
    def __eq__(self, other):
        if isinstance(other, RecordType):
            if len(self.pairs) != len(other.pairs):
                return False

            for key, type_ in self.pairs.items():
                if key not in other.pairs or other.pairs[key] != type_:
                    return False
            return True
        return False

    def __init__(self, pairs):
        self.pairs = pairs

    def __str__(self):
        return "{" + ",".join(["{}: {}".format(name, type_) for (name, type_) in self.pairs]) + "}"
