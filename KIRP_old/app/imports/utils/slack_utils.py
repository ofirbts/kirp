def format_slack_message(user: str, text: str, ts: str):
    return f"{user}: {text} ({ts})"
