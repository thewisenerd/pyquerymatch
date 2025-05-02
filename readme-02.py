from pyquerymatch import deserialize, build

matchers = list(deserialize({"num": {"$gt": 42}}))
(query, params) = build(matchers)
print(f"{query=}") # query='num > :num0'
print(f"{params=}") # params={'num0': 42}
assert query == 'num > :num0'
assert params == {'num0': 42}
