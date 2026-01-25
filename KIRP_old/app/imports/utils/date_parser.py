from dateutil import parser

def parse_date(text: str):
    try:
        return parser.parse(text)
    except Exception:
        return None
