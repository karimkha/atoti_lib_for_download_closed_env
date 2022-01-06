from typing import Mapping, TypeVar

from .._repr_utils import ReprJson, ReprJsonable
from ._base_measure import BaseMeasure

_BaseMeasure = TypeVar("_BaseMeasure", bound="BaseMeasure")


class BaseMeasures(Mapping[str, _BaseMeasure], ReprJsonable):
    """Manage the base measures."""

    def _repr_json_(self) -> ReprJson:
        """Return the JSON representation of measures."""
        measures_json = dict()
        no_folder = dict()
        for measure in self.values():
            if measure.visible:
                json = {"formatter": measure.formatter}
                if measure.description is not None:
                    json["description"] = measure.description
                if measure.folder is None:
                    # We store them into another dict to insert them after the folders
                    no_folder[measure.name] = json
                else:
                    folder = f"📁 {measure.folder}"
                    measures_json.setdefault(folder, {})[measure.name] = json
        for folder, measures_in_folder in measures_json.items():
            measures_json[folder] = dict(sorted(measures_in_folder.items()))
        return (
            {**measures_json, **dict(sorted(no_folder.items()))},
            {"expanded": False, "root": "Measures"},
        )
