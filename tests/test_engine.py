from app.engine import analyze_transaction

def test_normal_transaction_allows():
    r=analyze_transaction({'amount':300,'transactions_last_10m':1,'amount_last_10m':300,'distance_from_home_km':5,'account_age_days':800,'merchant_risk':.05,'hour':14,'new_device':False},{'avg_amount':650})
    assert r.decision=='ALLOW'
    assert r.score<25

def test_risky_transaction_blocks():
    r=analyze_transaction({'amount':5000,'transactions_last_10m':8,'amount_last_10m':10000,'distance_from_home_km':1200,'account_age_days':5,'merchant_risk':.95,'hour':2,'new_device':True,'related_accounts':5,'shared_devices':3,'shared_ips':3,'shared_beneficiaries':4},{'avg_amount':650,'transactions_last_30d':2,'previous_fraud_flags':1,'failed_attempts_30d':1})
    assert r.decision=='BLOCK'; assert r.score>=70

def test_network_relationships_raise_risk():
    base={'amount':650,'transactions_last_10m':1,'amount_last_10m':650,'distance_from_home_km':5,'account_age_days':800,'merchant_risk':.05,'hour':14,'new_device':False}
    normal=analyze_transaction(base|{'related_accounts':0,'shared_devices':0,'shared_ips':0,'shared_beneficiaries':0},{'avg_amount':650})
    linked=analyze_transaction(base|{'related_accounts':5,'shared_devices':3,'shared_ips':3,'shared_beneficiaries':4},{'avg_amount':650})
    assert linked.signals['network_relationship']==100.0; assert linked.score>normal.score

def test_account_history_changes_score():
    tx={'amount':900,'transactions_last_10m':2,'amount_last_10m':900,'distance_from_home_km':10,'account_age_days':400,'merchant_risk':.1,'hour':14,'new_device':False}
    clean=analyze_transaction(tx,{'avg_amount':650,'transactions_last_30d':40,'previous_fraud_flags':0,'failed_attempts_30d':0})
    risky=analyze_transaction(tx,{'avg_amount':650,'transactions_last_30d':2,'previous_fraud_flags':2,'failed_attempts_30d':4})
    assert risky.score>clean.score

def test_ml_signal_exists():
    r=analyze_transaction({'amount':4800,'transactions_last_10m':7,'amount_last_10m':9200,'distance_from_home_km':850,'account_age_days':12,'merchant_risk':.82,'hour':1,'new_device':True},{'avg_amount':650})
    assert 0<=r.signals['ml_anomaly']<=100
