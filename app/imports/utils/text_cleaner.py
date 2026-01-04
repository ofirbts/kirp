import re

def clean_text(text: str):
    text = text.strip()
    text = re.sub(r'\s+', ' ', text)
    return text
