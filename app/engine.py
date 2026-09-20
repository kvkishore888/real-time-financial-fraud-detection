from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any

FEATURE_WEIGHTS = {
    'amount_anomaly': 0.18,
    'velocity': 0.17,
    'location': 0.13,
    'device': 0.13,
    'account_age': 0.07,
    'merchant_risk': 0.08,
    'night_activity': 0.07,
    'network_relationship': 0.17,
}

@dataclass
class FraudResult:
    score: float
    decision: str
    risk_level: str
    reasons: list[str]
    signals: Dict[str, float]

def clamp(x):
    return max(0.0, min(1.0, float(x)))

def analyze_transaction(tx: Dict[str, Any], history: Dict[str, Any] | None = None) -> FraudResult:
    history = history or {}
    amount = float(tx.get('amount', 0))
    avg_amount = max(float(history.get('avg_amount', 500)), 1)
    amount_anomaly = clamp(max(0, amount / avg_amount - 1) / 4)

    velocity_count = int(tx.get('transactions_last_10m', 0))
    velocity_amount = float(tx.get('amount_last_10m', 0))
    velocity = clamp(max(velocity_count / 8, velocity_amount / (avg_amount * 5)))

    distance = float(tx.get('distance_from_home_km', 0))
    location = clamp(distance / 500)

    new_device = bool(tx.get('new_device', False))
    device_change_days = float(tx.get('device_change_days', 365))
    device = clamp((0.7 if new_device else 0) + (0.3 if device_change_days < 3 else 0))

    account_age_days = max(int(tx.get('account_age_days', history.get('account_age_days', 365))), 1)
    account_age = clamp((30 - account_age_days) / 30)

    merchant_risk = clamp(float(tx.get('merchant_risk', 0.1)))
    hour = int(tx.get('hour', datetime.now().hour))
    night_activity = 1.0 if hour < 5 or hour >= 23 else 0.0

    # Lightweight relationship graph for the hackathon MVP.
    # In production this can be backed by a graph database or feature store.
    related_accounts = int(tx.get('related_accounts', 0))
    shared_devices = int(tx.get('shared_devices', 0))
    shared_ips = int(tx.get('shared_ips', 0))
    shared_beneficiaries = int(tx.get('shared_beneficiaries', 0))
    network_relationship = clamp(
        max(
            related_accounts / 5,
            shared_devices / 3,
            shared_ips / 3,
            shared_beneficiaries / 4,
        )
    )

    signals = {
        'amount_anomaly': amount_anomaly,
        'velocity': velocity,
        'location': location,
        'device': device,
        'account_age': account_age,
        'merchant_risk': merchant_risk,
        'night_activity': night_activity,
        'network_relationship': network_relationship,
    }
    raw = sum(signals[k] * FEATURE_WEIGHTS[k] for k in signals)
    score = round(max(0.0, min(100.0, raw * 100)), 1)

    reasons = []
    if amount_anomaly > .45:
        reasons.append('Transaction amount is far above the account baseline.')
    if velocity > .55:
        reasons.append('High transaction velocity or burst spending detected.')
    if location > .55:
        reasons.append('Transaction location is unusually far from the home profile.')
    if device > .5:
        reasons.append('New or recently changed device fingerprint.')
    if account_age > .5:
        reasons.append('New account profile increases exposure.')
    if merchant_risk > .6:
        reasons.append('Merchant category has elevated historical risk.')
    if night_activity and score > 25:
        reasons.append('Transaction occurred during a low-activity time window.')
    if network_relationship > .4:
        reasons.append(
            f'Network link analysis found {related_accounts} related accounts, '
            f'{shared_devices} shared devices, {shared_ips} shared IPs, and '
            f'{shared_beneficiaries} shared beneficiaries.'
        )
    if not reasons:
        reasons.append('Signals are consistent with the observed account profile.')

    if score >= 70:
        decision, risk = 'BLOCK', 'Critical'
    elif score >= 45:
        decision, risk = 'REVIEW', 'High'
    elif score >= 25:
        decision, risk = 'STEP-UP', 'Medium'
    else:
        decision, risk = 'ALLOW', 'Low'

    return FraudResult(
        score,
        decision,
        risk,
        reasons,
        {k: round(v * 100, 1) for k, v in signals.items()},
    )
