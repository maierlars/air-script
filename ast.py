from enum import Enum


class BinaryOperator(Enum):
    ADD = 0
    SUB = 1
    MUL = 2
    DIV = 3
    AND = 4
    OR = 5

    def __str__(self):
        strs = ["+", "-", "*", "/", "and", "or"]
        if self.value < len(strs):
            return strs[self.value]
        else:
            raise RuntimeError("Unknown binary operator")


class BinaryExpression:
    def __init__(self, op, left, right):
        self.op = op
        self.left = left
        self.right = right

    def airify(self):
        return [str(self.op), self.left.airify(), self.right.airify()]


class UnaryOperator(Enum):
    NEG = 0

    def __str__(self):
        if self.value == UnaryOperator.NEG:
            return "neg"
        else:
            raise RuntimeError("Unknown unary operator")


class UnaryExpression:
    def __init__(self, op, operand):
        self.op = op
        self.operand = operand

    def airify(self):
        if self.op == UnaryOperator.NEG:
            return ["-", 0, self.operand.airify()]
        return [str(self.op), self.operand.airify()]


class CaseExpression:
    def __init__(self, cases):
        self.cases = cases

    def airify(self):
        return ["if", *[[x[0].airify(), x[1].airify()] for x in self.cases]]


class BlockExpression:
    def __init__(self, block):
        self.block = block

    def airify(self):
        if len(self.block) == 1:
            return self.block[0].airify()
        return ["seq", *[x.airify() for x in self.block]]


class LetExpression:
    def __init__(self, bindings, block):
        self.bindings = bindings
        self.block = block

    def airify(self):
        b = ([x[0].name, x[1].airify()] for x in self.bindings)
        return ["let", list(b), *(x.airify() for x in self.block)]


class CallExpression:
    def __init__(self, func, parameter):
        self.func = func
        self.parameter = parameter

    def airify(self):
        return [self.func.airify(), *[p.airify() for p in self.parameter]]


class VariableReference:
    def __init__(self, name):
        self.name = name

    def airify(self):
        return ["var-ref", self.name]


class JsonValue:
    def __init__(self, value):
        self.value = value

    def airify(self):
        if isinstance(self.value, list):
            return ["quote", self.value]
        return self.value


class IfThenElse:
    def __init__(self, cond, then, otherwise):
        self.cond = cond
        self.then = then
        self.otherwise = otherwise

    def airify(self):
        return ["if", [self.cond.airify(), self.then.airify()], [True, self.otherwise.airify()]]


class Identifier:
    def __init__(self, name):
        self.name = name

    def airify(self):
        return self.name


class ForeachExpression:
    def __init__(self, var_binds, block):
        self.vars = var_binds
        self.block = block

    def airify(self):
        return ["foreach", [[x[0].name, x[1].airify()] for x in self.vars], *[p.airify() for p in self.block]]


class LambdaExpression:
    def __init__(self, params, captures, expr):
        self.params = params
        self.captures = captures
        self.expr = expr

    def airify(self):
        return ["lambda", ["quote", [x.name for x in self.captures]], ["quote", [x.name for x in self.params]],
                ["quote", self.expr.airify()]]
