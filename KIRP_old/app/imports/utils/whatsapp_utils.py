import re

WHATSAPP_PATTERN = re.compile(r'^(\d{1,2}/\d{1,2}/\d{4}), (\d{1,2}:\d{2}) - (.*?): (.*)$')

def parse_whatsapp_line(line: str):
    match = WHATSAPP_PATTERN.match(line)
    if match:
        date, time, sender, message = match.groups()
        return sender, message, f"{date} {time}"
    return None
