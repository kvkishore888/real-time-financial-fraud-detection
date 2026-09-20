from flask import Flask, jsonify, render_template, request
from datetime import datetime, timezone
import csv
import io
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

@app.post('/api/analyze-dataset')
def analyze_dataset():
    uploaded = request.files.get('file')
    if not uploaded or not uploaded.filename:
        return jsonify({'error': 'Please upload a CSV dataset.'}), 400
    if not uploaded.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only CSV files are supported.'}), 400
    try:
        text = uploaded.read().decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(text))
        if not reader.fieldnames or 'amount' not in reader.fieldnames:
            raise ValueError('CSV must contain an amount column.')
        results = []
        counts = {'ALLOW': 0, 'STEP-UP': 0, 'REVIEW': 0, 'BLOCK': 0}
        for index, row in enumerate(reader):
            if index >= 1000:
                break
            tx = {k: v for k, v in row.items() if v not in (None, '')}
            if 'new_device' in tx:
                tx['new_device'] = str(tx['new_device']).strip().lower() in ('true', '1', 'yes', 'y')
            result = analyze_transaction(tx, DEMO_HISTORY)
            counts[result.decision] += 1
            results.append({
                'row': index + 2,
                'amount': float(tx.get('amount', 0)),
                'score': result.score,
                'decision': result.decision,
                'risk_level': result.risk_level,
                'reasons': result.reasons,
            })
        return jsonify({'filename': uploaded.filename, 'rows_processed': len(results), 'summary': counts, 'results': results})
    except UnicodeDecodeError:
        return jsonify({'error': 'CSV must be UTF-8 encoded.'}), 400
    except (TypeError, ValueError) as e:
        return jsonify({'error': f'Invalid dataset: {e}'}), 400

@app.get('/api/events')
def events():
    return jsonify(recent)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
