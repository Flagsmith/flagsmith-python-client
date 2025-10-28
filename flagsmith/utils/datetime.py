import sys

if sys.version_info >= (3, 11):
    from datetime import datetime

    fromisoformat = datetime.fromisoformat
else:
    import iso8601

    fromisoformat = iso8601.parse_date
