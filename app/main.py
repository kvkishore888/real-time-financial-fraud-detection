from flask import Flask,jsonify,render_template,request
from datetime import datetime,timezone
import csv,io,sqlite3
from app.engine import analyze_transaction

app=Flask(__name__,template_folder='../templates',static_folder='../static')
DB_PATH='fraudshield.db'
DEMO_HISTORY={'avg_amount':650,'account_age_days':420,'transactions_last_30d':38,'previous_fraud_flags':0,'failed_attempts_30d':0}

def db():
    conn=sqlite3.connect(DB_PATH); conn.row_factory=sqlite3.Row; return conn

def init_db():
    with db() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,timestamp TEXT NOT NULL,account_id TEXT NOT NULL,
            amount REAL NOT NULL,device_id TEXT,ip_address TEXT,beneficiary_id TEXT,
            score REAL NOT NULL,decision TEXT NOT NULL,risk_level TEXT NOT NULL,payload TEXT NOT NULL)""")
init_db()

def account_history(account_id):
    with db() as conn:
        rows=conn.execute('SELECT amount,decision FROM transactions WHERE account_id=? ORDER BY id DESC LIMIT 100',(account_id,)).fetchall()
    if not rows:return dict(DEMO_HISTORY)
    amounts=[float(r['amount']) for r in rows]
    return {'avg_amount':round(sum(amounts)/len(amounts),2),'account_age_days':420,'transactions_last_30d':len(rows),'previous_fraud_flags':sum(r['decision'] in ('REVIEW','BLOCK') for r in rows),'failed_attempts_30d':sum(r['decision']=='BLOCK' for r in rows)}

def network_evidence(tx):
    account_id=str(tx.get('account_id','demo-user')); device=str(tx.get('device_id','')); ip=str(tx.get('ip_address','')); beneficiary=str(tx.get('beneficiary_id',''))
    values=[]; clauses=[]
    for field,value in [('device_id',device),('ip_address',ip),('beneficiary_id',beneficiary)]:
        if value: clauses.append(f'{field}=?'); values.append(value)
    with db() as conn:
        related=conn.execute('SELECT DISTINCT account_id FROM transactions WHERE account_id<>? AND ('+' OR '.join(clauses)+')',[account_id,*values]).fetchall() if clauses else []
        shared_devices=conn.execute('SELECT COUNT(DISTINCT account_id) FROM transactions WHERE device_id=? AND account_id<>?',(device,account_id)).fetchone()[0] if device else 0
        shared_ips=conn.execute('SELECT COUNT(DISTINCT account_id) FROM transactions WHERE ip_address=? AND account_id<>?',(ip,account_id)).fetchone()[0] if ip else 0
        shared_beneficiaries=conn.execute('SELECT COUNT(DISTINCT account_id) FROM transactions WHERE beneficiary_id=? AND account_id<>?',(beneficiary,account_id)).fetchone()[0] if beneficiary else 0
    return {'related_accounts':len(related),'shared_devices':shared_devices,'shared_ips':shared_ips,'shared_beneficiaries':shared_beneficiaries}

def normalize(payload):
    if 'amount' not in payload: raise ValueError('Missing required field: amount')
    payload=dict(payload); payload.setdefault('account_id','demo-user'); payload.setdefault('device_id','demo-device'); payload.setdefault('ip_address','demo-ip'); payload.setdefault('beneficiary_id','demo-beneficiary'); return payload

@app.get('/')
def home(): return render_template('index.html')

@app.get('/api/health')
def health(): return jsonify({'status':'ok','service':'fraud-engine','timestamp':datetime.now(timezone.utc).isoformat()})

@app.post('/api/analyze')
def analyze():
    try:
        tx=normalize(request.get_json(silent=True) or {}); history=account_history(tx['account_id']); network=network_evidence(tx); tx.update(network); result=analyze_transaction(tx,history); now=datetime.now(timezone.utc).isoformat()
        with db() as conn:
            conn.execute('INSERT INTO transactions(timestamp,account_id,amount,device_id,ip_address,beneficiary_id,score,decision,risk_level,payload) VALUES(?,?,?,?,?,?,?,?,?,?)',(now,tx['account_id'],float(tx['amount']),tx['device_id'],tx['ip_address'],tx['beneficiary_id'],result.score,result.decision,result.risk_level,str(tx)))
        return jsonify({'transaction':{'timestamp':now,**tx,'score':result.score,'decision':result.decision,'risk_level':result.risk_level},'reasons':result.reasons,'signals':result.signals,'account_history':history,'network':network})
    except (TypeError,ValueError) as e:return jsonify({'error':str(e)}),400

@app.post('/api/analyze-dataset')
def analyze_dataset():
    uploaded=request.files.get('file')
    if not uploaded or not uploaded.filename:return jsonify({'error':'Please upload a CSV dataset.'}),400
    if not uploaded.filename.lower().endswith('.csv'):return jsonify({'error':'Only CSV files are supported.'}),400
    try:
        reader=csv.DictReader(io.StringIO(uploaded.read().decode('utf-8-sig')))
        if not reader.fieldnames or 'amount' not in reader.fieldnames:raise ValueError('CSV must contain an amount column.')
        results=[]; counts={'ALLOW':0,'STEP-UP':0,'REVIEW':0,'BLOCK':0}
        for index,row in enumerate(reader):
            if index>=1000:break
            tx={k:v for k,v in row.items() if v not in (None,'')}
            if 'new_device' in tx:tx['new_device']=str(tx['new_device']).strip().lower() in ('true','1','yes','y')
            tx=normalize(tx); history=account_history(tx['account_id']); network=network_evidence(tx); tx.update(network); result=analyze_transaction(tx,history); counts[result.decision]+=1
            results.append({'row':index+2,'amount':float(tx.get('amount',0)),'score':result.score,'decision':result.decision,'risk_level':result.risk_level,'reasons':result.reasons,'ml_anomaly':result.signals['ml_anomaly']})
        return jsonify({'filename':uploaded.filename,'rows_processed':len(results),'summary':counts,'results':results})
    except UnicodeDecodeError:return jsonify({'error':'CSV must be UTF-8 encoded.'}),400
    except (TypeError,ValueError) as e:return jsonify({'error':f'Invalid dataset: {e}'}),400

@app.get('/api/events')
def events():
    with db() as conn: rows=conn.execute('SELECT * FROM transactions ORDER BY id DESC LIMIT 20').fetchall()
    return jsonify([dict(r) for r in rows])

if __name__=='__main__':app.run(host='0.0.0.0',port=5000,debug=False)
