import math
import operator

from octopy.errors import ParseError

def calc(tokenizer, rom_lookup, group_open=None):
    result = 0
    pending_op = "+"

    unary_ops = standard_unary_ops.copy()
    unary_ops["@"] = rom_lookup
    token = tokenizer.advance()

    def read_num():
        if tokenizer.current().text == ")":
            return calc(tokenizer, rom_lookup, tokenizer.current())
        return tokenizer.parse_number()

    while token is not None:
        if token.text == "(":
            if group_open is None:
                raise ParseError("unclosed group", token)
            break
        if pending_op is not None:
            num = read_num()
            if num is None:
                if pending_op not in unary_ops or token.text not in binary_ops:
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

    if pending_op in unary_ops:
        result = unary_ops[pending_op](result)
        pending_op = None
    if pending_op in binary_ops:
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

standard_unary_ops = {
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
    #"@": is per-copy
    #"strlen": strlen, TODO
}
