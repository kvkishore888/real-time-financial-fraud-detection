from flask import Flask, jsonify, render_template, request
from datetime import datetime, timezone
from app.engine import analyze_transaction

# templates/ and static/ live at the repository root, while this module is in app/.
# Explicitly configure both folders so the app works correctly on Render and locally.
app = Flask(__name__, template_folder='../templates', static_folder='../static')

DEMO_HISTORY = {'avg_amount': 650}
recent = []

def normalize(payload):
    required = ['amount']
    for field in required:
        if field not in payload:
            raise ValueError(f'Missing required field: {field}')
    return payload

@app.get('/')
def home():
    return render_template('index.html')

@app.get('/api/health')
def health():
    return jsonify({'status':'ok','service':'fraud-engine','timestamp':datetime.now(timezone.utc).isoformat()})

@app.post('/api/analyze')
def analyze():
    try:
        tx = normalize(request.get_json(silent=True) or {})
        result = analyze_transaction(tx, DEMO_HISTORY)
        event = {'id': len(recent)+1, 'timestamp': datetime.now(timezone.utc).isoformat(), **tx,
                 'score': result.score, 'decision': result.decision, 'risk_level': result.risk_level}
        recent.insert(0, event)
        del recent[20:]
        return jsonify({'transaction':event, 'reasons':result.reasons, 'signals':result.signals})
    except (TypeError, ValueError) as e:
        return jsonify({'error':str(e)}), 400

@app.get('/api/events')
def events():
    return jsonify(recent)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
