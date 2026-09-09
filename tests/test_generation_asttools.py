import ast
import os
import shutil
import unittest
from pathlib import Path

from agentstack.generation import asttools

BASE_PATH = Path(__file__).parent

class TestGenerationASTTools(unittest.TestCase):
    def setUp(self):
        self.project_dir = BASE_PATH / 'tmp' / 'asttools'
        os.makedirs(self.project_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.project_dir)

    def test_edit_node_range(self):
        # Create a sample Python file
        sample_code = """
def hello():
    print("Hello, World!")

def goodbye():
    print("Goodbye, World!")
"""
        file_path = self.project_dir / "sample.py"
        with open(file_path, "w") as f:
            f.write(sample_code)

        # Use the File class to manipulate the file
        with asttools.File(file_path) as f:
            # Find the range of the hello function
            hello_func = next(node for node in f.tree.body if isinstance(node, ast.FunctionDef) and node.name == "hello")
            start, end = f.get_node_range(hello_func)

            # Replace the hello function with a new implementation
            new_func = """def hello():
    print("Hello, Universe!")"""
            f.edit_node_range(start, end, new_func)

        # Read the modified file and check its contents
        with open(file_path, "r") as f:
            modified_code = f.read()

        expected_code = """
def hello():
    print("Hello, Universe!")

def goodbye():
    print("Goodbye, World!")
"""
        self.assertEqual(modified_code.strip(), expected_code.strip())

    def test_render_node(self):
        file_path = self.project_dir / "sample.py"
        file_path.touch()
        file = asttools.File(file_path)
        
        # Test rendering a string
        string_input = "print('Hello, World!')"
        self.assertEqual(file._render_node(string_input), string_input)

        # Test rendering an AST node
        ast_node = ast.Expr(value=ast.Call(
            func=ast.Name(id='print', ctx=ast.Load()),
            args=[ast.Constant(value='Hello, AST!')],
            keywords=[]
        ))
        expected_output = "print('Hello, AST!')"
        self.assertEqual(file._render_node(ast_node), expected_output)

        # Test rendering a more complex AST node
        complex_ast_node = ast.FunctionDef(
            name='greet',
            args=ast.arguments(
                posonlyargs=[],
                args=[ast.arg(arg='name')],
                kwonlyargs=[],
                kw_defaults=[],
                defaults=[]
            ),
            body=[
                ast.Return(
                    value=ast.BinOp(
                        left=ast.Constant(value='Hello, '),
                        op=ast.Add(),
                        right=ast.Name(id='name', ctx=ast.Load())
                    )
                )
            ],
            decorator_list=[]
        )
        expected_complex_output = "def greet(name):\n    return 'Hello, ' + name"
        self.assertEqual(file._render_node(complex_ast_node).strip(), expected_complex_output)

    def test_insert_method(self):
        file_path = self.project_dir / "sample.py"
        file_path.write_text("""class TestClass:
    def existing(self):
        pass""")
        file = asttools.File(file_path)
        class_node = asttools.find_class(file.tree, "TestClass")
        method_node = asttools.find_method_in_class(class_node, "existing")
        _, end = file.get_node_range(method_node)
        file.insert_method(end, """    def method1(self):
        pass""")
        self.assertEqual(file.source, """class TestClass:
    def existing(self):
        pass

    def method1(self):
        pass

""")

        # Test inserting method when there's already a newline at the end
        new_method = """    def method2(self):
        return True"""
        class_node = asttools.find_class(file.tree, "TestClass")
        method_node = asttools.find_method_in_class(class_node, "method1")
        _, end = file.get_node_range(method_node)
        
        file.insert_method(end, new_method)
        self.assertEqual(file.source, """class TestClass:
    def existing(self):
        pass

    def method1(self):
        pass

    def method2(self):
        return True

""")

        # Test inserting method in the middle of existing methods
        new_method = """    def method_middle(self):
        print('middle')"""
        class_node = asttools.find_class(file.tree, "TestClass")
        method_node = asttools.find_method_in_class(class_node, "method1")
        _, end = file.get_node_range(method_node)
        file.insert_method(end, new_method)
        self.assertEqual(file.source, """class TestClass:
    def existing(self):
        pass

    def method1(self):
        pass

    def method_middle(self):
        print('middle')

    def method2(self):
        return True

""")

    def test_ast_query_helpers(self):
        tree = ast.parse("""from os import path
import json

@marker
class Sample:
    @decorated
    def run(self):
        return Worker()

    def plain(self):
        value = Worker()
        self.client.send(value, timeout=1)
        return value
""")
        self.assertEqual([node.module for node in asttools.get_all_imports(tree)], ["os"])
        self.assertIsNone(asttools.find_method(tree, "missing"))
        sample = asttools.find_class(tree, "Sample")
        self.assertEqual(asttools.find_method(sample, "run").name, "run")
        plain_method = asttools.find_method_in_class(sample, "plain")
        self.assertEqual(len(asttools.find_method_calls(plain_method, "send")), 1)
        self.assertEqual(len(asttools.find_method_calls(plain_method, "Worker")), 1)
        self.assertEqual(asttools.find_class_with_decorator(tree, "marker"), [sample])
        self.assertEqual(asttools.find_class_with_regex(tree, r"Sam.*"), [sample])
        self.assertEqual(asttools.find_method_in_class(sample, "plain").name, "plain")
        self.assertEqual([m.name for m in asttools.find_decorated_method_in_class(sample, "decorated")], ["run"])
        instantiation_tree = ast.parse("Worker = Worker()")
        self.assertIsNotNone(asttools.find_class_instantiation(instantiation_tree, "Worker"))
        call = ast.parse("send(timeout=1)").body[0].value
        self.assertEqual(asttools.find_kwarg_in_method_call(call, "timeout").arg, "timeout")

    def test_ast_value_and_tool_helpers(self):
        self.assertEqual(asttools.create_attribute("client", "send").attr, "send")
        self.assertEqual(asttools.get_node_value(ast.parse("client.send").body[0].value), "send")
        self.assertEqual(asttools.get_node_value(ast.Constant(value="value")), "value")
        tool = asttools.create_tool_node("search")
        self.assertEqual(len(asttools.find_tool_nodes(ast.List(elts=[tool]))), 1)
        self.assertEqual(asttools.find_tool_nodes(ast.List(elts=[ast.Name(id="other")])), [])
        file_path = self.project_dir / "remove.py"
        file_path.write_text("value = 1\nother = 2\n")
        file = asttools.File(file_path)
        file.remove_node(file.tree.body[0])
        self.assertEqual(file.source, "\nother = 2\n")
