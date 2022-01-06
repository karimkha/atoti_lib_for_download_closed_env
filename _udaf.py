from __future__ import annotations

from threading import Lock
from typing import Sequence

from ._java_api import JavaApi
from ._operation import Operation
from ._udaf_utils import (
    LongAggregationOperationVisitor,
    MaxAggregationOperationVisitor,
    MeanAggregationOperationVisitor,
    MinAggregationOperationVisitor,
    MultiplyAggregationOperationVisitor,
    ShortAggregationOperationVisitor,
    SingleValueNullableAggregationOperationVisitor,
    SquareSumAggregationOperationVisitor,
    SumAggregationOperationVisitor,
)
from ._udaf_utils.java_operation_visitor import OperationVisitor
from .column import Column

OPERATION_VISITORS = {
    "SUM": SumAggregationOperationVisitor,
    "MEAN": MeanAggregationOperationVisitor,
    "MULTIPLY": MultiplyAggregationOperationVisitor,
    "MIN": MinAggregationOperationVisitor,
    "MAX": MaxAggregationOperationVisitor,
    "SQ_SUM": SquareSumAggregationOperationVisitor,
    "SHORT": ShortAggregationOperationVisitor,
    "LONG": LongAggregationOperationVisitor,
    "SINGLE_VALUE_NULLABLE": SingleValueNullableAggregationOperationVisitor,
}


class AtomicCounter:
    """Threadsafe counter to get unique IDs."""

    def __init__(self):
        self._value = 0
        self._lock = Lock()

    def read_and_increment(self) -> int:
        with self._lock:
            self._value += 1
            return self._value


class UserDefinedAggregateFunction:
    """A class template which builds the sources to compile an AUserDefinedAggregate function at runtime.

    This class parses the combination of operations passed and converts them into Java source code blocks.
    These source code blocks are then compiled using Javassist into a new aggregation function which is then registered on the session.
    """

    _agg_fun: str
    _operation: Operation
    _columns: Sequence[Column]
    column_names: Sequence[str]
    _java_api: JavaApi
    plugin_key: str
    _id_provider = AtomicCounter()

    def __init__(self, operation: Operation, agg_fun: str):
        self._operation = operation
        self._columns = operation.columns
        self.column_names = [column.name for column in self._columns]
        self._agg_fun = agg_fun
        self._java_api = self._columns[0]._table._java_api
        self.plugin_key = f"{''.join(self.column_names)}{UserDefinedAggregateFunction._id_provider.read_and_increment()}.{agg_fun}"

    def register_aggregation_function(self):
        """Generate the required Java source code blocks and pass them to the Java process to be compiled into a new UserDefinedAggregateFunction."""
        visitor_class = OPERATION_VISITORS[self._agg_fun]
        if visitor_class is None:
            raise ValueError("Unsupported aggregation function " + self._agg_fun)
        visitor: OperationVisitor = visitor_class(
            column_names=self.column_names, java_api=self._java_api
        )

        java_operation = visitor.build_java_operation(self._operation)
        self._java_api.register_aggregation_function(
            additional_imports=java_operation.additional_imports,
            additional_methods=java_operation.additional_methods_source_codes,
            contribute_source_code=java_operation.contribute_source_code,
            decontribute_source_code=java_operation.decontribute_source_code,
            merge_source_code=java_operation.merge_source_code,
            terminate_source_code=java_operation.terminate_source_code,
            buffer_types=java_operation.buffer_types,
            output_type=java_operation.output_type,
            plugin_key=self.plugin_key,
        )
