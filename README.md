# FraudShield — Real-Time Financial Fraud Detection Engine

A hackathon-ready prototype for explainable, real-time financial transaction risk scoring.

## Problem
Financial fraud can emerge from combinations of transaction behaviour, account history, device, location and velocity. A transaction that looks legitimate alone can become suspicious when contextual signals are combined.

## Proposed solution
FraudShield evaluates behavioural and contextual signals and maps each transaction to ALLOW, STEP-UP, REVIEW, or BLOCK with an explainable risk score and reasons.

## Features
- Real-time transaction scoring API
- Multi-signal behavioural/contextual risk engine
- Explainable reasons and signal bars
- Velocity, amount anomaly, device, location, merchant and time signals
- Interactive dashboard and risky-demo scenario
- Recent decision history
- Automated tests and CI

## Stack
Python 3.11+, Flask, HTML/CSS/JavaScript, pytest

## Run locally
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python -m app.main
```
Open http://127.0.0.1:5000

## API
- `GET /api/health`
- `POST /api/analyze`

Example request:
```json
{"amount":4800,"transactions_last_10m":7,"amount_last_10m":9200,"distance_from_home_km":850,"account_age_days":12,"merchant_risk":0.82,"hour":1,"new_device":true}
```

The response contains the risk score, action, risk level, reasons and normalized signals.

## Demo
1. Open the dashboard.
2. Click **Load risky demo**.
3. Show the score, decision and reasons.
4. Change amount, device, location or velocity and analyze again.
5. Review the Recent Decisions table.

## Architecture
Browser UI → Flask API → Risk engine → JSON decision → Dashboard. The demo keeps recent events in memory and requires no external database.

## Security and limitations
No credentials are required. Real `.env` files are ignored. For production, replace the deterministic demo scorer with a trained model and add persistent storage, streaming infrastructure, authentication, monitoring, calibration, drift detection and human-review feedback loops.

## Team
Add team member names and contribution areas before final submission.
