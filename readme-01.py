from pyquerymatch import deserialize, match

data: list = [{"num": 40},{"num": 41},{"num": 42},{"num": 43},{"num": 44}]
matchers = list(deserialize({"num": {"$gt": 42}}))
filtered = list(filter(lambda x: match(x, matchers), data))
print(filtered) # [{'num': 43}, {'num': 44}]
assert filtered == [{"num": 43},{"num": 44}]
