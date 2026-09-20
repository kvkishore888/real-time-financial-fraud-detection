from app.engine import analyze_transaction

def test_normal_transaction_allows():
    r=analyze_transaction({'amount':300,'transactions_last_10m':1,'amount_last_10m':300,'distance_from_home_km':5,'account_age_days':800,'merchant_risk':.05,'hour':14,'new_device':False},{'avg_amount':650})
    assert r.decision=='ALLOW'
    assert r.score < 25

def test_risky_transaction_blocks():
    r=analyze_transaction({'amount':5000,'transactions_last_10m':8,'amount_last_10m':10000,'distance_from_home_km':1200,'account_age_days':5,'merchant_risk':.95,'hour':2,'new_device':True},{'avg_amount':650})
    assert r.decision=='BLOCK'
    assert r.score >= 70
