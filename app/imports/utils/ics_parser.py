def extract_ics_field(text: str, key: str):
    for line in text.splitlines():
        if line.startswith(key):
            return line.split(":", 1)[1]
    return ""
