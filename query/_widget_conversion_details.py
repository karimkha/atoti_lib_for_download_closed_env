from dataclasses import dataclass


@dataclass(frozen=True)
class WidgetConversionDetails:
    mdx: str
    session_id: str
    widget_creation_code: str
