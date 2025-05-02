import os
import unittest
import yaml

from pyquerymatch import deserialize, match, Operator

class TestMatchers(unittest.TestCase):
    def read_resource(self, name) -> bytes:
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "resources", name
        )
        with open(file_path, "rb") as fp:
            return fp.read()

    def impl_test_resource(self, name):
        resource = self.read_resource(name)

        data: list[dict] | None = None
        flip = True
        matchers: list[Operator] | None = None
        for obj in yaml.safe_load_all(resource):
            if data is None:
                data = obj
                print(f"{data=}")
                continue

            if flip:
                flip = False

                matchers = list(deserialize(obj))
                print(f"{matchers=}")
            else:
                flip = True
                expected = obj
                actual = [x for x in data if match(x, matchers)]
                print(f"{expected=} {actual=}")
                self.assertEqual(expected, actual)

    def test_comparisons(self):
        self.impl_test_resource("01-comparison.yaml")

    def test_logical(self):
        self.impl_test_resource("02-logical.yaml")

    def test_logical_root(self):
        self.impl_test_resource("03-logical-root.yaml")

    def test_exists(self):
        self.impl_test_resource("04-exists.yaml")
