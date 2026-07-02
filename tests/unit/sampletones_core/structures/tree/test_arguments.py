from dataclasses import dataclass
from typing import Any, List, Type
from unittest.mock import Mock

import pytest
from anytree import Node

from sampletones_core.structures.tree import Arguments
from sampletones_core.structures.tree.node import TreeNode
from sampletones_core.structures.tree.type import NodeType
from tests.suite.case import BaseTestCase


@pytest.fixture
def a_node() -> TreeNode:
    return TreeNode("test_node", NodeType.FILE)


class TestArgumentsCreateMethod:
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseTestCase):
        label: str
        args: List[Any]
        exc: Type[Exception]

    INVALID_ARGS_CASES = [
        TestCase(label="empty", args=[], exc=ValueError),
        TestCase(label="missing_node", args=[object()], exc=ValueError),
        TestCase(label="self_is_none", args=[None, Node("placeholder")], exc=TypeError),
    ]

    def test_creates_with_self_and_node(self, a_node: TreeNode) -> None:
        self_ = object()
        result = Arguments.create(method=True, args=[self_, a_node], kwargs={})
        assert result.self is self_
        assert result.node is a_node
        assert result.args == []

    def test_extra_args_captured_in_args(self, a_node: TreeNode) -> None:
        self_ = object()
        result = Arguments.create(method=True, args=[self_, a_node, "x", 42], kwargs={})
        assert result.args == ["x", 42]

    def test_kwargs_preserved(self, a_node: TreeNode) -> None:
        self_ = object()
        result = Arguments.create(method=True, args=[self_, a_node], kwargs={"k": "v"})
        assert result.kwargs == {"k": "v"}

    def test_method_property_is_true(self, a_node: TreeNode) -> None:
        self_ = object()
        result = Arguments.create(method=True, args=[self_, a_node], kwargs={})
        assert result.method is True

    @pytest.mark.parametrize("case", INVALID_ARGS_CASES, ids=lambda c: c.label)
    def test_invalid_args_raises(self, case: "TestArgumentsCreateMethod.TestCase") -> None:
        with pytest.raises(case.exc):
            Arguments.create(method=True, args=case.args, kwargs={})


class TestArgumentsCreateFunction:
    def test_creates_with_node(self, a_node: TreeNode) -> None:
        result = Arguments.create(method=False, args=[a_node], kwargs={})
        assert result.node is a_node
        assert result.self is None
        assert result.args == []

    def test_extra_args_captured_in_args(self, a_node: TreeNode) -> None:
        result = Arguments.create(method=False, args=[a_node, "x", 42], kwargs={})
        assert result.args == ["x", 42]

    def test_method_property_is_false(self, a_node: TreeNode) -> None:
        result = Arguments.create(method=False, args=[a_node], kwargs={})
        assert result.method is False

    def test_empty_args_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            Arguments.create(method=False, args=[], kwargs={})


class TestArgumentsExecute:
    @dataclass(frozen=True, kw_only=True)
    class TestCase(BaseTestCase):
        label: str
        method: bool
        extra_args: List[Any]

    EXECUTE_CASES = [
        TestCase(label="function_node_only", method=False, extra_args=[]),
        TestCase(label="function_with_extra", method=False, extra_args=["x"]),
        TestCase(label="method_self_and_node", method=True, extra_args=[]),
        TestCase(label="method_with_extra", method=True, extra_args=["x"]),
    ]

    @pytest.mark.parametrize("case", EXECUTE_CASES, ids=lambda c: c.label)
    def test_execute_dispatches_correctly(self, a_node: TreeNode, case: "TestArgumentsExecute.TestCase") -> None:
        self_ = object()
        args_list = ([self_, a_node] if case.method else [a_node]) + case.extra_args
        arguments = Arguments.create(method=case.method, args=args_list, kwargs={})
        mock_fn = Mock()
        arguments.execute(mock_fn)
        if case.method:
            mock_fn.assert_called_once_with(self_, a_node, *case.extra_args)
        else:
            mock_fn.assert_called_once_with(a_node, *case.extra_args)
