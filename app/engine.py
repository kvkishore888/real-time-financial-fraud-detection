from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any
import numpy as np
from sklearn.ensemble import IsolationForest

FEATURE_WEIGHTS = {'amount_anomaly':.15,'velocity':.14,'location':.10,'device':.10,'account_age':.06,'account_history':.10,'merchant_risk':.07,'night_activity':.05,'network_relationship':.13,'ml_anomaly':.10}

@dataclass
class FraudResult:
    score: float
    decision: str
    risk_level: str
    reasons: list[str]
    signals: Dict[str, float]

def clamp(x): return max(0.0,min(1.0,float(x)))

def _build_model():
    rng=np.random.default_rng(42)
    normal=np.column_stack([
        rng.lognormal(6.1,.45,1200),rng.poisson(1.1,1200),rng.lognormal(5.8,.55,1200),
        rng.gamma(2.0,12.0,1200),rng.integers(60,1500,1200),rng.beta(2,18,1200),
        rng.integers(6,23,1200),rng.binomial(1,.08,1200)])
    model=IsolationForest(n_estimators=120,contamination=.04,random_state=42)
    model.fit(normal)
    return model

ANOMALY_MODEL=_build_model()

def analyze_transaction(tx: Dict[str,Any], history: Dict[str,Any]|None=None)->FraudResult:
    history=history or {}
    amount=float(tx.get('amount',0)); avg_amount=max(float(history.get('avg_amount',500)),1)
    amount_anomaly=clamp(max(0,amount/avg_amount-1)/4)
    velocity_count=int(tx.get('transactions_last_10m',0)); velocity_amount=float(tx.get('amount_last_10m',0))
    velocity=clamp(max(velocity_count/8,velocity_amount/(avg_amount*5)))
    location=clamp(float(tx.get('distance_from_home_km',0))/500)
    new_device=bool(tx.get('new_device',False)); device_change_days=float(tx.get('device_change_days',365))
    device=clamp((.7 if new_device else 0)+(.3 if device_change_days<3 else 0))
    account_age_days=max(int(tx.get('account_age_days',history.get('account_age_days',365))),1)
    account_age=clamp((30-account_age_days)/30)
    transactions_30d=int(history.get('transactions_last_30d',0)); previous_flags=int(history.get('previous_fraud_flags',0)); failed_attempts=int(history.get('failed_attempts_30d',0))
    account_history=clamp((max(0,10-transactions_30d)/10)*.35+clamp(previous_flags/3)*.40+clamp(failed_attempts/5)*.25)
    merchant_risk=clamp(float(tx.get('merchant_risk',.1))); hour=int(tx.get('hour',datetime.now().hour))
    night_activity=1.0 if hour<5 or hour>=23 else 0.0
    related_accounts=int(tx.get('related_accounts',0)); shared_devices=int(tx.get('shared_devices',0)); shared_ips=int(tx.get('shared_ips',0)); shared_beneficiaries=int(tx.get('shared_beneficiaries',0))
    network_relationship=clamp(max(related_accounts/5,shared_devices/3,shared_ips/3,shared_beneficiaries/4))
    row=np.array([[amount,velocity_count,velocity_amount,float(tx.get('distance_from_home_km',0)),account_age_days,merchant_risk,hour,int(new_device)]],dtype=float)
    ml_score=clamp((1-float(ANOMALY_MODEL.decision_function(row)[0]))/2)
    signals={'amount_anomaly':amount_anomaly,'velocity':velocity,'location':location,'device':device,'account_age':account_age,'account_history':account_history,'merchant_risk':merchant_risk,'night_activity':night_activity,'network_relationship':network_relationship,'ml_anomaly':ml_score}
    raw=sum(signals[k]*FEATURE_WEIGHTS[k] for k in signals); score=round(max(0,min(100,raw*100)),1)
    reasons=[]
    if amount_anomaly>.45: reasons.append('Transaction amount is far above the account baseline.')
    if velocity>.55: reasons.append('High transaction velocity or burst spending detected.')
    if location>.55: reasons.append('Transaction location is unusually far from the home profile.')
    if device>.5: reasons.append('New or recently changed device fingerprint.')
    if account_age>.5: reasons.append('New account profile increases exposure.')
    if account_history>.45: reasons.append('Account history shows elevated prior-risk or failed-attempt signals.')
    if merchant_risk>.6: reasons.append('Merchant category has elevated historical risk.')
    if night_activity and score>25: reasons.append('Transaction occurred during a low-activity time window.')
    if network_relationship>.4: reasons.append(f'Network analysis found {related_accounts} related accounts, {shared_devices} shared devices, {shared_ips} shared IPs, and {shared_beneficiaries} shared beneficiaries.')
    if ml_score>.65: reasons.append('ML anomaly model identifies this transaction as unusual versus the learned baseline.')
    if not reasons: reasons.append('Signals are consistent with the observed account profile.')
    if score>=70: decision,risk='BLOCK','Critical'
    elif score>=45: decision,risk='REVIEW','High'
    elif score>=25: decision,risk='STEP-UP','Medium'
    else: decision,risk='ALLOW','Low'
    return FraudResult(score,decision,risk,reasons,{k:round(v*100,1) for k,v in signals.items()})
