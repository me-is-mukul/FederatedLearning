# Demo guide (about 10 minutes)

## Before class

1. Make sure MongoDB is running.
2. Terminal: `cd node-red` then `npm start`. Wait for `Connected to broker`, about 20 seconds.
3. Open http://localhost:1880 (flows) and http://localhost:1880/dashboard in two browser tabs.
4. Optional: open your ThingSpeak channel in a third tab.
5. Open both notebooks in VS Code or Jupyter. They already contain their outputs.

Start Node-RED about 5 minutes before you present, so the chart has data and the first hourly diagnoses exist. Meter time starts at midnight, so the first 4 minutes are "night", the right time to show a reversed meter.

## 1. The idea (1 minute)

> "Smart meters send readings every minute. Our system collects them with MQTT and Node-RED, stores them in MongoDB and pushes summaries to ThingSpeak. The interesting part: when a meter looks abnormal, we work out *why*. Is the meter broken, or did the family buy an EV or solar panels? Those need opposite responses."

## 2. Node-RED flows (2 minutes)

Show the four tabs at http://localhost:1880:

1. **Smart meters**: the built-in MQTT broker and the simulator publishing every second.
2. **Ingest, detect, store**: *Check reading* flags bad readings and *Hourly diagnosis* decides between meter fault and genuine change, and both are saved to MongoDB.
3. **ThingSpeak**: a 20-second summary sent over HTTP.
4. **Dashboard**: the widgets.

Point at the node status dots (green: working).

## 3. Live dashboard (3 minutes)

At http://localhost:1880/dashboard:

1. Show the live power chart and the total-load gauge.
2. Pick **MTR-02**, press **Stuck**. The line goes flat and within 10 seconds `stuck` rows appear in *Latest alerts*.
3. Pick **MTR-00**, press **Spikes**. Spikes appear in the chart and the alert table.
4. Pick **MTR-04**, press **Solar**. During daytime meter hours the line dips below zero. Within the next meter hour the diagnosis table says *genuine change: exporting in daylight (solar panels?)*.
5. Show that the stuck meter's diagnosis says *meter fault: reading frozen*. Same "abnormal" behaviour, different cause.
6. Press **Normal** for each meter (or choose *all meters* → **Normal**).

## 4. MongoDB and ThingSpeak (1 minute)

- MongoDB Compass → `gridguard_iot`: show `readings`, `alerts` and `diagnosis` filling up.
- ThingSpeak channel: the same data as cloud charts, with field 7 and field 8 jumping when you broke a meter.

## 5. Notebooks (3 minutes)

- **Notebook 1**, recorded day: scroll through the five panels (reversed meter below zero, flat stuck period, spikes, EV block, solar dip), then the hourly heat map and the diagnosis grid.
- **Notebook 2**, GridGuard federated learning: show the error chart (FedAvg explodes after the attacks, GridGuard keeps improving), the decision grid and the scorecard (97% causes correct, 100% attacks blocked, 0 honest homes excluded).

## Likely questions

| Question | Answer |
|---|---|
| Why a simulator, not real meters? | No real smart meters in the lab. The simulator produces the same MQTT messages a real meter gateway would, so a real meter could replace it without changing the rest of the flow. |
| Why MQTT? | It is light, works over unreliable links, and many sensors can publish to one broker. That is the standard IoT protocol. |
| Why both MongoDB and ThingSpeak? | MongoDB keeps every raw reading for analysis. ThingSpeak is a ready-made cloud dashboard and has a strict rate limit (one update per 15 s), so it only gets 20-second summaries. |
| How is a reversed meter told apart from solar panels? | Solar only exports in daylight. A reversed meter is negative at night too, when solar is impossible. |
| What does federated learning add? | Homes improve a shared AI model without uploading raw data. Notebook 2 shows that without GridGuard's checks, a few bad homes ruin the model. |
