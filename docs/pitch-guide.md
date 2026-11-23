# GridGuard: pitch guide (teacher ke saamne kaise present karna hai)

Ye file do kaam karti hai:

1. **Presentation ka script**: kya bolna hai, kya dikhana hai, kis order mein.
2. **Concepts ki deep explanation**: MQTT, Node-RED, MongoDB, ThingSpeak, NILM, federated learning, attacks, signatures, hash chain. Viva mein teacher kuch bhi pooche, yahan se answer mil jaana chahiye.

Teacher ke saamne bolne wali lines English mein di hain (`>` wale blocks). Baaki explanation Hinglish mein hai, taaki khud samajh sako.

---

## 0. Ek line mein project

> "GridGuard is an IoT analytics system for smart meters. It collects meter readings through MQTT and Node-RED, stores them in MongoDB, sends summaries to ThingSpeak, and, most importantly, when a meter looks abnormal, it works out *why*: is the meter broken, or did the family genuinely change, like installing solar panels or buying an EV? We then apply the same idea to federated learning, where it protects a shared AI model from attackers without punishing honest homes."

Ye line yaad kar lo. Har jawab isi idea se juda hai: **"abnormal" ke teen alag cause hote hain, aur teeno ka response alag hona chahiye.**

| Cause | Example | Sahi response |
|---|---|---|
| Meter fault | meter atak gaya (stuck), ulta laga hai (reversed), spikes de raha hai | meter repair karo, family ko blame mat karo |
| Genuine change | solar panel lag gaye, EV charger aa gaya | accept karo, naya pattern seekho |
| Attack | koi jaan-boojh ke galat data / galat model update bhej raha hai | reject karo, trust kam karo |

Normal systems teeno ko "anomaly" bol ke ek jaisa treat karte hain. Yahi gap hum fill kar rahe hain.

---

## 1. Presentation ka flow (10–12 minute)

### Pehle se ready rakho (class se 5–10 min pehle)

1. MongoDB service chal rahi ho (Windows services mein `MongoDB`).
2. Terminal mein `cd node-red`, phir `npm start`. Log mein `Connected to broker` aane tak ruko (lagbhag 20 sec).
3. Browser tabs kholo:
   - `http://localhost:1880` (flows)
   - `http://localhost:1880/dashboard` (dashboard)
   - ThingSpeak channel (agar key daal di hai)
   - MongoDB Compass (`gridguard_iot` database)
4. VS Code mein dono notebooks khol ke rakho. Output already saved hai, run karne ki zarurat nahi.
5. Node-RED ko kam se kam 5 min pehle start karo, taaki chart mein data ho aur pehle hourly diagnosis aa chuke hon.

Meter ka clock midnight se start hota hai. 1 real second = 1 meter minute, to pehle ~6 minute "raat" hai. Reversed meter dikhane ka best time yahi hai.

### Step 1: Problem (1 min)

> "Smart meters only report the total power of a house. When a reading looks strange, there are three possible reasons: the meter is faulty, the family has genuinely changed their usage, for example solar panels or an EV, or someone is attacking the system. These need opposite responses, but normal systems treat them all as the same anomaly. GridGuard tells them apart."

### Step 2: Architecture (1.5 min)

README wala architecture diagram (`docs/images/architecture.png`) dikhao, ya report ka Figure 2.1.

> "Five simulated smart meters publish a reading every second over MQTT to a broker running inside Node-RED. Node-RED checks every reading, diagnoses each meter every hour, stores everything in MongoDB, uploads a 20-second summary to ThingSpeak, and shows a live dashboard. Jupyter notebooks then analyse the stored data and run the federated-learning experiment."

IoT layers bolne ka tareeka (teacher ko ye sunna accha lagta hai):

| Layer | Hamare project mein |
|---|---|
| Device / perception | 5 simulated smart meters |
| Network | MQTT (Aedes broker, port 1883) |
| Edge processing | Node-RED function nodes (Check reading, Hourly diagnosis) |
| Storage | MongoDB |
| Cloud | ThingSpeak |
| Application | Node-RED Dashboard + Jupyter notebooks |

### Step 3: Node-RED flows (2 min)

`http://localhost:1880` pe chaaro tabs dikhao:

1. **Smart meters**: broker node, "Every second" inject → "Simulate 5 meters" → "Publish reading". Neeche "Control commands" jo mode change karta hai.
2. **Ingest, detect, store**: "Meter readings" (MQTT in) → "Check reading" → MongoDB + "Hourly diagnosis" → MongoDB. Alerts alag output se jaate hain.
3. **ThingSpeak**: 20 second window → HTTP GET → response check.
4. **Dashboard**: widgets.

Node ke neeche green dot (status) dikhao: "connected", meter time, "s=6125" (MongoDB mein kitne documents save hue).

> "Each box is a node, and messages flow along the wires. The function nodes contain our analytics logic in JavaScript. Node-RED is event-driven: every MQTT message triggers the flow."

### Step 4: Live demo, dashboard (3 min)

Ye sabse important part hai. Teacher ko khud button dabane do.

1. Live chart aur total-load gauge dikhao.
2. **MTR-02 → Stuck**: line flat ho jayegi, ~10 sec mein alert table mein `stuck` aayega.
3. **MTR-00 → Spikes**: chart mein spikes, alert table mein `spike`.
4. **MTR-01 → Reversed** (raat ke time pe): line zero ke neeche, `reverse` alert, diagnosis "meter fault: negative power with no sun".
5. **MTR-04 → Solar** (din ke time, 06:30 ke baad): line negative hogi, par diagnosis "**genuine change**: exporting in daylight (solar panels?)".
6. **MTR-03 → EV charger** (19:00–23:00): +7 kW, diagnosis "genuine change: EV charging".

Phir punch line bolo:

> "Look: the reversed meter and the solar home both show negative power, but one is diagnosed as a meter fault and the other as a genuine change. The difference is the night. Solar panels can't export when the sun is down, but a reversed meter stays negative day and night."

End mein **all meters → Normal**.

### Step 5: MongoDB + ThingSpeak (1 min)

- Compass mein `gridguard_iot`: `readings`, `alerts` aur `diagnosis` collections, ek document khol ke dikhao (flags array, reason field).
- ThingSpeak: field 6 (total load) ka chart, aur field 7/8 jo meter break karne pe jump karte hain.

> "MongoDB keeps every raw reading for analysis; ThingSpeak is the cloud view, with 20-second summaries because the free plan allows one update every 15 seconds."

### Step 6: Notebooks (3 min)

**Notebook 1** (recorded day):
1. Paanch panels: reversed (neeche), stuck (flat red), spikes (red dots), EV block (shaam), solar dip (dopahar).
2. Heat map: reversed meter poora din red, solar sirf din mein red.
3. Energy bars: EV 34.8 kWh, solar −16.2 kWh, reversed −4.8 kWh. Kisi normal ghar ki negative energy impossible hai, ye wiring fault ka strong sign hai.
4. Diagnosis grid: FAULT vs CH.

**Notebook 2** (federated learning): section 3 mein iski poori theory hai.
1. Error graph: FedAvg 316 W tak phat jaata hai, GridGuard 23.4 W pe khatam.
2. Decision grid: AT, FX, CH, SIG, OK.
3. Scorecard: 97% causes correct, 100% attacks blocked, 0% honest homes excluded.
4. Audit chain demo: record 17 edit kiya, check ne pakad liya.

### Step 7: Close (30 sec)

> "So GridGuard does three things: it monitors meters in real time with Node-RED, MongoDB and ThingSpeak; it explains *why* a meter looks abnormal instead of just raising an alarm; and it uses the same evidence to protect federated learning, blocking attackers while still learning from homes that genuinely changed."

---

## 2. IoT part: deep concepts

### 2.1 Smart meter aur hamara simulator

Real smart meter har kuch second/minute mein total power (watts) aur voltage bhejta hai. Hamare paas real meter nahi the, isliye **"Simulate 5 meters"** function node banaya. Har home ka load in cheezon se banta hai:

| Cheez | Model |
|---|---|
| Standby (fan, router, etc.) | 50 + 25·i watt, din mein ±5% variation |
| Subah ka load | 06:30–08:30, extra 60 + 20·i W |
| Shaam ka load | 17:30–23:00, extra 120 + 40·i W |
| Fridge | 85–125 W, 15–22 min ON, 30–45 min OFF (compressor cycle) |
| Kettle | 2500 W, 3 min, subah/shaam random |
| Washing machine | 65 min cycle: 2000 W heating, 220 W wash, 500 W spin |
| Noise | ±2 W; voltage 230 ± 2 V |

(i = home number 0 to 4, isliye har ghar thoda alag hai.)

**Time trick:** "Every second" inject node har second simulator chalata hai, aur har tick = 1 meter minute. Poora din = 1440 ticks = 24 real minutes. Isliye demo mein raat aur din dono dikh jaate hain.

**Modes** (dashboard buttons ya MQTT se badalte hain):

| Mode | Kya hota hai | Type |
|---|---|---|
| stuck | value freeze ho jaati hai | fault |
| spike | 5% readings mein +5 se 15 kW ka jump | fault |
| reverse | sign ulta (meter backwards laga) | fault |
| ev | 19:00–23:00 +7 kW | genuine |
| solar | din mein −3 kW tak (sine curve, peak 12:30) | genuine |

> Q: "Simulator kyun, real data kyun nahi?"
> "We have no real smart meters in the lab. The simulator publishes exactly the same MQTT messages a real meter gateway would, so a real meter could replace it without changing anything else in the flow."

### 2.2 MQTT: deep

**MQTT kya hai:** ek lightweight **publish/subscribe** messaging protocol, IoT ka standard. TCP ke upar chalta hai, port 1883.

- **Publisher** (meter) message bhejta hai ek **topic** pe, jaise `gridguard/meters/MTR-01/reading`.
- **Broker** (beech ka post office) message leta hai aur un sabko deta hai jinhone us topic ko **subscribe** kiya hai.
- **Subscriber** (Node-RED ka "Meter readings" node) ko pata bhi nahi hota ki message kis device ne bheja. Isko **decoupling** kehte hain: publisher aur subscriber ek doosre ko nahi jaante.

**HTTP se better kyun?**
- HTTP request/response hai: client ko baar-baar poochna padta hai. MQTT mein broker khud push karta hai.
- Header chhota hota hai (2 bytes minimum), to kam bandwidth aur kam battery lagti hai.
- Ek connection open rehta hai, har message pe naya connection nahi banta.
- Bahut saare sensors ek broker pe publish kar sakte hain.

**Topic wildcards:**
- `+` matlab ek level: `gridguard/meters/+/reading` saare meters ki readings deta hai.
- `#` matlab baaki sab levels: `gridguard/#` sab kuch.

**QoS (Quality of Service):**

| QoS | Matlab | Hamare project mein |
|---|---|---|
| 0 | at most once: bhej diya, confirmation nahi | readings: har second nayi aati hai, ek gayi to farak nahi |
| 1 | at least once: jab tak ACK na aaye, dobara bhejo (duplicate ho sakta hai) | control commands aur alerts: ye miss nahi hone chahiye |
| 2 | exactly once: 4-step handshake, sabse slow | use nahi kiya |

**Broker:** Mosquitto alag install karna padta, isliye humne **Aedes** use kiya, jo Node-RED ke andar hi chalta hai (`node-red-contrib-aedes`, port 1883). Ek install, sab kuch ready.

**Hamare topics:**

| Topic | Direction | Content |
|---|---|---|
| `gridguard/meters/<id>/reading` | meter → Node-RED | reading JSON |
| `gridguard/control/<id>` or `/all` | koi bhi client → simulator | `{"mode": "stuck"}` |
| `gridguard/alerts` | Node-RED → koi bhi subscriber | flagged reading |

Ek reading ka message:
```json
{"meter_id": "MTR-01", "household_id": "house-01", "session": "2026-11-22T20:13:48.295Z",
 "ts": "2026-11-22T00:20:00.000Z", "power_w": -170.9, "voltage_v": 228.6}
```

### 2.3 Node-RED: deep

**Node-RED** IBM ka banaya, ab OpenJS Foundation ka, **flow-based programming** tool hai. Browser mein boxes (nodes) ko wires se jodte ho. Node.js pe chalta hai.

Important concepts:

- **msg object:** nodes ke beech jo cheez travel karti hai woh ek JavaScript object hai (`msg`). Main data `msg.payload` mein hota hai, aur `msg.topic` mein MQTT topic.
- **Node types jo humne use kiye:**
  - `inject`: timer
  - `function`: custom JavaScript
  - `mqtt in` / `mqtt out`
  - `mongodb4`: database write
  - `http request`
  - `link in` / `link out`: ek tab se doosre tab mein message bhejna
  - `change`
  - `debug`
  - Dashboard ke `ui-*` nodes
- **Config nodes:** ek "Built-in broker" config ko 3 MQTT nodes share karte hain, aur ek MongoDB client config ko 3 database nodes. Setting ek jagah, use teen jagah.
- **Context (memory):** function node apni state yaad rakh sakta hai:
  - `context`: sirf us node ki private memory. "Check reading" har meter ka `{before, pending, repeats}` yahan rakhta hai.
  - `flow`: ek tab ke saare nodes share karte hain. ThingSpeak ka 20 s window yahan hai.
  - `global`: saare tabs share karte hain. Meter modes, meter time (`simTime`) aur latest diagnosis yahan hain.
- **Multiple outputs:** "Check reading" ke 2 outputs hain. Output 1 pe har reading jaati hai, output 2 pe sirf alerts. `return [msg1, msg2]`; agar alert nahi hai to doosra `null`.
- **Status:** `node.status({fill:"green", text:"..."})` se node ke neeche dot aur text dikhta hai, live debugging ke liye.
- **Deploy:** editor mein change karke Deploy dabao, to `flows.json` mein save ho jaata hai. Poora project isi ek file mein hai.

> Q: "Why Node-RED and not just Python?"
> "Node-RED is built for IoT: MQTT, databases, HTTP and dashboards are ready-made nodes, the flow is visual so anyone can follow the data path, and it is event-driven, so each reading is processed the moment it arrives. Python is only used for offline analysis in the notebooks."

### 2.4 Real-time detection: "Check reading" (edge analytics, level 1)

Har reading pe 4 rules chalte hain:

| Flag | Rule | Logic kyun |
|---|---|---|
| `stuck` | lagatar 10 same values | real readings hamesha thoda hilti hain (fridge, noise). 10 minute bilkul same matlab meter atak gaya |
| `spike` | reading dono padosiyon (pichli aur agli) se 4 kW se zyada upar | koi appliance 1 minute mein ON aur OFF nahi hota. Kettle 3 min chalti hai aur 2.5 kW hai, isliye flag nahi hoti |
| `reverse` | 00:00–04:00 ke beech −20 W se kam | raat ko solar export kar hi nahi sakta, to negative matlab meter ulta laga hai |
| `implausible` | 23 kW se zyada | ghar ka supply itna de hi nahi sakta |

**Hold-back trick (important, teacher pooch sakta hai):** spike check karne ke liye *agli* reading bhi chahiye. Isliye har reading ek step rok ke rakhte hain (`pending`). Jab agli aati hai, tab pichli ko dono padosiyon se compare karke check karte hain. Cost: sirf 1 second ki delay. Pehle bina iske spike ka flag galat reading (spike ke baad wali) pe lagta tha; humne ye bug fix kiya.

Valid na ho (meter_id, ts ya numeric power missing), to reading drop ho jaati hai aur status red ho jaata hai. Ye **data validation** hai.

### 2.5 Hourly diagnosis (edge analytics, level 2): GridGuard ka core

Har meter ki 60 readings (1 meter hour) jama karke ek summary banti hai:
- frozen share: kitne % readings `stuck` flagged
- spikes count
- negative share: kitne % readings −20 W se kam
- heavy minutes: kitne minute 5 kW se upar

Phir rules **upar se neeche** chalte hain, aur pehla match decide karta hai:

1. frozen > 15% → **meter fault** (reading frozen)
2. spikes ≥ 1 → **meter fault** (impossible spikes)
3. negative > 50% aur sun down (19:00–06:00) → **meter fault** (wired backwards)
4. negative > 20% aur ye meter raat ko bhi negative tha → **meter fault** (negative day and night)
5. negative > 20% → **genuine change** (solar panels?)
6. heavy ≥ 30 min → **genuine change** (EV charging?)
7. warna → **normal**

**Reversed vs solar: ye sabse acha concept hai, ise achhe se samjhao:**
- Din mein dono negative dikhte hain. Data se farak nahi pata chalta.
- Isliye function **yaad rakhta hai** (`reversedMeters` global memory) ki raat ko kaun sa meter mostly negative tha.
- Raat ko negative = solar ho hi nahi sakta = meter ulta hai. Agle din bhi woh meter "fault" hi rahega, solar nahi bolega.
- Pehle humara bug tha: shaam ko reversed meter ko solar bol deta tha. Sun-hours rule aur memory se fix kiya.

Isko **context-aware / rule-based edge analytics** kehte hain. Cloud tak raw data bheje bina, edge pe hi decision.

> Q: "Why do the analytics at the edge?"
> "Less data to the cloud, faster response, and it still works if the internet is down. Only summaries need to leave the gateway."

### 2.6 MongoDB

**Kya hai:** NoSQL **document database**. Data JSON-jaise documents (BSON) mein store hota hai; table aur fixed columns nahi hote.

**Kyun:**
- MQTT ka message already JSON hai, to seedha save ho jaata hai. Koi conversion nahi.
- Schema flexible hai: `flags` ek array hai, alerts aur diagnosis ke fields alag hain, koi problem nahi.
- Time-series jaisa append-heavy data easily handle hota hai.

**Hamara structure:** database `gridguard_iot`, 3 collections:

| Collection | Ek document = | Fields |
|---|---|---|
| `readings` | har reading | meter_id, household_id, session, ts, power_w, voltage_v, flags[], received_at |
| `alerts` | har flagged reading | meter_id, session, ts, problem, power_w |
| `diagnosis` | 1 meter × 1 hour | avg/max/min W, energy_kwh, frozen_share, spikes, negative_share, heavy_minutes, diagnosis, reason |

`session` = Node-RED kab start hua. Har run alag analyse kar sakte hain; notebook latest session uthata hai.

Node: `node-red-contrib-mongodb4`, operation `insertOne`, aur `msg.payload` hi document hai.

mongosh mein dikhane wale queries:
```js
use gridguard_iot
db.readings.countDocuments()
db.alerts.find().sort({_id: -1}).limit(5)
db.diagnosis.find({diagnosis: "meter fault"})
db.readings.aggregate([{ $group: { _id: "$meter_id", avg: { $avg: "$power_w" } } }])
```

### 2.7 ThingSpeak

**Kya hai:** MathWorks ka cloud IoT platform. Har **channel** mein 8 **fields** hote hain. Data HTTP se bhejte hain, aur woh khud charts bana deta hai. MATLAB analysis bhi kar sakte hain.

**Hamara upload:** "Collect 20 s window" har reading jodta jaata hai. "Every 20 s" pe average nikal ke ek HTTP GET bhejta hai:
```
https://api.thingspeak.com/update?api_key=WRITE_KEY&field1=..&field2=..…&field8=..
```

| Field | Value |
|---|---|
| 1–5 | MTR-00 se MTR-04 ka average power (W) |
| 6 | total neighbourhood load (W) |
| 7 | flagged readings count |
| 8 | kitne meters mein problem hai |

**20 second kyun?** Free plan mein ek channel pe minimum **15 sec** ka gap chahiye. Har second bhejte to ThingSpeak reject kar deta (response `0`). Isliye 20 sec average bhejte hain. Ye **data aggregation before cloud upload** hai: bandwidth bachti hai aur rate limit follow hoti hai.

**Response:** ThingSpeak success pe entry number deta hai (1, 2, 3…) aur fail pe `0`. "Check response" node isi ko status mein dikhata hai.

**Key safety:** Write API key tab 3 ke environment variable `THINGSPEAK_WRITE_KEY` mein hai. Isko public GitHub pe mat daalna.

> Q: "Why both MongoDB and ThingSpeak?"
> "MongoDB stores every raw reading locally for detailed analysis. ThingSpeak is the cloud layer: a public dashboard anyone can open, but with a rate limit, so it only receives 20-second summaries."

### 2.8 Dashboard (FlowFuse Dashboard 2.0)

- Live line chart (pichle 3 minute)
- Total-load gauge: green < 8 kW, orange 8–15 kW, red > 15 kW
- Meter clock
- Meter dropdown + 6 buttons. Button seedha `global.modes` change karta hai, jo simulator padhta hai. Ye **actuation / control path** hai: dashboard se device ka behaviour badalna.
- Diagnosis table aur last 12 alerts

### 2.9 Notebook 1: analysis

MongoDB se `pymongo` se latest session padhta hai, ek din tak trim karta hai, phir:
1. **Day panels**: har meter ka poora din, red dots = Node-RED ne flag kiya.
2. **Heat map** (meter × hour): blue = power le raha, red = export kar raha.
3. **Energy bars**: kWh = average W × hours / 1000.
4. **Flag counts**: reverse 220, stuck 230, spike 4.
5. **Diagnosis grid**: FAULT / CH.
6. **ThingSpeak read-back**: `api.thingspeak.com/channels/<id>/feeds.json` se wapas data padh ke plot karta hai (channel ID set ho tab).

Recorded day ke numbers: 7,135 readings, 454 flagged, 120 diagnoses (5 × 24).

---

## 3. Federated learning part: deep concepts

### 3.1 NILM: Non-Intrusive Load Monitoring

Meter sirf **total** deta hai, jaise 2,750 W. NILM ka sawaal: is total mein fridge kitna, kettle kitna, washing machine kitni?
- "Non-intrusive" matlab har appliance pe alag sensor nahi lagana; sirf main meter se andaza lagana hai.
- 1992 mein George Hart ne idea diya. Aaj deep learning se hota hai.
- Fayda: family ko pata chalta hai kaunsa appliance bijli kha raha hai, aur utility demand ko better samajh paati hai.

### 3.2 Seq2Point model

- **Input:** 59 minute ka total power (ek window).
- **Output:** window ke **beech wale minute** pe 3 appliances ka power (fridge, kettle, washing machine).
- Beech ka point isliye, ki model ko us minute ke pehle aur baad dono ka context mil jaata hai (kettle ON hua ya OFF).
- **Architecture:** 3 × Conv1D (pattern detectors: edges, ON/OFF steps) → MaxPool → 2 Linear layers. Total **48,715 parameters**.
- Training: Adam optimiser, lr 0.001, batch 128, loss = MSE. Error measure = **MAE in watts** on 2 homes jo training mein kabhi nahi the (unseen homes).
- Notebook 2 ka pehla chart: black line = jo meter dekhta hai, coloured areas = jo model ko nikalna hai.

### 3.3 Federated Learning: basics

**Problem:** accha model banane ke liye bahut gharon ka data chahiye, par koi apni minute-by-minute bijli ka data upload nahi karna chahega. Usse pata chalta hai ki aap kab ghar pe ho, kab soye ho, kaunse appliances hain. Ye privacy issue hai.

**Solution, Federated Learning (Google, McMahan et al. 2017):** data ghar mein hi rehta hai, model ghar jaata hai.

Ek **round** aise chalta hai:
1. Server current **global model** sab gharon ko bhejta hai.
2. Har ghar apne data pe kuch epochs train karta hai (local training).
3. Har ghar sirf **update** bhejta hai: Δ = naye weights − purane weights. Raw data kabhi nahi jaata.
4. Server sab updates ka **weighted average** leta hai aur global model update karta hai.
5. Repeat.

**FedAvg formula:**

  w(new) = w(old) + Σ (n_k × Δ_k) / Σ n_k

n_k = ghar k ke training samples. Jiske paas zyada data, uska weight zyada.

Hamare experiment mein: 8 ghar, 8 rounds, har round 2 epochs, har ghar apne last 2 din ke data pe.

### 3.4 FedAvg ki kamzori: Byzantine / poisoning attack

Server ko updates ke andar ka data nahi dikhta, sirf numbers dikhte hain. To koi bhi ghar jhoota update bhej sakta hai.

**Toy example (yaad rakhna, board pe samjha sakte ho):**
- 3 honest ghar: updates +1.0, +1.2, +0.8. Average = **+1.0**, sahi direction.
- **Sign-flip attacker** apna update ×(−5) karke −5 bhejta hai. Average = (1 + 1.2 + 0.8 − 5)/4 = **−0.5**. Model ulti direction mein chala gaya.
- **Scaling attacker** ×20 karke +20 bhejta hai. Average = (3 + 20)/4 = **5.75**. Bahut bada jump, model overshoot karke kharab.
- **Tampering:** update raste mein (network pe) badal diya gaya, man-in-the-middle.

Ek attacker hi poore average ko kheench sakta hai, kyunki average outliers ke saamne kamzor hai. Notebook mein FedAvg ka error 42 W se **316 W** tak chala gaya.

**Existing defences** (Krum, trimmed mean, median, FLTrust) jo bhi alag dikhe use hata dete hain. Problem: solar wala ghar, EV wala ghar aur kharab meter wala ghar bhi alag dikhte hain, to ye honest ghar bhi hat jaate hain. Unfair bhi hai, aur model naye pattern seekh bhi nahi paata.

### 3.5 GridGuard: kaise investigate karta hai

Har update ke saath do tarah ka **evidence** dekhta hai:

**(a) Meter evidence**: ghar ke andar compute hota hai, sirf 6 numbers bahar jaate hain (raw data nahi):
1. spikes ka share
2. stuck readings ka share
3. raat (00–04) mein negative ka share
4. din (07–17) mein negative ka share
5. usage change: log(abhi ka average / history ka average)
6. heavy load: kitne 60-minute windows poore 5 kW se upar

Ye wahi ideas hain jo Node-RED live karta hai. Real system mein IoT gateway ye numbers update ke saath bhej dega.

**(b) Update evidence**: server compute karta hai:
- **Size** = ‖Δ‖ / median ‖Δ‖. Vector ki length (norm), typical update se compare. Scaling attack ka size ~20 aata hai.
- **Direction** = cosine similarity (update, baaki updates ka median).
  - Cosine similarity = do arrows ke beech ka angle: **+1** same direction, **0** perpendicular, **−1** bilkul ulta.
  - Sign-flip attack ka direction negative aata hai.

**(c) Decision rules** (order important hai):
1. **Pehle meter check:** spikes > 0.1%, stuck > 5% ya raat ko negative > 30%, to **meter_fault**. Kharab meter se update bhi ajeeb aata hai, par woh family ki galti nahi hai, isliye meter pehle check hota hai.
2. **Update odd hai?** (size > 3, ya direction < 0)
   - Saath mein real-change evidence bhi hai, to **uncertain** (hold back, accuse mat karo).
   - Koi real-change evidence nahi, to **malicious**.
3. **Real change?** (din mein export aur raat ko nahi = solar, ya EV-size load, ya bada usage shift) → **genuine_change**.
4. Warna **benign**.

### 3.6 Trust scores aur weighted aggregation

Har ghar ke 3 alag scores (0 se 1):

| Score | Kab badalta hai | Matlab |
|---|---|---|
| Integrity | attack / bad signature pe **×0.5**, uncertain pe ×0.95, benign pe dheere badhta hai | kya ye ghar imaandaar hai? |
| Reliability | meter fault pe **×0.6** | kya iska meter bharosemand hai? |
| Adaptability | genuine change pe **+0.1** | kya ye naye behaviour mein hai? |

Teen alag scores kyun? Kharab meter wale ghar ki **integrity** kam nahi hoti, sirf reliability. Woh attacker nahi hai. Trust bar chart mein yahi dikhta hai.

**Weight:**
- benign: weight = integrity
- genuine change: weight = 0.5 × integrity × adaptability (aadha weight, careful adaptation)
- malicious / meter fault / uncertain / bad signature: 0
- integrity < 0.25: hamesha 0 (blacklist jaisa)

**Clipping:** har update ko median size ke 2 guna tak chhota kar dete hain, taaki koi bhi akela update model ko zyada na kheench sake.

Final: w(new) = w(old) + Σ (n_k × weight_k × clipped Δ_k) / Σ (n_k × weight_k)

### 3.7 Cryptography: signature aur hash chain

**Hash (SHA-256):** kisi bhi data ka 256-bit **fingerprint**.
- Ek bit bhi badlo to hash poora badal jaata hai.
- Hash se data wapas nahi nikal sakte (one-way).
- Do alag data ka same hash milna practically impossible hai.

**Digital signature (Ed25519):** har ghar ke paas ek **private key** (sirf uske paas) aur **public key** (server ke paas).
- Ghar sign karta hai: {client id, round, SHA-256(update), evidence}.
- Server public key se verify karta hai.
- Agar raste mein update badla, to hash badlega aur signature fail ho jayega, to **SIG** (reject).
- Analogy: private key = ghar ki apni mohar (stamp); public key se koi bhi check kar sakta hai ki mohar asli hai.
- house-07 ka update sign hone ke **baad** badla gaya tha. Signature ne round 5–8 mein pakad liya.

**Signature kya prove nahi karta (honest point, teacher impress hoga):** ye prove karta hai ki update raste mein nahi badla aur isi ghar ne bheja. Ye **nahi** prove karta ki meter physically sahi padh raha hai. Uske liye meter evidence hai.

**Audit chain (hash chain):** har decision ek record mein jaata hai, aur har record mein **pichle record ka hash** hota hai:

  h_i = SHA-256(i, entry_i, h_(i−1))

- Agar koi purana record chupke se badle (jaise operator "malicious" ko "benign" kar de), to uska hash badlega, aur aage ka chain toot jayega.
- Notebook demo: record 17 (house-01 malicious) ko benign kiya, to check ne turant **record 17** report kiya.
- Ye blockchain ka basic idea hai, bina mining ke. Tamper-**evident** log.

### 3.8 Results: kaise padhna hai

| Round | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|---|---|---|---|---|---|---|---|---|
| FedAvg (W) | 42.5 | 43.0 | 65.7 | 64.0 | **316.0** | 56.8 | 153.8 | 37.2 |
| GridGuard (W) | 42.5 | 43.0 | 36.7 | 42.5 | 24.7 | 24.5 | 29.0 | **23.4** |

- Round 1–2 dono same, kyunki sab honest hain. Ye fair comparison ka proof hai.
- Round 3 se attacks start, aur FedAvg upar-neeche hone lagta hai. Round 5 mein tampering bhi aa jaati hai.
- GridGuard behtar hota rehta hai. Final error FedAvg se **37% kam**.

Scorecard (64 decisions = 8 ghar × 8 rounds):
- causes correct **97%**
- attacks blocked **100%**
- faulty meters quarantined **100%**
- honest homes excluded **0%**

**97% kyun, 100% kyun nahi?** EV wala ghar round 3–4 mein "benign" bola gaya, "genuine change" nahi. Round 5 se sahi pakda. Uska update accept hi hua tha, to koi nuksaan nahi hua, bas change 2 round late pehchana. 2/64 galat = 97%. Ye khud bata dena: honesty se impression accha padta hai.

---

## 4. Viva ke likely sawaal

| Sawaal | Jawab (English mein bolo) |
|---|---|
| What is IoT analytics in your project? | Collecting sensor data (meters), processing it at the edge (Node-RED rules), storing it (MongoDB), visualising it in the cloud (ThingSpeak), and extracting insight (diagnosis, notebooks). |
| Why MQTT and not HTTP? | Publish/subscribe, tiny headers, persistent connection, broker pushes data. Ideal for many low-power devices. We still use HTTP for ThingSpeak because that is its API. |
| What is a broker? | The server that receives every published message and forwards it to subscribers of that topic. Ours is Aedes, running inside Node-RED. |
| What is QoS? Which did you use? | Delivery guarantee: 0 at most once, 1 at least once, 2 exactly once. Readings use 0 (they arrive every second); commands and alerts use 1. |
| What does `+` mean in a topic? | Single-level wildcard: `gridguard/meters/+/reading` matches every meter. |
| What is a Node-RED function node? | A node that runs our own JavaScript on each message. All our analytics rules live in function nodes. |
| What is context in Node-RED? | Memory that survives between messages: node, flow or global scope. We keep per-meter state in node context and the meter modes in global context. |
| Why MongoDB and not MySQL? | Messages are JSON, the schema differs per collection (flags array, diagnosis fields), and it handles append-heavy time-series data easily. |
| What is ThingSpeak's rate limit? | One update per 15 seconds on the free plan, so we send 20-second averages. |
| How do you tell a reversed meter from solar? | Solar only exports in daylight. A reversed meter is also negative at night, and we remember that per meter. |
| Why not flag a kettle as a spike? | A kettle is 2.5 kW and lasts about 3 minutes. A spike must be over 4 kW above both neighbouring minutes. |
| What is edge computing here? | Decisions are made in Node-RED next to the data, not in the cloud, so it is faster, uses less bandwidth and keeps working offline. |
| What is NILM? | Estimating individual appliance power from the single total reading of the main meter. |
| What is Seq2Point? | A CNN that takes a window of total power and predicts appliance power at the window's middle point. |
| What is federated learning? | Training a shared model where data stays at each client and only model updates are sent and averaged. |
| What is FedAvg? | The server's weighted average of the client updates, weighted by number of samples. |
| What is a poisoning / Byzantine attack? | A client sends a harmful update. Because FedAvg averages, one large or reversed update can ruin the model. |
| What is cosine similarity? | It measures the angle between two vectors: +1 same direction, −1 opposite. A sign-flip attack gives a negative value. |
| Why three trust scores and not one? | So a faulty meter loses *reliability* but not *integrity*: the family did nothing wrong. Attackers lose integrity. |
| Why give genuine change half weight? | Accept the new behaviour but adapt carefully, in case it is a disguised attack. |
| What does the signature prove? | That the update came from that home and was not changed in transit. It does not prove the meter reads correctly. |
| What is a hash chain? | Each log record stores the hash of the previous one, so editing any old record breaks the chain after it. |
| What if evidence is mixed? | The update is marked *uncertain* and held back, not called malicious. |
| Is your data real? | Simulated, with appliance models similar to public datasets like UK-DALE. Running on real datasets is listed as future work. |
| Where is OOP in your project? | Node-RED nodes are objects exchanging message objects, with private context (encapsulation). In Python, `Seq2Point` inherits from `torch.nn.Module` and overrides `forward` (inheritance, polymorphism), and `AuditChain` encapsulates the log. |
| What changed from the synopsis? | ThingSpeak instead of AWS (it is the course's cloud platform), a plain PyTorch loop instead of Flower (same FedAvg, easier to explain), Node-RED Dashboard instead of Streamlit, simulated meters instead of public datasets, and no Raspberry Pi yet. |
| Limitations? | Simulated meters, fixed thresholds, all FL clients in one notebook, no Raspberry Pi measurements, EV change detected two rounds late. |
| Future scope? | Real meters (ESP32 + current sensor) on the same topics, Raspberry Pi edge, real datasets with Flower, learned thresholds, TLS on MQTT. |

---

## 5. Agar demo mein kuch gadbad ho

| Problem | Fix |
|---|---|
| Log mein `Connection failed to broker` | Normal hai. Built-in broker ready hone se pehle client try karta hai; 15–20 sec mein connect ho jaata hai. |
| Dashboard khali | Node-RED start hone ke ~20 sec baad readings aati hain. Page refresh karo. |
| MongoDB nodes red | MongoDB service start karo (services.msc → MongoDB → Start). |
| ThingSpeak status grey | Key set nahi hai. Tab 3 → double-click → env var `THINGSPEAK_WRITE_KEY` → Deploy. |
| ThingSpeak "refused (400 / 0)" | Key galat hai, Write API Key dobara copy karo. |
| Diagnosis table khali | Pehla diagnosis 60 readings (1 real minute) ke baad aata hai. Thoda ruko. |
| Solar dikhana hai par raat chal rahi hai | Meter clock dekho: 06:30–18:30 mein hi solar negative hota hai. Tab tak EV ya stuck dikhao. |
| Notebook 1 naya chota session dikha raha | Notebook latest session padhta hai. Saved output (recorded day) hi dikhao, re-run mat karo. |

---

## 6. Cheat sheet (numbers jo yaad hone chahiye)

- 5 meters, 1 sec = 1 meter minute, 1 din = 24 min
- MQTT port 1883, Node-RED port 1880, MongoDB 27017
- Rules: stuck 10 same, spike > 4 kW, reverse < −20 W at 00–04, implausible > 23 kW
- Diagnosis: 60 readings; frozen > 15%, negative > 50% at night, > 20% by day, EV ≥ 30 min > 5 kW
- ThingSpeak: 8 fields, every 20 s (limit 15 s)
- Recorded day: 7,135 readings, 454 flagged, 120 diagnoses
- Energy: EV 34.8 kWh, solar −16.2 kWh, reversed −4.8 kWh
- FL: 8 homes, 8 rounds, model 48,715 params, window 59 min
- Attacks: sign flip ×(−5), scaling ×20, tamper after signing
- FedAvg worst 316 W, final 37.2 W; GridGuard final 23.4 W
- 97% causes correct, 100% attacks blocked, 100% faults quarantined, 0% honest excluded
- Audit chain: record 17 tamper caught
- Integrity ×0.5 per attack, cut-off 0.25; reliability ×0.6 per fault; genuine change half weight

Report: `report/GridGuard_Project_Report.pdf`. Isme saare flowcharts, UML diagrams, screenshots aur test cases hain.
