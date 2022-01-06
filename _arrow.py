import json
from http import HTTPStatus
from typing import Any, Collection, Mapping, cast
from urllib.parse import urljoin
from urllib.request import Request, urlopen

import pandas as pd
import pyarrow as pa

from .query._mdx_utils import parse_level_unique_name
from .query.session import QuerySession

ATOTI_API_VERSION = "1"


def get_raw_query_endpoint(session: QuerySession) -> str:
    return urljoin(
        f"{session.url}/",
        f"atoti/rest/v{ATOTI_API_VERSION}/arrow/query",
    )


def run_raw_arrow_query(
    params: Mapping[str, Any],
    *,
    session: QuerySession,
) -> pa.Table:
    url = get_raw_query_endpoint(session)
    auth = session._auth(url) or {}
    headers = {
        **auth,
        "Content-Type": "application/json",
    }
    req = Request(
        url, method="POST", headers=headers, data=json.dumps(params).encode("utf-8")
    )
    with urlopen(req) as response:  # nosec
        if response.status != HTTPStatus.OK:
            try:
                # Try to get the first error of the chain if it exists.
                error = RuntimeError(
                    f"Query failed: {json.loads(response)['error']['errorChain'][0]}"
                )
            except Exception:  # pylint: disable=broad-except
                error = RuntimeError(response.content)
            raise error
        record_batch_stream = pa.ipc.open_stream(response)
        return pa.Table.from_batches(
            record_batch_stream, schema=record_batch_stream.schema
        )


def arrow_to_pandas(
    table: pa.Table,  # type: ignore
) -> pd.DataFrame:
    return table.to_pandas().rename(
        columns={
            column_name: parse_level_unique_name(column_name)[2]  # type: ignore
            for column_name in cast(Collection[str], table.column_names)
            if parse_level_unique_name(column_name) is not None
        }
    )
