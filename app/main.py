from flask import Flask, jsonify, render_template, request
from datetime import datetime, timezone
from app.engine import analyze_transaction

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# Demo account history. These values represent historical features that would
# normally come from a transaction database/feature store.
DEMO_HISTORY = {
    'avg_amount': 650,
    'account_age_days': 420,
    'transactions_last_30d': 38,
    'previous_fraud_flags': 0,
}

recent = []

def normalize(payload):
    if 'amount' not in payload:
        raise ValueError('Missing required field: amount')
    return payload

@app.get('/')
def home():
    return render_template('index.html')

@app.get('/api/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'fraud-engine',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    })

@app.post('/api/analyze')
def analyze():
    try:
        tx = normalize(request.get_json(silent=True) or {})
        result = analyze_transaction(tx, DEMO_HISTORY)
        event = {
            'id': len(recent) + 1,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            **tx,
            'score': result.score,
            'decision': result.decision,
            'risk_level': result.risk_level,
        }
        recent.insert(0, event)
        del recent[20:]
        return jsonify({
            'transaction': event,
            'reasons': result.reasons,
            'signals': result.signals,
            'account_history': DEMO_HISTORY,
            'network': {
                'related_accounts': int(tx.get('related_accounts', 0)),
                'shared_devices': int(tx.get('shared_devices', 0)),
                'shared_ips': int(tx.get('shared_ips', 0)),
                'shared_beneficiaries': int(tx.get('shared_beneficiaries', 0)),
            },
        })
    except (TypeError, ValueError) as e:
        return jsonify({'error': str(e)}), 400

@app.get('/api/events')
def events():
    return jsonify(recent)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
