"""
TODO:
- none/null semantics
- better item passing semantics when root is not a KeyValueOperator
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import (
    Any,
    Generator,
    Generic,
    Iterable,
    Protocol,
    Type,
    TypeVar,
    get_origin,
    get_type_hints,
)

logger = logging.getLogger(__name__)


# https://github.com/python/typing/issues/59
# https://stackoverflow.com/a/37669538
class Comparable(Protocol):
    @abstractmethod
    def __lt__(self, other: Any) -> bool: ...


T = TypeVar("T")
CT = TypeVar("CT", bound=Comparable)


class ItemValueWrapper(Generic[T]):
    def __init__(self, item: dict, exists: bool, value: T | None):
        self.item = item

        self.exists = exists
        self.value = value


def _unwrap(value: T | ItemValueWrapper[T] | None) -> T | None:
    if isinstance(value, ItemValueWrapper):
        return value.value
    return value


class Operator(ABC):
    operator: str

    @abstractmethod
    def match(self, value: ...) -> bool:
        pass


@dataclass
class CmpEqual(Generic[CT], Operator):
    operator = "$eq"
    value: CT | None

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) == self.value


@dataclass
class CmpGreaterThan(Generic[CT], Operator):
    operator = "$gt"
    value: CT | None

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) > self.value


@dataclass
class CmpGreaterThanOrEqual(Generic[CT], Operator):
    operator = "$gte"
    value: CT | None

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) >= self.value


@dataclass
class CmpIn(Generic[CT], Operator):
    operator = "$in"
    value: list[CT]

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) in self.value


@dataclass
class CmpLessThan(Generic[CT], Operator):
    operator = "$lt"
    value: CT | None

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) < self.value


@dataclass
class CmpLessThanOrEqual(Generic[CT], Operator):
    operator = "$lte"
    value: CT | None

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) <= self.value


@dataclass
class CmpNotEqual(Generic[CT], Operator):
    operator = "$ne"
    value: CT | None

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) != self.value


@dataclass
class CmpNotIn(Generic[CT], Operator):
    operator = "$nin"
    value: list[CT]

    def match(self, value: CT | ItemValueWrapper[CT] | None) -> bool:
        return _unwrap(value) not in self.value


@dataclass
class LogicalAnd(Generic[CT], Operator):
    operator = "$and"
    value: list[Operator]

    def match(self, theirs: CT | ItemValueWrapper[CT] | None) -> bool:
        return all(op.match(theirs) for op in self.value)


@dataclass
class LogicalNot(Generic[CT], Operator):
    operator = "$not"
    value: Operator

    def match(self, theirs: CT | ItemValueWrapper[CT] | None) -> bool:
        return not self.value.match(theirs)


@dataclass
class LogicalNor(Generic[CT], Operator):
    operator = "$nor"
    value: list[Operator]

    def match(self, theirs: CT | ItemValueWrapper[CT] | None) -> bool:
        return not any(op.match(theirs) for op in self.value)


@dataclass
class LogicalOr(Generic[CT], Operator):
    operator = "$or"
    value: list[Operator]

    def match(self, theirs: CT | ItemValueWrapper[CT] | None) -> bool:
        return any(op.match(theirs) for op in self.value)


@dataclass
class Exists(Generic[CT], Operator):
    operator = "$exists"
    value: bool

    def match(self, item: ItemValueWrapper[CT]) -> bool:
        if not isinstance(item, ItemValueWrapper):
            raise ValueError("ExistsOperator can only be used with an ItemValueWrapper")

        return item.exists == self.value


@dataclass
class MatchKeyValue(Generic[CT], Operator):
    operator = "$kv"
    key: str
    value: Operator

    def match(self, item: dict) -> bool:
        if not isinstance(item, dict):
            raise ValueError("KeyValueOperator can only be used with a dict")

        return self.value.match(
            ItemValueWrapper(item, self.key in item, item.get(self.key, None))
        )


KNOWN_VAL_OPERATORS: dict[str, Type[Operator]] = {
    CmpEqual.operator: CmpEqual,
    CmpGreaterThan.operator: CmpGreaterThan,
    CmpGreaterThanOrEqual.operator: CmpGreaterThanOrEqual,
    CmpIn.operator: CmpIn,
    CmpLessThan.operator: CmpLessThan,
    CmpLessThanOrEqual.operator: CmpLessThanOrEqual,
    CmpNotEqual.operator: CmpNotEqual,
    CmpNotIn.operator: CmpNotIn,
    Exists.operator: Exists,
}

KNOWN_LOGICAL_OPERATORS: dict[str, Type[Operator]] = {
    LogicalAnd.operator: LogicalAnd,
    LogicalNot.operator: LogicalNot,
    LogicalNor.operator: LogicalNor,
    LogicalOr.operator: LogicalOr,
}

_KIND_UNSET = 0
_KIND_FIELD = 1
_KIND_OPERATOR = 2


def _check_and_set_kind(kind: int, new_kind: int) -> int:
    if kind == _KIND_UNSET:
        return new_kind
    if kind != new_kind:
        raise ValueError(
            "inconsistent kind, cannot mix fields and operators in a query"
        )
    return kind


def _at_least(
    n: int,
    generator: Generator[T, None, None],
) -> Generator[T, None, None]:
    count = 0
    for op in generator:
        yield op
        count += 1

    if count < n:
        raise ValueError(f"too few values, expected at least '{n}' values")


def _at_most(
    n: int,
    generator: Generator[T, None, None],
) -> Generator[T, None, None]:
    count = 0
    for op in generator:
        if count >= n:
            raise ValueError(f"too many values, only expected '{n}' values")

        yield op
        count += 1


def _check_value_type(
    cls: Type[Operator],
    value: Any,
) -> Any:
    try:
        type_hints = get_type_hints(cls)["value"]
    except KeyError:
        logger.warning("no type hint found for 'value' in class '%s'", cls)
        return value

    origin = get_origin(type_hints)
    if origin == list:
        if not isinstance(value, origin):
            raise ValueError(
                f"expected {origin}, got '{type(value)}' for operator '{cls.operator}'"
            )

    return value


def deserialize(
    query: dict[str, Any], max_depth: int = 1024, /, depth=0
) -> Generator[Operator, None, None]:
    if depth > max_depth:
        raise ValueError(f"max depth of {max_depth} exceeded")

    if depth == 0 and not isinstance(query, dict):
        raise ValueError("query must be a dict")

    kind = _KIND_UNSET
    for key, value in query.items():
        if key.startswith("$"):
            kind = _check_and_set_kind(kind, _KIND_FIELD)

            if key in KNOWN_VAL_OPERATORS:
                cls = KNOWN_VAL_OPERATORS[key]
                yield cls(_check_value_type(cls, value))
            elif key in KNOWN_LOGICAL_OPERATORS:
                cls = KNOWN_LOGICAL_OPERATORS[key]
                # input for {and, or, nor} is always a list
                if key in {
                    LogicalAnd.operator,
                    LogicalNor.operator,
                    LogicalOr.operator,
                }:
                    if not isinstance(value, list):
                        raise ValueError(f"'{key}' must be a list")
                    operators = [
                        list(
                            _at_least(
                                1,
                                _at_most(
                                    1,
                                    deserialize(x, max_depth, depth + 1),
                                ),
                            )
                        )[0]
                        for x in value
                    ]
                    yield cls(_check_value_type(cls, operators))
                # input for {not} is always a single operator
                # if multiple are provided, 'and' the whole thing
                elif key == LogicalNot.operator:
                    if not isinstance(value, dict):
                        raise ValueError(f"'{key}' must be a dict")
                    operators = list(
                        _at_least(1, deserialize(value, max_depth, depth + 1))
                    )
                    if len(operators) == 1:
                        yield LogicalNot(operators[0])
                    else:
                        yield LogicalNot(LogicalAnd(operators))
            else:
                raise ValueError(f"unknown operator '{key}'")
        else:
            kind = _check_and_set_kind(kind, _KIND_OPERATOR)

            operators = list(_at_least(1, deserialize(value, max_depth, depth + 1)))
            if len(operators) == 1:
                yield MatchKeyValue(key, operators[0])
            else:
                yield MatchKeyValue(key, LogicalAnd(operators))


def match(
    item: dict,
    matchers: Iterable[Operator],
) -> bool:
    """
    simply provided as a helper for a reference implementation.
    possibly deal with object wrapping in the future.
    """
    return all(m.match(item) for m in matchers)
