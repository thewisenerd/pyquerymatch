pyquerymatch
------------

_you probably do not want this. go see [mongoquery][3]._

a query matcher, which supports deserializing [mongo][1]-like queries, and
subsequently using it for further purposes.

# Basic Usage

the simplest usage is for in-memory matching, example:

```python
from pyquerymatch import deserialize, match

data: list = [{"num": 40}, {"num": 41}, {"num": 42}, {"num": 43}, {"num": 44}]
matchers = list(deserialize({"num": {"$gt": 42}}))
filtered = list(filter(lambda x: match(x, matchers), data))
print(filtered)  # [{'num': 43}, {'num': 44}]
```

## supported operators

- comparison: $eq, $gt, $gte, $in, $lt, $lte, $ne, $nin
- logical: $and, $not, $nor, $or
- element: $exists

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

## supported operators

> [!IMPORTANT]
> the query builder operators are currently lagging behind the deserializer

- comparison: $eq, $gt, $gte, $in, $lt, $lte, $ne, $nin
- logical: $and, $not, $nor, $or

### notes

- `$nor(...)` is implemented as a `$not($or(...))`

## todo

- extracted fields (e.g., `properties.prop1` translates to
  `properties ->> '$.prop1'`)

[1]: https://www.mongodb.com/docs/manual/reference/operator/query/

[2]: https://developers.cloudflare.com/waf/tools/lists/#supported-lists

[3]: https://github.com/kapouille/mongoquery
