_JDBC_PREFIX = "jdbc:"


def normalize_jdbc_url(url: str) -> str:
    if not url.startswith(_JDBC_PREFIX):
        url = f"{_JDBC_PREFIX}{url}"
    return url
