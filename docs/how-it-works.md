# How GridGuard works

Everything below lives in `gridguard.py` unless stated otherwise. The function names are given so you can find each part quickly.

## 1. The homes (simulated smart meters)

`make_household(seed, days)` creates one home, one reading per minute:

- **background** use: lights and standby, higher in the evening
- **fridge**: switches on and off all day, about 100 W
- **kettle**: about 4 times a day, 2.5 kW for a few minutes
- **washing machine**: every other day, a 2 kW heating phase, then washing and spinning

The meter only reports the **total** (`aggregate`). The individual appliance values are the "answers" the AI learns from, like the plug sensors used in public datasets such as UK-DALE.

`add_event(frame, kind, start_day, seed)` changes a home from a given day:

| kind | what happens to the meter reading |
|---|---|
| `stuck` | freezes at one value for 30 to 240 minutes at a time |
| `spike` | random jumps of 5 to 15 kW |
| `reverse` | becomes negative (sensor clamped on backwards) |
| `ev` | +7 kW for 2 to 5 hours on most evenings |
| `solar` | up to 3 kW lower around midday, so it can go negative |

## 2. The AI model (NILM)

NILM means Non-Intrusive Load Monitoring: estimating appliance use from the total alone.

`Seq2Point` is a small neural network. It looks at 59 minutes of total power and predicts the fridge, kettle and washing machine at the middle minute. `windows()` cuts the data into those 59-minute slices, and `error_in_watts()` measures how far off the predictions are (mean absolute error) on two extra homes that never take part in training.

## 3. Federated learning

`Federation.step()` runs one round:

1. Every home gets the current shared model.
2. It trains on its own last two days of data (`train_local`) and keeps the data at home.
3. It sends back only the **update** (how its weights changed), six summary numbers about its meter, and a **digital signature**.
4. The server combines the updates into the next shared model.

Two servers run side by side on exactly the same updates:

- **FedAvg**, the standard method: a plain average, no questions asked.
- **GridGuard**: investigates first, as described below.

Attacks used in the demo (`client_round`):

| attack | what the dishonest home sends |
|---|---|
| sign flip | its real update × −5 (pushes the model backwards) |
| scaling | its real update × 20 (overpowers everyone else) |
| tampering | an honest update that gets changed in transit, after it was signed |

## 4. How GridGuard decides (the main idea)

GridGuard combines three kinds of evidence.

**a) The meter's own numbers** (`meter_evidence`). These are computed inside the home, so only six numbers are shared:

| number | high means |
|---|---|
| `spikes` | sudden isolated jumps, so a broken meter |
| `stuck` | many identical readings in a row, so a broken meter |
| `negative_at_night` | power "exported" at night, which is impossible, so a reversed meter |
| `negative_by_day` | export only in daytime, so solar panels |
| `heavy_load` | more than 5 kW for over an hour, so an EV |
| `usage_change` | the home uses much more or less than it used to |

**b) The update itself** (`update_evidence`):

- `size`: how big the update is compared with the typical home. Scaling attacks are huge.
- `direction`: how similar it is to everyone else's (1 means the same way, negative means the opposite way). Sign-flip attacks point backwards.

**c) Trust** (`update_trust`): three scores per home.

| score | drops when | used for |
|---|---|---|
| integrity | the home attacks (halved each time) | how much its updates count |
| reliability | its meter is faulty | tracking broken meters |
| adaptability | never | grows each time a real change is confirmed |

**The rules** (`find_cause`):

```
meter looks broken                 -> meter_fault     (quarantine)
odd update + real change in home   -> uncertain       (hold back)
odd update, normal home            -> malicious       (reject)
real change, normal update         -> genuine_change  (accept at half weight)
nothing unusual                    -> benign          (accept)
```

The meter is checked first. A broken meter also produces a strange update, and that is the meter's fault, not the family's.

Finally, very large updates are cut down to twice the typical size before averaging, and homes whose integrity has fallen below 0.25 are ignored.

## 5. Signatures and the audit chain

- Each home has its own **Ed25519** key. It signs a message containing its name, the round number, the **SHA-256** fingerprint of its update, and its six meter numbers (`signed_message`).
- The server checks the signature (`signature_ok`). If even one number was changed on the way, the check fails and the update is rejected as `bad_signature`.
- Every decision is added to an **audit chain** (`AuditLog`). Each record stores the fingerprint of the record before it, so editing an old record breaks every fingerprint after it, and `first_broken()` finds the edit. The *Audit chain* tab lets you try this.

## 6. The live IoT pipeline

```
python gridguard.py meters  --MQTT-->  Mosquitto  -->  Node-RED  -->  MongoDB (readings, alerts)
        ^                                                 |
        +---------- MQTT gridguard/control/<meter> <------+---- POST /control (dashboard buttons)
```

- `run_meters()` publishes one reading per meter per second (each second counts as one simulated minute) to `gridguard/meters/<meter>/reading`, and listens for commands like `{"mode": "stuck"}`. Options: `--meters 5`, `--interval 1.0`, and `--start-hour 0` to start the meter clock at midnight. The meters take a few seconds to start because PyTorch loads first.
- **Node-RED** (`node-red/flows.json`, editable at http://localhost:1880):
  - *Check reading* flags `stuck` (10 identical readings), `spike` (a jump of over 4 kW that drops straight back), `reverse` (negative between midnight and 4 am) and `implausible` (over 23 kW).
  - Every reading is saved to MongoDB `gridguard.readings`, and flagged ones also to `gridguard.alerts`.
  - `POST /control` checks a dashboard command and forwards it to the meter over MQTT.
- **MongoDB** runs on your computer. Node-RED, inside Docker, reaches it at `host.docker.internal:27017`. To point it elsewhere, set `MONGO_URI_FOR_DOCKER` before `docker compose up`.

## 7. Saving results

After training, the dashboard has two buttons:

- **Save run to MongoDB** stores the summary, every round, every decision and the audit chain in `gridguard.runs`.
- **Upload run to AWS S3** uploads the same data as one JSON file. You need an S3 bucket, `aws configure` with an IAM user that may upload to it, and `$env:S3_BUCKET = "your-bucket"` set before starting the dashboard.

## Limits (good to mention in the viva)

- The homes are simulated. Real datasets (REDD, UK-DALE, REFIT) would need a loader.
- Slow calibration drift of a meter is not detected; it looks like normal variation.
- The method assumes most homes are honest. If half the homes attack, "typical" stops meaning honest.
- Federated learning is written in plain Python. A framework such as Flower would be the next step for running on real devices like a Raspberry Pi.
