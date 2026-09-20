from dataclasses import dataclass
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
from typing import Dict, Any

FEATURE_WEIGHTS = {
    'amount_anomaly': 0.22,
    'velocity': 0.20,
    'location': 0.16,
    'device': 0.16,
    'account_age': 0.08,
    'merchant_risk': 0.10,
    'night_activity': 0.08,
}

@dataclass
class FraudResult:
    score: float
    decision: str
    risk_level: str
    reasons: list[str]
    signals: Dict[str, float]

def haversine_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2-lat1)
    dl = radians(lon2-lon1)
    a = sin(dp/2)**2 + cos(p1)*cos(p2)*sin(dl/2)**2
    return 2*r*atan2(sqrt(a), sqrt(1-a))

def clamp(x):
    return max(0.0, min(1.0, float(x)))

def analyze_transaction(tx: Dict[str, Any], history: Dict[str, Any] | None = None) -> FraudResult:
    history = history or {}
    amount = float(tx.get('amount', 0))
    avg_amount = max(float(history.get('avg_amount', 500)), 1)
    amount_anomaly = clamp(max(0, amount/avg_amount - 1) / 4)

    velocity_count = int(tx.get('transactions_last_10m', 0))
    velocity_amount = float(tx.get('amount_last_10m', 0))
    velocity = clamp(max(velocity_count/8, velocity_amount/(avg_amount*5)))

    distance = float(tx.get('distance_from_home_km', 0))
    location = clamp(distance / 500)

    new_device = bool(tx.get('new_device', False))
    device_change_days = float(tx.get('device_change_days', 365))
    device = clamp((0.7 if new_device else 0) + (0.3 if device_change_days < 3 else 0))

    account_age_days = max(int(tx.get('account_age_days', 365)), 1)
    account_age = clamp((30-account_age_days)/30)

    merchant_risk = clamp(float(tx.get('merchant_risk', 0.1)))
    hour = int(tx.get('hour', datetime.now().hour))
    night_activity = 1.0 if hour < 5 or hour >= 23 else 0.0

    signals = {
        'amount_anomaly': amount_anomaly,
        'velocity': velocity,
        'location': location,
        'device': device,
        'account_age': account_age,
        'merchant_risk': merchant_risk,
        'night_activity': night_activity,
    }
    raw = sum(signals[k]*FEATURE_WEIGHTS[k] for k in signals)
    score = round(max(0.0, min(100.0, raw * 100)), 1)

    reasons = []
    if amount_anomaly > .45: reasons.append('Transaction amount is far above the account baseline.')
    if velocity > .55: reasons.append('High transaction velocity or burst spending detected.')
    if location > .55: reasons.append('Transaction location is unusually far from the home profile.')
    if device > .5: reasons.append('New or recently changed device fingerprint.')
    if account_age > .5: reasons.append('New account profile increases exposure.')
    if merchant_risk > .6: reasons.append('Merchant category has elevated historical risk.')
    if night_activity and score > 25: reasons.append('Transaction occurred during a low-activity time window.')
    if not reasons: reasons.append('Signals are consistent with the observed account profile.')

    if score >= 70:
        decision, risk = 'BLOCK', 'Critical'
    elif score >= 45:
        decision, risk = 'REVIEW', 'High'
    elif score >= 25:
        decision, risk = 'STEP-UP', 'Medium'
    else:
        decision, risk = 'ALLOW', 'Low'
    return FraudResult(score, decision, risk, reasons, {k: round(v*100,1) for k,v in signals.items()})
