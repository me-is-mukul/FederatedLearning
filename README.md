# GridGuard

**Smart-meter AI that can tell an attacker from a broken meter.**

IoT Analytics Lab mini project, JIIT. Mukul Aggarwal (2401030239) and Shivam Diwaker (2401030245).

Eight homes train one AI model together to work out how much the fridge, kettle and washing machine use, from nothing but the total smart-meter reading. Their raw data never leaves the home; only model updates are shared (*federated learning*).

The trouble is that some updates look wrong, and there are three very different reasons why:

| Reason | Example | What GridGuard does |
|---|---|---|
| Attack | a home sends a reversed or blown-up update on purpose | **rejects** it |
| Broken meter | the meter is stuck, spiking, or wired backwards | **quarantines** it (no blame) |
| Real change | the family bought an EV or installed solar panels | **accepts** it at half weight |

Normal federated learning (FedAvg) treats them all the same and its model falls apart. GridGuard checks the evidence first.

## What's in the folder

| File | What it is |
|---|---|
| `app.py` | the interactive dashboard: start here |
| `gridguard.py` | the engine: simulated homes, AI model, federated training, cause detection, signatures, live meters |
| `node-red/` | Node-RED flow (MQTT to MongoDB with alerts) and its Docker setup |
| `docker-compose.yml` | starts Mosquitto (MQTT broker) and Node-RED |
| `test_gridguard.py` | automatic checks |
| `docs/how-it-works.md` | every idea explained simply |
| `docs/demo-guide.md` | a step-by-step script for the presentation |

## Setup (once)

You need Python 3.11+, Docker Desktop and MongoDB running on your computer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once.

## Run it

```powershell
streamlit run app.py
```

The dashboard opens at http://localhost:8501 with four tabs:

1. **Explore a home**: see what a smart meter records, add a fault or an EV, and watch the evidence change.
2. **Train the federation**: pick what happens in each home, press *Train*, and watch FedAvg and GridGuard learn side by side, live.
3. **Audit chain**: secretly edit a past decision and watch the hash chain catch it.
4. **Live meters**: real MQTT meters going through Node-RED into MongoDB. Break a meter with one click.

For the live tab, open two more terminals (with the venv activated):

```powershell
docker compose up -d --build
python gridguard.py meters --start-hour 0
```

Without the dashboard, `python gridguard.py train` runs the default experiment in the terminal. `pytest` runs the checks.

## Result (default setup, 10 rounds)

| | Model error at the end |
|---|---|
| FedAvg | 120.6 W (and it jumps between 25 and 204 W) |
| **GridGuard** | **20.0 W** |

GridGuard identified the right cause for 96% of updates. It blocked 100% of attacks, quarantined 100% of faulty-meter updates and wrongly excluded 2% of honest updates. The audit chain stayed intact.

## Tech used

Python (NumPy, Pandas, PyTorch), MQTT (Mosquitto, paho-mqtt), Node-RED, MongoDB, cryptography (SHA-256, Ed25519), Streamlit and Altair, Docker, and AWS S3 for saving results.
