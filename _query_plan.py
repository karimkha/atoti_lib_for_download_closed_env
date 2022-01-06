from __future__ import annotations

from dataclasses import dataclass
from operator import attrgetter
from typing import Any, Callable, Dict, Mapping, Sequence, Union

from ._repr_utils import ReprJson


@dataclass(frozen=True)
class RetrievalData:
    """Retrieval data."""

    id: int
    retrieval_type: str
    location: str
    filter_id: int
    measures: Sequence[str]
    start_times: Sequence[int]
    elapsed_times: Sequence[int]
    result_size: int
    retrieval_filter: str
    partitioning: str
    measures_provider: str

    @property
    def elapsed_time_per_core(self) -> float:
        """Return the average elapsed time per core."""
        if not self.elapsed_times:
            return 0

        import multiprocessing

        parallelism = min(len(self.elapsed_times), multiprocessing.cpu_count())
        return sum(self.elapsed_times) / parallelism

    def _repr_json_(self) -> ReprJson:
        """JSON representation."""
        if self.retrieval_type == "NoOpPrimitiveAggregatesRetrieval":
            return (
                dict(),
                {"expanded": False, "root": self.title},
            )

        data = dict()
        data["Location"] = self.location
        data["Filter ID"] = self.filter_id
        data["Measures"] = "[" + ", ".join(self.measures) + "]"
        data["Partitioning"] = self.partitioning
        data["Measures provider"] = self.measures_provider
        data["Start time   (in ms)"] = (
            "[" + ", ".join([str(t) for t in self.start_times]) + "]"
        )
        data["Elapsed time (in ms)"] = (
            "[" + ", ".join([str(t) for t in self.elapsed_times]) + "]"
        )
        data["Elapsed time per core (in ms)"] = self.elapsed_time_per_core
        data["Result size"] = self.result_size
        return (data, {"expanded": False, "root": self.title})

    @property
    def title(self) -> str:
        """Title of this retrieval."""
        return f"Retrieval #{self.id}: {self.retrieval_type}"


class QueryPlan:
    """Query plan."""

    def __init__(
        self,
        *,
        infos: Mapping[str, Any],
        retrievals: Sequence[RetrievalData],
        dependencies: Mapping[int, Sequence[int]],
    ):
        """Init."""
        self.retrievals: Mapping[int, RetrievalData] = {
            retr.id: retr for retr in retrievals
        }
        self.infos: Mapping[str, Any] = infos
        self.dependencies: Mapping[int, Sequence[int]] = dependencies

    def _analyze_retrievals(self) -> QueryPlanRetrievalsAnalyzer:
        """Return an object used to analyze this query plan's retrievals."""
        return QueryPlanRetrievalsAnalyzer(
            infos=self.infos,
            retrievals=self.retrievals,
            dependencies=self.dependencies,
            analyzed_retrievals=self.retrievals,
        )

    @staticmethod
    def _enrich_repr_json(
        *,
        retr_id: int,
        retrievals: Mapping[int, RetrievalData],
        dependencies: Mapping[int, Sequence[int]],
    ) -> Dict[str, Any]:
        """Add the dependencies to the JSON of the retrieval."""
        retr = retrievals[retr_id]
        json = retr._repr_json_()
        if retr_id not in dependencies:
            return json[0]  # leaf
        retr_dependencies = {
            retrievals[id].title: QueryPlan._enrich_repr_json(
                retr_id=id, retrievals=retrievals, dependencies=dependencies
            )
            for id in dependencies[retr_id]
        }
        return {**json[0], "Dependencies": retr_dependencies}

    def _repr_json_(self) -> ReprJson:
        """JSON representation."""
        retrievals = {
            retr.title: QueryPlan._enrich_repr_json(
                retr_id=id, retrievals=self.retrievals, dependencies=self.dependencies
            )
            for id, retr in self.retrievals.items()
            if id in self.dependencies[-1]
        }
        data = {
            "Info": self.infos,
            "Retrievals": retrievals,
        }
        return data, {"expanded": True, "root": "QueryPlan"}


class QueryPlanRetrievalsAnalyzer:
    """Analyzer for query plan retrievals."""

    def __init__(
        self,
        *,
        infos: Mapping[str, Any],
        retrievals: Mapping[int, RetrievalData],
        dependencies: Mapping[int, Sequence[int]],
        analyzed_retrievals: Mapping[int, RetrievalData],
    ):
        """Init."""
        self.retrievals = retrievals
        self.infos = infos
        self.dependencies = dependencies
        self.analyzed_retrievals = analyzed_retrievals

    def sort(
        self,
        *,
        key: Callable[[RetrievalData], Any] = attrgetter("elapsed_time_per_core"),
        reverse: bool = False,
    ) -> QueryPlanRetrievalsAnalyzer:
        """Sort the retrievals based on the given attribute.

        Args:
            key: A function of one argument that is used to extract
                a comparison key from each RetrievalData.
            reverse: Whether the result should be sorted in descending order or not.
        """
        return QueryPlanRetrievalsAnalyzer(
            infos=self.infos,
            retrievals=self.retrievals,
            dependencies=self.dependencies,
            analyzed_retrievals={
                retr.id: retr
                for retr in sorted(
                    self.analyzed_retrievals.values(), key=key, reverse=reverse
                )
            },
        )

    def filter(
        self, callback: Callable[[RetrievalData], bool]
    ) -> QueryPlanRetrievalsAnalyzer:
        """Filter the retrievals using the provided callback method."""
        return QueryPlanRetrievalsAnalyzer(
            infos=self.infos,
            retrievals=self.retrievals,
            dependencies=self.dependencies,
            analyzed_retrievals={
                retr.id: retr
                for retr in self.analyzed_retrievals.values()
                if callback(retr)
            },
        )

    def __getitem__(self, key: Union[int, slice]) -> QueryPlanRetrievalsAnalyzer:
        """Return the retrieval with the target key, or a subset of the retrievals.

        Args:
            key: The ID of a retrieval, or a slice of the retrievals.
        """
        slice_idx = key if isinstance(key, slice) else slice(key, key + 1)
        return QueryPlanRetrievalsAnalyzer(
            infos=self.infos,
            retrievals=self.retrievals,
            dependencies=self.dependencies,
            analyzed_retrievals={
                retr.id: retr
                for retr in list(self.analyzed_retrievals.values())[slice_idx]
            },
        )

    def _repr_json_(self) -> ReprJson:
        """JSON representation."""
        retrievals = {
            retr.title: QueryPlan._enrich_repr_json(
                retr_id=id, retrievals=self.retrievals, dependencies=self.dependencies
            )
            for id, retr in self.analyzed_retrievals.items()
        }
        return retrievals, {"expanded": False, "root": "Retrievals"}


@dataclass(frozen=True)
class QueryAnalysis:
    """Query Analysis."""

    query_plans: Sequence[QueryPlan]

    def _repr_json_(self) -> ReprJson:
        data = {
            f"Query plan #{idx}": plan._repr_json_()[0]
            for idx, plan in enumerate(self.query_plans)
        }
        return data, {"expanded": True, "root": "Query analysis"}
