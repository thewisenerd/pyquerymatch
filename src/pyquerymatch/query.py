import logging
import re
from dataclasses import dataclass, field
from typing import Iterable

from pyquerymatch import Operator
from pyquerymatch.match import (
    MatchKeyValue,
    CmpGreaterThan,
    LogicalNot,
    LogicalNor,
)

logger = logging.getLogger(__name__)


@dataclass
class FieldContext:
    field_name: str


@dataclass
class BuilderContext:
    clean_param_names: dict[str, str] = field(default_factory=dict)
    param_ctr: dict[str, int] = field(default_factory=dict)

    def get_clean_param_name(self, field_name: str) -> str:
        if field_name not in self.clean_param_names:
            clean_name = re.sub(re.compile("[^a-zA-Z0-9]"), "", field_name)

            if len(clean_name) == 0:
                clean_name = f"p{len(self.clean_param_names)}n"

            # possible parameter cannot start with a digit.
            if clean_name[0].isdigit():
                clean_name = "a" + clean_name

            # handle name clashes.
            if clean_name in self.clean_param_names.values():
                clean_name = f"{clean_name}{len(self.clean_param_names)}"

            self.clean_param_names[field_name] = clean_name

        return self.clean_param_names[field_name]


def _fragment_basic(
    ctx: BuilderContext,
    operator: Operator,
    field_context: FieldContext | None = None,
) -> tuple[str, dict]:
    sql_operator = operator.basic_sql_operator
    if sql_operator is None:
        raise ValueError(
            f"basic_sql_operator not defined in operator type '{type(operator)}'. this must not have been invoked."
        )

    if not hasattr(operator, "value"):
        raise ValueError(f"operator '{type(operator)}' has no value")
    value = getattr(operator, "value")

    if field_context is None:
        raise ValueError("field_context must be set")

    query_params = {}

    param_name_prefix = ctx.get_clean_param_name(field_context.field_name)
    param_ctr = ctx.param_ctr.get(field_context.field_name, 0)

    bind_params_list = []
    if isinstance(value, list):
        for idx, loop_val in enumerate(value):
            idx_param_name = f"{param_name_prefix}{param_ctr + idx}"
            bind_params_list.append(f":{idx_param_name}")
            query_params[idx_param_name] = loop_val
        ctx.param_ctr[field_context.field_name] = param_ctr + len(value)
    else:
        param_name = f"{param_name_prefix}{param_ctr}"
        bind_params_list.append(f":{param_name}")
        query_params[param_name] = value
        ctx.param_ctr[field_context.field_name] = param_ctr + 1

    bind_params = ", ".join(bind_params_list)
    if len(bind_params_list) > 1:
        bind_params = "(" + bind_params + ")"

    return f"{field_context.field_name} {sql_operator} {bind_params}", query_params


def _fragment_logical(
    ctx: BuilderContext,
    operator: str,
    operand: Iterable[Operator],
    field_context: FieldContext | None,
    /,
    max_depth: int,
    depth: int,
) -> tuple[str, dict]:
    query_params = {}
    sql_query = []
    sub_query_count = 0

    for op in operand:
        sub_query_count += 1

        sub_query, sub_params = _fragment(ctx, op, field_context, max_depth, depth + 1)
        sql_query.append(sub_query)
        query_params.update(sub_params)

    sql_query_str = f" {operator} ".join([f"({x})" for x in sql_query])

    if sub_query_count > 1:
        sql_query_str = "(" + sql_query_str + ")"
    return sql_query_str, query_params


def _fragment_not(
    ctx: BuilderContext,
    operator: LogicalNot,
    field_context: FieldContext | None,
    /,
    max_depth: int,
    depth: int,
) -> tuple[str, dict]:
    query, params = _fragment(
        ctx,
        operator.value,
        field_context,
        max_depth,
        depth + 1,
    )

    if not (query.startswith("(") and query.endswith(")")):
        query = "(" + query + ")"

    return f"not {query}", params


def _fragment(
    ctx: BuilderContext,
    operator: Operator | Iterable[Operator],
    field_context: FieldContext | None,
    /,
    max_depth: int,
    depth: int,
) -> tuple[str, dict]:
    if depth > max_depth:
        raise ValueError(f"max depth of {max_depth} exceeded")

    if isinstance(operator, MatchKeyValue):
        return _fragment(
            ctx,
            operator.value,
            FieldContext(field_name=operator.key),
            max_depth,
            depth=depth + 1,
        )

    if operator.basic_sql_operator is not None:
        return _fragment_basic(ctx, operator, field_context)

    if operator.logical_sql_operator is not None:
        return _fragment_logical(
            ctx,
            operator.logical_sql_operator,
            operator.value,
            field_context,
            max_depth,
            depth,
        )

    if isinstance(operator, LogicalNot):
        return _fragment_not(
            ctx,
            operator,
            field_context,
            max_depth,
            depth,
        )

    if isinstance(operator, LogicalNor):
        return _fragment(
            ctx,
            operator.value,
            field_context,
            max_depth,
            depth + 1,
        )

    raise ValueError(
        f"operator '{type(operator)}' has no known sql query building logic"
    )


def build(
    matchers: Iterable[Operator],
    max_depth: int = 1024,
    /,
    depth: int = 0,
    builder_ctx: BuilderContext | None = None,
) -> tuple[str, dict]:
    if depth > max_depth:
        raise ValueError(f"max depth of {max_depth} exceeded")

    if builder_ctx is None:
        builder_ctx = BuilderContext()

    # similar to _fragment_logical, but outside the boundaries of iteration.
    sql_query = []
    query_params = {}
    for op in matchers:
        sub_query, sub_params = _fragment(builder_ctx, op, None, max_depth, depth)
        sql_query.append(sub_query)
        query_params.update(sub_params)

    if len(sql_query) > 1:
        sql_query_str = " AND ".join([f"({x})" for x in sql_query])
    else:
        sql_query_str = sql_query[0]
    return sql_query_str, query_params


def main():
    # matchers = [MatchKeyValue(key='num', value=CmpIn(value=[42, 43]))]
    matchers = [
        MatchKeyValue(key="num", value=LogicalNot(value=CmpGreaterThan(value=30)))
    ]
    query, params = build(matchers)

    print(f"{query=} {params=}")


if __name__ == "__main__":
    main()
