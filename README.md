pyquerymatch
------------

_you probably do not want this. go see [mongoquery][3]._

a query matcher, which supports deserializing [mongo][1]-like queries, and
subsequently using it for further purposes.

this only supports a subset of the query notation supported in MongoDB, see
the [supported operators](#supported-operators) section. this is a conscious
choice!

# Basic Usage

the simplest usage is for in-memory matching, example:

```python
from pyquerymatch import deserialize, match

data: list = [{"num": 40}, {"num": 41}, {"num": 42}, {"num": 43}, {"num": 44}]
matchers = list(deserialize({"num": {"$gt": 42}}))
filtered = list(filter(lambda x: match(x, matchers), data))
print(filtered)  # [{'num': 43}, {'num': 44}]
```

# SQL query builder

```python
from pyquerymatch import deserialize, build

matchers = list(deserialize({"num": {"$gt": 42}}))
(query, params) = build(matchers)
print(f"{query=}")  # query='num > :num0'
print(f"{params=}")  # params={'num0': 42}
```

all parameters are strictly parameterized to avoid oopsies.
for very large lists, we intend to have something similar to the [Cloudflare][2]
notation, that somehow does sub-queries.

# supported operators

- simple: `{ field: $val }`
- comparison: $eq, $gt, $gte, $in, $lt, $lte, $ne, $nin
- logical: $and, $not, $nor, $or
- element: $exists

# notes

- `$nor(...)` is implemented as a `$not($or(...))`

# todo

- validate null semantics for in-memory matchers

[1]: https://www.mongodb.com/docs/manual/reference/operator/query/

[2]: https://developers.cloudflare.com/waf/tools/lists/#supported-lists

[3]: https://github.com/kapouille/mongoquery
