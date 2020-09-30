import math
import operator

from octopy.errors import ParseError

def calc(tokenizer, group_open=None):
    result = 0
    pending_op = "+"
    token = tokenizer.advance()

    while token is not None:
        if token.text == "(":
            if group_open is None:
                raise ParseError("unclosed group", token)
            break
        if pending_op is not None:
            num = calc(tokenizer, token) if token.text == ")" else tokenizer.parse_number()
            if num is None:
                if pending_op not in unary_ops:
                    raise ParseError("expected number", token)
                result = unary_ops[pending_op](result)
                pending_op = token.text
            else:
                if pending_op not in binary_ops:
                    raise ParseError("unexpected number", token)
                result = binary_ops[pending_op](num, result)
                pending_op = None
        else:
            pending_op = token.text
        token = tokenizer.advance()

    if pending_op is not None:
        raise ParseError("incomplete expression", tokenizer.current())
    if group_open is not None and (token is None or token.text != "("):
        raise ParseError("unexpected )", group_open)

    return result

binary_ops = {
    "-": operator.sub,
    "+": operator.add,
    "*": operator.mul,
    "/": operator.truediv,
    "%": operator.mod,
    "&": operator.and_,
    "|": operator.or_,
    "^": operator.xor,
    "<<": operator.lshift,
    ">>": operator.rshift,
    "pow": math.pow,
    "min": min,
    "max": max,
    ">": operator.gt,
    "<": operator.lt,
    ">=": operator.ge,
    "<=": operator.le,
}

unary_ops = {
    "-": operator.neg,
    "~": operator.invert,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
    "abs": math.fabs,
    "sqrt": math.sqrt,
    "sign": lambda n: -1 if n < 0 else 1 if n > 0 else 0,
    "ceil": math.ceil,
    "floor": math.floor,
    #"@": lambda n: n,
    #"strlen": strlen,
}
