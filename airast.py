from enum import Enum
from air_types import *


class SourceLocation:
    def __init__(self, begin, end):
        self.begin = begin
        self.end = end

    def __add__(self, other):
        if not isinstance(other, SourceLocation):
            return NotImplemented
        return SourceLocation(min(self.begin, other.begin), max(self.end, other.end))

    def __str__(self):
        return "{}-{}".format(self.begin, self.end)


class AstNode:
    def __init__(self, location=None, value_type=None):
        self.value_type = value_type
        self.location = location

    def airify(self):
        raise NotImplementedError

    def is_int(self):
        return isinstance(self.value_type, IntegerType)


class BinaryOperator(Enum):
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    AND = 4
    OR = 5
    EQ = 6
    NEQ = 7
    LT = 8
    LE = 9
    GT = 10
    GE = 11

    def __str__(self):
        return self.name()

    def name(self):
        strs = ["+", "-", "*", "/", "and", "or", "eq?", "ne?", "lt?", "le?", "gt?", "ge?"]
        assert self.value < len(strs)
        return strs[self.value]

    def precedence(self):
        precs = {
            self.ADD: 0,
            self.SUB: 0,
            self.MUL: 1,
            self.DIV: 1,
            self.AND: -3,
            self.OR: -3,
            self.EQ: -2,
            self.NEQ: -2,
            self.LT: -2,
            self.LE: -2,
            self.GT: -2,
            self.GE: -2,
        }
        assert self in precs
        return precs[self]


class BinaryExpression(AstNode):
    def __init__(self, op, left, right):
        super().__init__()
        self.op = op
        self.left = left
        self.right = right

    def airify(self):
        return [self.op.name(), self.left.airify(), self.right.airify()]


class UnaryOperator(Enum):
    NEG = 0

    def __str__(self):
        if self.value == UnaryOperator.NEG:
            return "neg"
        else:
            raise RuntimeError("Unknown unary operator")


class UnaryExpression(AstNode):
    def __init__(self, op, operand):
        super().__init__()
        self.op = op
        self.operand = operand

    def airify(self):
        if self.op == UnaryOperator.NEG:
            return ["-", 0, self.operand.airify()]
        return [str(self.op), self.operand.airify()]


class CaseExpression(AstNode):
    def __init__(self, cases):
        super().__init__()
        self.cases = cases

    def airify(self):
        return ["if", *[[x[0].airify(), x[1].airify()] for x in self.cases]]


class BlockExpression(AstNode):
    def __init__(self, block):
        super().__init__()
        self.block = block

    def airify(self):
        if len(self.block) == 1:
            return self.block[0].airify()
        return ["seq", *[x.airify() for x in self.block]]


class LetExpression(AstNode):
    def __init__(self, bindings, block):
        super().__init__()
        self.bindings = bindings
        self.block = block

    def airify(self):
        b = ([x[0].name, x[1].airify()] for x in self.bindings)
        return ["let", list(b), *(x.airify() for x in self.block)]


class CallExpression(AstNode):
    def __init__(self, func, parameter):
        super().__init__()
        self.func = func
        self.parameter = parameter

        assert func is not None
        assert all(p is not None for p in parameter)

    def airify(self):
        return [self.func.airify(), *[p.airify() for p in self.parameter]]


class VariableReference(AstNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def airify(self):
        return ["var-ref", self.name]


class ValueNode(AstNode):
    def __init__(self, value, value_type):
        super().__init__(value_type=value_type)
        self.value = value

    def airify(self):
        if isinstance(self.value, list):
            return ["quote", self.value]
        return self.value


class IfThenElse(AstNode):
    def __init__(self, cond, then, otherwise):
        super().__init__()
        self.cond = cond
        self.then = then
        self.otherwise = otherwise

    def airify(self):
        return ["if", [self.cond.airify(), self.then.airify()], [True, self.otherwise.airify()]]


class Identifier(AstNode):
    def __init__(self, name):
        super().__init__()
        self.name = name

    def airify(self):
        return self.name


class ForeachExpression(AstNode):
    def __init__(self, var_binds, block):
        super().__init__()
        self.vars = var_binds
        self.block = block

    def airify(self):
        return ["foreach", [[x[0].name, x[1].airify()] for x in self.vars], *[p.airify() for p in self.block]]


class LambdaExpression(AstNode):
    def __init__(self, params, captures, expr):
        super().__init__()
        self.params = params
        self.captures = captures
        self.expr = expr

    def airify(self):
        return ["lambda", ["quote", [x.name for x in self.captures]], ["quote", [x.name for x in self.params]],
                ["quote", self.expr.airify()]]


class ArrayConstructor(AstNode):
    def __init__(self, entries):
        super().__init__()
        self.entries = entries

    def airify(self):
        return ["list", *[e.airify() for e in self.entries]]


class RecordKeyValuePair:
    def __init__(self, key, value, type_hint):
        self.key = key
        self.value = value
        self.type_hint = type_hint


class RecordConstructor(AstNode):
    def __init__(self, entries):
        super().__init__()
        self.entries = entries

    def airify(self):
        return ["dict", *[[p.key.airify(), p.value.airify()] for p in self.entries]]
