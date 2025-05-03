import os
import unittest
from typing import TypedDict

import yaml

from pyquerymatch import deserialize, match
from pyquerymatch.query import build


class SqlTestCase(TypedDict):
    query: str
    params: dict


class TestCase(TypedDict):
    query: dict
    result: list[dict]
    sql: SqlTestCase | None


class TestMatchers(unittest.TestCase):
    def read_resource(self, name) -> bytes:
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "resources", name
        )
        with open(file_path, "rb") as fp:
            return fp.read()

    def impl_test_resource(self, name):
        resource = self.read_resource(name)

        iterable = yaml.safe_load_all(resource)

        base = next(iterable)
        assert base["data"] is not None, "data not specified at root"

        for case in iterable:
            case = TestCase(**case)
            matchers = list(deserialize(case["query"]))
            print(f"{matchers=}")
            expected = case["result"]
            actual = [x for x in base["data"] if match(x, matchers)]
            print(f"{expected=} {actual=}")
            self.assertEqual(expected, actual)

            sql = case.get("sql")
            if sql is not None:
                sql = SqlTestCase(**sql)
                (query, params) = build(matchers)
                print(f"{query=} {params=}")
                self.assertEqual(sql["query"], query)
                self.assertEqual(sql["params"], params)

    def test_simple_eq(self):
        self.impl_test_resource("00-simple-00.yaml")
        self.impl_test_resource("00-simple-01.yaml")
        self.impl_test_resource("00-simple-02.yaml")

    def test_comparisons(self):
        self.impl_test_resource("01-comparison.yaml")

    def test_logical(self):
        self.impl_test_resource("02-logical.yaml")

    def test_logical_root(self):
        self.impl_test_resource("03-logical-root.yaml")

    def test_exists(self):
        self.impl_test_resource("04-exists.yaml")

    def test_dot_notation(self):
        self.impl_test_resource("05-dot-notation.yaml")
