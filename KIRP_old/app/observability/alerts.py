ALERTS = []


def check_confidence(confidence: float):
    if confidence < 0.4:
        ALERTS.append({
            "type": "LOW_CONFIDENCE",
            "value": confidence
        })


def get_alerts():
    return ALERTS
