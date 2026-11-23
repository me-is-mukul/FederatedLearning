# Notebooks

Open them with `jupyter notebook notebooks` (from the activated venv) or directly in VS Code. Both are saved with their outputs, so they can be read without running them.

## 1_iot_data_analysis.ipynb: analysis of what Node-RED stored

Needs MongoDB with at least a few minutes of data from Node-RED. A full day (24 minutes) looks best.

| Section | Graph |
|---|---|
| 1. A full day of readings | one panel per home, with the readings Node-RED flagged shown as red dots |
| 2. Daily load profile | heat map of average power per home and hour (blue = drawing power, red = exporting) |
| 3. Energy per home | kWh for the day. The EV home uses the most, and the reversed meter even shows negative energy. |
| 4. Problems flagged | how many readings got each flag (stuck, spike, reverse) |
| 5. Hourly diagnosis | home × hour grid of normal, genuine change and meter fault, plus the reasons |
| 6. ThingSpeak | the same data read back from the cloud channel (skipped if no channel is set) |

## 2_gridguard_federated_learning.ipynb: the GridGuard experiment

Runs on its own and needs no Node-RED or MongoDB. It takes about a minute.

1. Simulates 8 homes over several days, including the true appliance power.
2. Shows one day as a stacked area chart: what the meter sees versus what each appliance really used.
3. Trains a small neural network (Seq2Point) that estimates appliances from the total.
4. Federated learning: homes train locally and only send model updates.
5. Attacks (sign flip, scaling, tampering in transit), broken meters (stuck, reversed) and real changes (EV, solar) are switched on from round 3.
6. Compares **FedAvg** (plain average) with **GridGuard** (signature check, meter evidence, update evidence, trust scores):
   - error per round (log scale)
   - a grid of every decision GridGuard made
   - the final scorecard
   - trust scores
   - an audit-chain tampering test
