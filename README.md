you probably do not want this. go see: [mongoquery][3].

the operators are inspired from [MongoDB][1]
we intend to support lists as well, using the [Cloudflare notation][2].

the simplest usage is for in-memory matching, example:

```python
from pyquerymatch import deserialize, match

data: list[...] = [...]
matchers = deserialize(query={...})
filtered = match(data, matchers)
```

[1]: https://www.mongodb.com/docs/manual/reference/operator/query/

[2]: https://developers.cloudflare.com/waf/tools/lists/#supported-lists

[3]: https://github.com/kapouille/mongoquery