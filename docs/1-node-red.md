# Node-RED flows

Everything runs inside one Node-RED instance started with `npm start` from the `node-red` folder. The flow file is `node-red/flows.json`. Open http://localhost:1880 to see it.

Add-ons used (installed by `npm install`):

| Package | Why |
|---|---|
| `node-red-contrib-aedes` | an MQTT broker inside Node-RED, so no separate Mosquitto install is needed |
| `node-red-contrib-mongodb4` | writes to MongoDB |
| `@flowfuse/node-red-dashboard` | the live dashboard (Dashboard 2.0) |

## Tab 1: Smart meters

```
[MQTT broker on port 1883]

[Every second] ──▶ [Simulate 5 meters] ──▶ [Publish reading]  (MQTT out)

[Control commands] (MQTT in, gridguard/control/+) ──▶ [Change meter mode]
```

- **MQTT broker on port 1883** (Aedes node): the broker that all MQTT nodes connect to.
- **Every second** (inject): one tick is one minute of meter time. A day is 1440 ticks, which is 24 real minutes. The clock starts at midnight.
- **Simulate 5 meters** (function): builds a realistic reading for each home from background load, a fridge switching on and off, kettle uses in the morning and evening, and an occasional washing-machine cycle. It then applies the home's current **mode**:

| mode | effect on the reading |
|---|---|
| `normal` | nothing |
| `stuck` | the value freezes |
| `spike` | random jumps of 5 to 15 kW |
| `reverse` | the sign flips (meter wired backwards) |
| `ev` | +7 kW between 19:00 and 23:00 |
| `solar` | up to −3 kW around midday |

  Each message goes to topic `gridguard/meters/MTR-0X/reading`:

```json
{"meter_id": "MTR-01", "household_id": "house-01", "session": "2026-11-22T19:46:27Z",
 "ts": "2026-11-23T03:15:00.000Z", "power_w": -212.4, "voltage_v": 230.6}
```

- **Control commands**: any MQTT client can change a mode by publishing `{"mode": "stuck"}` to `gridguard/control/MTR-02` (or `.../all`). The dashboard buttons do the same thing directly.

## Tab 2: Ingest, detect, store

```
[Meter readings] (MQTT in) ──▶ [Check reading] ──┬─▶ [Save reading]   → MongoDB readings
                                                 ├─▶ [Hourly diagnosis] ─▶ [Save diagnosis] → MongoDB diagnosis
                                                 ├─▶ to ThingSpeak tab
                                                 ├─▶ to dashboard tab
                                                 └─(alerts)─▶ [Save alert] → MongoDB alerts
                                                            └▶ [Publish alert] (MQTT gridguard/alerts)
```

**Check reading** holds each reading back for one second, so it can compare it with the reading before *and* the reading after:

| flag | rule | meaning |
|---|---|---|
| `stuck` | 10 identical readings in a row | real readings always wobble a little |
| `spike` | the reading is more than 4 kW above both neighbours | no appliance switches on and off within one minute |
| `reverse` | negative power between 00:00 and 04:00 | solar can't export at night, so the meter is wired backwards |
| `implausible` | more than 23 kW | more than a home supply can deliver |

**Hourly diagnosis** collects 60 readings (one meter hour) per meter and decides:

| diagnosis | when |
|---|---|
| meter fault | more than 15% frozen readings, any spike, mostly negative while there is no sun (19:00 to 06:00), or negative in daylight for a meter that was already negative the night before |
| genuine change | more than 20% negative in daylight on a meter that was positive at night (solar), or 30+ minutes above 5 kW (EV) |
| normal | anything else |

During daylight, a reversed meter and a home with solar panels look the same, because both read negative. The difference shows when the sun is down: solar stops exporting, but a reversed meter stays negative. So the diagnosis remembers which meters were negative in the dark.

This is the GridGuard idea at the edge: a *broken meter* and a *home that really changed* both look "abnormal", but need opposite responses.

## Tab 3: ThingSpeak

```
from ingest ──▶ [Collect 20 s window]
[Every 20 s] ──▶ [Build ThingSpeak update] ──▶ [ThingSpeak update] (HTTP GET) ──▶ [Check response] ──▶ debug
```

Every 20 seconds (ThingSpeak's free plan allows one update every 15 s), Node-RED sends the averages of the last window. See [3-thingspeak.md](3-thingspeak.md) for the fields and for where to put the API key. If no key is set, the node status shows *no THINGSPEAK_WRITE_KEY set* and nothing is sent.

## Tab 4: Dashboard

Open http://localhost:1880/dashboard.

| Widget | Shows |
|---|---|
| Power chart | the last 3 minutes of every meter, one line per home |
| Total load gauge | the whole neighbourhood in kW (green, then orange from 8 kW, then red from 15 kW) |
| Meter time | the simulated clock |
| Meter dropdown and 6 buttons | pick a meter (or all) and switch it to Normal, Stuck, Spikes, Reversed, EV charger or Solar |
| Diagnosis table | the latest hourly diagnosis of every meter, with the reason |
| Alerts table | the last 12 flagged readings |

## Tips

- After editing a flow in the browser, press **Deploy**. Node-RED saves the change into `node-red/flows.json`.
- A red or grey dot under a node is its status. For example, *Check response* in tab 3 shows whether ThingSpeak accepted the last upload.
- Restarting Node-RED starts a new **session**: the clock goes back to midnight, and the notebooks then analyse the new session.
- At start-up the log may show `Connection failed to broker` once. The MQTT client tries before the built-in broker is ready, and connects about 15 seconds later.
