import ast


class LookaheadIterator:
    def __init__(self, it):
        self.iter = it
        self.lh = None

    def __iter__(self):
        return self

    def next(self):
        if self.lh is not None:
            value = self.lh
            self.lh = None
            return value
        return next(self.iter)

    def __next__(self):
        return self.next()

    def lookahead(self):
        if self.lh is not None:
            return self.lh
        self.lh = next(self.iter, None)
        return self.lh


class NumericValue:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return '{}f'.format(self.value)


class StringValue:
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return '"{}"'.format(self.value)


class Atom:
    def __init__(self, name):
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, Atom):
            return NotImplemented
        return self.name.lower() == other.name.lower()

    def __str__(self):
        return "`{}`".format(self.name)


class Operator:
    def __init__(self, op):
        self.op = op

    def __eq__(self, other):
        if not isinstance(other, Operator):
            return NotImplemented
        return self.op == other.op

    def __str__(self):
        return "{}".format(self.op)


def atomize(source):
    space = " \r\n\t\v"
    atom_terminator = "()[]{}\"#:;,`" + space
    special_chars = "=+-*/"
    operators = "+-*/"
    i = 0
    while i < len(source):
        if source[i] in space:
            i += 1  # skip all whitespace
        elif source[i] == '#':
            # skip comment until end of line
            while i < len(source) and source[i] != '\n':
                i += 1
        elif source[i] == '"':
            value = ""
            i += 1
            while source[i] != '"':
                value += source[i]
                i += 1
                if i >= len(source):
                    raise RuntimeError("Unterminated string constant")
            i += 1
            yield StringValue(value)
        elif source[i] == '`':
            value = ""
            i += 1
            while source[i] != '`':
                value += source[i]
                i += 1
                if i >= len(source):
                    raise RuntimeError("Unterminated quote sequence")
            i += 1
            yield Atom(value)
        elif source[i] in operators:
            c = source[i]
            i += 1
            yield Operator(c)
        elif source[i] in atom_terminator + special_chars:
            c = source[i]
            i += 1
            yield c
        else:
            # read atom
            start = i
            while i < len(source) and source[i] not in atom_terminator:
                i += 1
            value = source[start:i]
            if value[0] in "0123456789":
                yield NumericValue(float(value))
            else:
                yield Atom(value)


def expect_exact(it, expected):
    atom = it.next()
    if atom != expected:
        raise RuntimeError("Unexpected {}, expected {}".format(atom, expected))


def parse_block(it):
    block = list()
    expect_exact(it, Atom("begin"))
    while it.lookahead() != Atom("end"):
        block.append(parse_block_expression(it))
    it.next()  # take end
    return ast.BlockExpression(block)


def parse_block_or_simple(it):
    if it.lookahead() == Atom("begin"):
        return parse_block_expression(it)
    else:
        return parse_simple_expression(it)


def parse_condition(it):
    cases = list()
    expect_exact(it, Atom("cond"))
    expect_exact(it, ":")
    while it.lookahead() == Atom("if"):
        it.next()  # take the if
        cond = parse_block_or_simple(it)
        expect_exact(it, Atom("do"))
        expect_exact(it, ':')
        then = parse_block_or_simple(it)
        cases.append((cond, then))
    if it.lookahead() == Atom("otherwise"):
        it.next()
        expect_exact(it, ":")
        then = parse_block_or_simple(it)
        cases.append((ast.JsonValue(True), then))
    expect_exact(it, Atom("end"))
    return ast.CaseExpression(cases)


def parse_simple_value(atom):
    if isinstance(atom, StringValue):
        return ast.JsonValue(atom.value)
    elif isinstance(atom, NumericValue):
        return ast.JsonValue(atom.value)
    elif atom == Atom("true"):
        return ast.JsonValue(True)
    elif atom == Atom("false"):
        return ast.JsonValue(False)
    elif isinstance(atom, Atom):
        if atom.name[0] == "$":
            return ast.VariableReference(atom.name[1:])
        else:
            return ast.Identifier(atom.name)


def parse_lambda_expression(it):
    params = list()
    while True:
        var = parse_simple_value(it.next())
        if not isinstance(var, ast.VariableReference):
            raise RuntimeError("Expected variable name, found {}".format(var))
        params.append(var)
        if it.lookahead() in [Atom("using"), Atom("do")]:
            break
        expect_exact(it, ',')

    captures = list()
    if it.lookahead() == Atom("using"):
        it.next()
        while True:
            var = parse_simple_value(it.next())
            if not isinstance(var, ast.VariableReference):
                raise RuntimeError("Expected variable name, found {}".format(var))
            captures.append(var)
            if it.lookahead() == Atom("do"):
                break
            expect_exact(it, ',')

    expect_exact(it, Atom("do"))
    expect_exact(it, ':')
    block = list()
    while it.lookahead() != Atom("end"):
        block.append(parse_block_expression(it))
    it.next()  # take end
    expr = ast.BlockExpression(block)

    return ast.LambdaExpression(params, captures, expr)


def parse_simple_expression(it):
    atom = it.next()
    if atom == "(":
        expr = parse_complex_expression(it)
        expect_exact(it, ")")
        return expr
    elif atom == Atom("if"):
        cond = parse_simple_expression(it)
        expect_exact(it, ':')
        then = parse_block_expression(it)
        expect_exact(it, Atom("else"))
        expect_exact(it, ':')
        otherwise = parse_block_expression(it)
        expect_exact(it, Atom("end"))
        return ast.IfThenElse(cond, then, otherwise)
    elif atom == Atom("lambda"):
        return parse_lambda_expression(it)
    else:
        return parse_simple_value(atom)


def parse_let_expression(it):
    expect_exact(it, Atom("let"))
    bindings = list()
    while True:
        var = parse_simple_value(it.next())
        if not isinstance(var, ast.VariableReference):
            raise RuntimeError("Expected variable reference, found {}".format(var))
        expect_exact(it, "=")
        val = parse_block_or_simple(it)
        bindings.append((var, val))
        tok = it.lookahead()
        if tok == ';':
            it.next()
            break
        expect_exact(it, ',')

    body = list()
    # consume more until the next end
    while it.lookahead() != Atom("end") and it.lookahead() is not None:
        body.append(parse_block_expression(it))
    return ast.LetExpression(bindings, body)


def parse_function_call(it, func):
    def terminates_call(token):
        if n in [')', ';', ':', ',']:
            return True
        if n in [Atom("end"), Atom("else"), Atom("begin")]:
            return True

        return False

    parameter = list()
    while True:
        n = it.lookahead()
        if terminates_call(n):
            break
        parameter.append(parse_simple_expression(it))
    return ast.CallExpression(func, parameter)


def parse_operator_application(it, left):
    def product(first=None):
        if first is None:
            first = parse_simple_expression(it)
        while True:
            op = it.lookahead()
            if op in [Operator('*'), Operator('/')]:
                it.next()  # take operator
                right = parse_simple_expression(it)
                first = ast.BinaryExpression(
                    ast.BinaryOperator.MUL if op == Operator('*') else ast.BinaryOperator.DIV,
                    first, right
                )
            else:
                break
        return first

    def summation(first=None):
        if first is None:
            first = product()
        while True:
            op = it.lookahead()
            if op in [Operator('+'), Operator('-')]:
                it.next()  # take operator
                right = product()
                first = ast.BinaryExpression(
                    ast.BinaryOperator.ADD if op == Operator('+') else ast.BinaryOperator.SUB,
                    first, right
                )

            else:
                break
        return first

    return summation(product(left))


def parse_complex_expression(it):
    first = parse_simple_expression(it)
    ahead = it.lookahead()
    if isinstance(ahead, Operator):
        return parse_operator_application(it, first)  # operator application
    elif isinstance(ahead, Atom) or ahead == '(':
        return parse_function_call(it, first)
    else:
        return first


def parse_foreach_expression(it):
    expect_exact(it, Atom("foreach"))
    bindings = list()
    while True:
        var = parse_simple_value(it.next())
        if not isinstance(var, ast.VariableReference):
            raise RuntimeError("Expected variable reference, found {}".format(var))
        expect_exact(it, ":")
        val = parse_simple_expression(it)
        bindings.append((var, val))
        tok = it.lookahead()
        if tok == Atom("do"):
            it.next()
            expect_exact(it, ':')
            break
        expect_exact(it, ',')

    body = list()
    # consume more until the next end
    while it.lookahead() != Atom("end"):
        body.append(parse_block_expression(it))
    it.next()  # take the end
    return ast.ForeachExpression(bindings, body)


def parse_block_expression(it):
    atom = it.lookahead()
    if atom == Atom("begin"):
        return parse_block(it)
    elif atom == Atom("cond"):
        return parse_condition(it)
    elif atom == Atom("let"):
        return parse_let_expression(it)
    elif atom == Atom("foreach"):
        return parse_foreach_expression(it)
    else:
        return parse_complex_expression(it)


def parse(source):
    block = list()
    it = LookaheadIterator(atomize(source))
    while it.lookahead() is not None:
        block.append(parse_block_expression(it))
    return ast.BlockExpression(block)
