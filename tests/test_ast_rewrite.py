import pytest
from textwrap import dedent

from aura.analyzers.python.nodes import *
from aura.analyzers.python.visitor import Visitor
from aura.analyzers.python_src_inspector import collect
from aura.uri_handlers.base import ScanLocation


def process_source_code(src: str, single=True) -> NodeType:
    tree = collect(dedent(src), minimal=True)
    loc = ScanLocation(location="<unknown>")

    v = Visitor.run_stages(location=loc, stages=("convert", "rewrite"), ast_tree=tree)
    if single:
        return v.tree[-1]
    else:
        return v.tree


def test_var_propagation_call_argument():
    # Should be rewritten to x(10)
    src = """\
    c = 10
    x(c)
    """
    tree = process_source_code(src)
    assert isinstance(tree, Call)
    assert len(tree.args) == 1
    assert isinstance(tree.args[0], Number), tree.args[0]


def test_call_rename():
    src = """
    x = print
    print("Hello world")
    """
    tree = process_source_code(src)
    assert isinstance(tree, Call)
    assert tree.full_name == "print"


def test_replace_string():
    src = """
    "something".replace("s", "a")
    """
    tree = process_source_code(src)
    assert isinstance(tree, String)
    assert str(tree) == "aomething"


def test_binop_string():
    src = """
    "hello_" + "world"
    """
    tree = process_source_code(src)
    assert isinstance(tree, String)
    assert str(tree) == "hello_world"


def test_binop_numbers():
    src = """
    20 + 22
    """
    tree = process_source_code(src)
    assert isinstance(tree, Number)
    assert int(tree) == 42


def test_binop_string_vars():
    src = """
    x = "hello_"
    y = "world"
    x + y
    """
    tree = process_source_code(src)
    assert isinstance(tree, String)
    assert str(tree) == "hello_world"


@pytest.mark.parametrize(
    "src,result", (
    ("'hello_world'[1:]", 'ello_world'),
    ("'hello_world'[:5]", 'hello'),
    ("'hello_world'[::2]", 'hlowrd'),
    ("'hello_world'[::-1]", 'dlrow_olleh'),
    ("'hello_world'[-1:0:-2]", 'drwol')
))
def test_string_slice(src, result):
    tree = process_source_code(src)
    assert isinstance(tree, String)
    assert str(tree) == result


@pytest.mark.parametrize(
    "src,result", (
    ("'aGVsbG9fd29ybGQ='.decode('base64')", "hello_world"),
))
def test_inline_decode(src, result):
    tree = process_source_code(src)
    assert str(tree) == result


def test_subscript_variable_resolving():
    src = """
    x = "Hello world"
    y = x
    y[::2]
    """
    tree = process_source_code(src)
    assert isinstance(tree, String)
    assert str(tree) == 'Hlowrd'


def test_return_statement_constat_propagation():
    src = """
    def func():
        x = 10
        return x
    """
    tree = process_source_code(src)
    assert isinstance(tree, FunctionDef)

    last = tree.body[-1]

    assert isinstance(last, ReturnStmt)
    assert isinstance(last.value, Number)
    assert int(last.value) == 10


def test_attribute_variable_replace():
    src = """
    x = "hello"
    x.replace("l", "s")
    """
    tree = process_source_code(src)
    assert isinstance(tree, String)
    assert str(tree) == "hesso"


def test_variable_propagation():
    src = """
    a = 42
    b = a
    c = b
    d = c
    d + 0
    """
    tree = process_source_code(src)
    assert isinstance(tree, Number)
    assert int(tree) == 42