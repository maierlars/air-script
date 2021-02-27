import airast


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


class ParserError(Exception):
    def __init__(self, msg, location=None):
        self.msg = msg
        self.location = location

    def __str__(self):
        return "at {}: {}".format(self.location, self.msg)


class Token:
    def __init__(self, location=None):
        self.location = location


class NumericValue(Token):
    def __init__(self, value, location=None):
        super().__init__(location)
        self.value = value

    def __str__(self):
        return '{}f'.format(self.value)


class StringValue(Token):
    def __init__(self, value, location=None):
        super().__init__(location)
        self.value = value

    def __str__(self):
        return '"{}"'.format(self.value)


class Atom(Token):
    def __init__(self, name, location=None):
        super().__init__(location)
        self.name = name

    def __eq__(self, other):
        if not isinstance(other, Atom):
            return NotImplemented
        return self.name.lower() == other.name.lower()

    def __str__(self):
        return "`{}`".format(self.name)


class Operator(Token):
    def __init__(self, op, location=None):
        super().__init__(location)
        self.op = op

    def __eq__(self, other):
        if not isinstance(other, Operator):
            return NotImplemented
        return self.op == other.op

    def __str__(self):
        return "{}".format(self.op)


class Symbol(Token):
    def __init__(self, sym, location=None):
        super().__init__(location)
        self.sym = sym

    def __eq__(self, other):
        if not isinstance(other, Symbol):
            return NotImplemented
        return self.sym == other.sym

    def __str__(self):
        return "{}".format(self.sym)


def atomize(source):
    space = " \r\n\t\v"
    atom_terminator = "()[]{}\"#:;,`" + space
    special_chars = "=+-*/"
    operators = "+-*/|><?!"
    line = 1
    line_start = 0
    i = 0

    def get_position():
        return line, i - line_start + 1

    while i < len(source):
        start_offset = get_position()

        def source_location():
            return airast.SourceLocation(start_offset, get_position())

        if source[i] in space:
            if source[i] == "\n":
                line += 1
                line_start = i + 1

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
                    raise ParserError("Unterminated string constant")
            i += 1
            yield StringValue(value, source_location())
        elif source[i] == '`':
            value = ""
            i += 1
            while source[i] != '`':
                value += source[i]
                i += 1
                if i >= len(source):
                    raise RuntimeError("Unterminated quote sequence")
            i += 1
            yield Atom(value, source_location())
        elif source[i] in operators:
            c = source[i]
            i += 1
            yield Operator(c, source_location())
        elif source[i] in atom_terminator + special_chars:
            c = source[i]
            i += 1
            yield Symbol(c, source_location())
        else:
            # read atom
            start = i
            while i < len(source) and source[i] not in atom_terminator:
                i += 1
            value = source[start:i]
            if value[0] in "0123456789":
                yield NumericValue(float(value), source_location())
            else:
                yield Atom(value, source_location())


def expect_exact(it, expected):
    atom = it.next()
    if atom != expected:
        raise ParserError("Unexpected {}, expected {}".format(atom, expected), atom.location)


def parse_block(it):
    block = list()
    expect_exact(it, Atom("begin"))
    while it.lookahead() != Atom("end"):
        block.append(parse_block_expression(it))
    it.next()  # take end
    return airast.BlockExpression(block)


def parse_block_or_simple(it):
    if it.lookahead() == Atom("begin"):
        return parse_block_expression(it)
    else:
        return parse_simple_expression(it)


def parse_block_or_complex(it):
    if it.lookahead() == Atom("begin"):
        return parse_block_expression(it)
    else:
        return parse_complex_expression(it)


def parse_condition(it):
    cases = list()
    expect_exact(it, Atom("cond"))
    expect_exact(it, Symbol(":"))
    while it.lookahead() == Atom("if"):
        it.next()  # take the if
        cond = parse_complex_expression(it)
        expect_exact(it, Atom("do"))
        expect_exact(it, Symbol(':'))
        then = parse_complex_expression(it)
        cases.append((cond, then))
    if it.lookahead() == Atom("otherwise"):
        it.next()
        expect_exact(it, Symbol(':'))
        then = parse_complex_expression(it)
        cases.append((airast.JsonValue(True), then))
    expect_exact(it, Atom("end"))
    return airast.CaseExpression(cases)


def parse_lambda_expression(it):
    expect_exact(it, Atom("lambda"))
    params = list()
    while True:
        var = parse_simple_value(it.next())
        if not isinstance(var, airast.VariableReference):
            raise RuntimeError("Expected variable name, found {}".format(var), var.location)
        params.append(var)
        if it.lookahead() in [Atom("using"), Atom("do")]:
            break
        expect_exact(it, Symbol('', ''))

    captures = list()
    if it.lookahead() == Atom("using"):
        it.next()
        while True:
            var = parse_simple_value(it.next())
            if not isinstance(var, airast.VariableReference):
                raise RuntimeError("Expected variable name, found {}".format(var))
            captures.append(var)
            if it.lookahead() == Atom("do"):
                break
            expect_exact(it, Symbol(','))

    expect_exact(it, Atom("do"))
    expect_exact(it, Symbol(':'))
    block = list()
    while it.lookahead() != Atom("end"):
        block.append(parse_block_expression(it))
    it.next()  # take end
    expr = airast.BlockExpression(block)

    return airast.LambdaExpression(params, captures, expr)


def parse_foreach_expression(it):
    expect_exact(it, Atom("foreach"))
    bindings = list()
    while True:
        var = parse_simple_value(it.next())
        if not isinstance(var, airast.VariableReference):
            raise RuntimeError("Expected variable reference, found {}".format(var))
        expect_exact(it, Atom("in"))
        val = parse_simple_expression(it)
        bindings.append((var, val))
        tok = it.lookahead()
        if tok == Atom("do"):
            it.next()
            expect_exact(it, Symbol(':'))
            break
        expect_exact(it, Symbol(','))

    body = list()
    # consume more until the next end
    while it.lookahead() != Atom("end"):
        body.append(parse_block_expression(it))
    it.next()  # take the end
    return airast.ForeachExpression(bindings, body)


def parse_let_expression(it):
    expect_exact(it, Atom("let"))
    bindings = list()
    while True:
        var = parse_simple_value(it.next())
        if not isinstance(var, airast.VariableReference):
            raise RuntimeError("Expected variable reference, found {}".format(var))
        expect_exact(it, Symbol("="))
        val = parse_block_or_complex(it)
        bindings.append((var, val))
        tok = it.lookahead()
        if tok == Symbol(';'):
            it.next()
            break
        expect_exact(it, Symbol(','))

    body = list()
    # consume more until the next end
    while it.lookahead() != Atom("end") and it.lookahead() is not None:
        body.append(parse_block_expression(it))
    return airast.LetExpression(bindings, body)


def parse_function_call(it, func):
    def terminates_call(token):
        if token == Symbol('('):
            return False
        if isinstance(token, Symbol) or isinstance(token, Operator):
            return True
        if n in [Atom("end"), Atom("else"), Atom("begin"), Atom("do")]:
            return True

        return False

    parameter = list()
    while True:
        n = it.lookahead()
        if terminates_call(n):
            break
        parameter.append(parse_simple_expression(it))
    return airast.CallExpression(func, parameter)


def parse_operator(it):
    op = it.next()
    if op == Operator('+'):
        return airast.BinaryOperator.ADD
    elif op == Operator('-'):
        return airast.BinaryOperator.SUB
    elif op == Operator('*'):
        return airast.BinaryOperator.MUL
    elif op == Operator('/'):
        return airast.BinaryOperator.DIV

    elif op == Atom("and"):
        return airast.BinaryOperator.AND
    elif op == Atom("or"):
        return airast.BinaryOperator.OR

    elif op == Operator("!"):
        expect_exact(it, Symbol("="))
        return airast.BinaryOperator.NEQ
    elif op == Symbol("="):
        expect_exact(it, Symbol("="))
        return airast.BinaryOperator.EQ

    elif op == Operator('<'):
        if it.lookahead() == Symbol('='):
            it.next()
            return airast.BinaryOperator.LE
        return airast.BinaryOperator.LT
    elif op == Operator('>'):
        if it.lookahead() == Symbol('='):
            it.next()
            return airast.BinaryOperator.GE
        return airast.BinaryOperator.GT

    else:
        raise ParserError("Unknown operator {}".format(op), op.location)


def is_operator_ahead(it):
    ahead = it.lookahead()
    if isinstance(ahead, Operator):
        return True
    elif ahead in [Atom("and"), Atom("or"), Symbol("=")]:
        return True
    return False


def parse_operator_expression(it, first):
    operand_stack = [first]
    operator_stack = []

    def reduce_stacks():
        assert len(operand_stack) >= 2
        right = operand_stack.pop()
        left = operand_stack.pop()
        assert len(operator_stack) >= 1
        next_op = operator_stack.pop()
        operand_stack.append(airast.BinaryExpression(next_op, left, right))

    while is_operator_ahead(it):
        op = parse_operator(it)
        while len(operator_stack) > 0 and operator_stack[-1].precedence() >= op.precedence():
            reduce_stacks()
        operator_stack.append(op)

        opnd = parse_simple_expression(it)
        operand_stack.append(opnd)

    while len(operator_stack) != 0:
        reduce_stacks()

    assert len(operand_stack) == 1
    return operand_stack[0]


def parse_simple_value(atom):
    if isinstance(atom, StringValue):
        return airast.JsonValue(atom.value)
    elif isinstance(atom, NumericValue):
        return airast.JsonValue(atom.value)
    elif atom == Atom("true"):
        return airast.JsonValue(True)
    elif atom == Atom("false"):
        return airast.JsonValue(False)
    elif isinstance(atom, Atom):
        if atom.name[0] == "$":
            return airast.VariableReference(atom.name[1:])
        else:
            return airast.Identifier(atom.name)


def parse_simple_expression(it):
    atom = it.next()
    if atom == Symbol("("):
        expr = parse_complex_expression(it)
        expect_exact(it, Symbol(")"))
        return expr
    elif atom == Operator('-'):
        expr = parse_simple_expression(it)
        return airast.UnaryExpression(airast.UnaryOperator.NEG, expr)
    else:
        return parse_simple_value(atom)


def parse_composed_expression(it):
    first = parse_simple_expression(it)
    ahead = it.lookahead()
    if isinstance(ahead, Operator):
        return parse_operator_expression(it, first)  # operator application
    elif isinstance(ahead, Atom) or ahead == Symbol('('):
        return parse_function_call(it, first)
    else:
        return first


def parse_if_else_expression(it):
    expect_exact(it, Atom("if"))
    cond = parse_simple_expression(it)
    expect_exact(it, Symbol(':'))
    then = parse_block_expression(it)
    expect_exact(it, Atom("else"))
    expect_exact(it, Symbol(':'))
    otherwise = parse_block_expression(it)
    expect_exact(it, Atom("end"))
    return airast.IfThenElse(cond, then, otherwise)


def parse_complex_expression(it):
    ahead = it.lookahead()
    if ahead == Atom("if"):
        return parse_if_else_expression(it)
    elif ahead == Atom("lambda"):
        return parse_lambda_expression(it)
    else:
        return parse_composed_expression(it)


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
        expr = parse_complex_expression(it)
        if it.lookahead() == Symbol(';'):
            it.next()
        return expr


def parse(source):
    block = list()
    it = LookaheadIterator(atomize(source))
    while it.lookahead() is not None:
        block.append(parse_block_expression(it))
    return airast.BlockExpression(block)
