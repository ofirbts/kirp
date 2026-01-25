import email

def parse_email(raw_data: str):
    msg = email.message_from_string(raw_data)
    sender = msg.get("From", "Unknown")
    subject = msg.get("Subject", "")
    body = msg.get_payload()
    return sender, subject, body
