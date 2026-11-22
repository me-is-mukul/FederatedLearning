# Demo guide (about 10 minutes)

## Before the demo

1. Start MongoDB (it usually runs as a Windows service already).
2. Terminal 1: `docker compose up -d --build`
3. Terminal 2: `python gridguard.py meters --start-hour 0`. This starts the meters' clock at midnight, so the reversed-meter alert can fire. Each real second is one meter minute, so night lasts about 4 real minutes.
4. Terminal 3: `streamlit run app.py`
5. Training 10 rounds takes about 35 seconds, short enough to do live.

## 1. The problem (1 min)

Show the header of the dashboard.

> "Homes want a shared AI that splits their electricity bill by appliance, without handing over their data. That's federated learning. But when a home sends a weird update, is it an attacker, a broken meter, or did they just buy an EV? Treating all three the same either breaks the model or punishes innocent homes."

## 2. Explore a home (2 min)

Tab **Explore a home**:

- With event *normal*, point out the coloured areas (fridge, kettle, washing machine) and the black total line. "The AI only ever sees the black line."
- Switch the event to *fault: reversed meter*, set the day to 4, and show the reading going negative. The verdict says *meter fault*.
- Switch to *change: EV charger*: a big 7 kW block in the evening, and the verdict says *genuine change*.
- Open the expander: "These six numbers are all the home shares. The raw data stays at home."

## 3. Train the federation (4 min)

Tab **Train the federation**:

- Show the table. Homes 1, 2 and 7 attack, 3 and 4 have broken meters, 5 and 6 bought an EV or solar panels.
- Press **Train** and talk while it runs:
  - the orange line (FedAvg) shoots up once the attacks start at round 3
  - the blue line (GridGuard) keeps going down
  - the grid fills in live: AT attack, FX meter fault, CH real change, SIG bad signature
- At the end, point to the cards: correct causes, attacks blocked, honest homes excluded.
- Hover a square in the grid to compare *really is* with *GridGuard says*.
- Show the trust bars: the attackers' integrity has collapsed, and the faulty meters lost reliability but not integrity.
- Optional: change the table (for example, make home 0 a scaling attacker from round 2) and train again.

## 4. Audit chain (1 min)

Tab **Audit chain**:

- "Every decision is chained with SHA-256 fingerprints."
- Press **Secretly flip its decision**: the block turns red and tampering is detected.
- Press **Undo all edits**: the chain is verified again.

## 5. Live IoT (2 min)

Tab **Live meters**:

- The chart updates every 3 seconds from MongoDB. The readings travelled meter → MQTT → Node-RED → MongoDB.
- Click **Stuck**: after about 10 seconds the line goes flat and a `stuck` alert appears.
- Click **Reversed** within the first 4 minutes: the line flips below zero and `reverse` alerts appear. Node-RED only calls a negative reading "reverse" between midnight and 4 am meter time; in daytime, negative power could just be solar panels.
- Click **Normal** to reset.
- Optional: open http://localhost:1880 and show the Node-RED flow.

## Likely questions

| Question | Answer |
|---|---|
| Why not just reject every odd update? | Homes with broken meters or new EVs are honest. Rejecting them is unfair, and the model would never learn about EVs. |
| Can an attacker fake the six meter numbers? | They are signed, so they can't be changed in transit. A home can lie about its own numbers, but its update still has to look normal, or it gets caught by size and direction. |
| What does the signature prove? | That the update was not changed after the home sent it. It doesn't prove the meter is accurate; that's the job of the meter evidence. |
| Why does GridGuard sometimes have a higher error than FedAvg in a single round? | It ignores the quarantined and rejected homes, so it learns from fewer homes. Over the rounds it stays stable while FedAvg swings wildly. |
| Where is the cloud? | Runs can be saved to MongoDB and uploaded to AWS S3 from the dashboard. Node-RED and the broker could run on an EC2 server the same way they run in Docker here. |
