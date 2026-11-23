# ThingSpeak

ThingSpeak is the cloud side: it stores the uploaded values and draws charts that anyone with the link can open.

## 1. Create the channel

1. Sign in at https://thingspeak.mathworks.com (a free MathWorks account is enough).
2. **Channels → My Channels → New Channel**.
3. Name it `GridGuard` and tick all 8 fields:

| Field | Name to type |
|---|---|
| Field 1 | MTR-00 power (W) |
| Field 2 | MTR-01 power (W) |
| Field 3 | MTR-02 power (W) |
| Field 4 | MTR-03 power (W) |
| Field 5 | MTR-04 power (W) |
| Field 6 | Total load (W) |
| Field 7 | Flagged readings |
| Field 8 | Meters with a problem |

4. Save the channel. Open the **API Keys** tab and copy the **Write API Key**. Note the **Channel ID** at the top too.

## 2. Give the key to Node-RED

1. Open http://localhost:1880 and go to tab **3. ThingSpeak**.
2. Double-click the tab name. Under **Environment Variables**, set `THINGSPEAK_WRITE_KEY` to your Write API Key.
3. Click **Done**, then **Deploy**.

Within 20 seconds the *Check response* node shows *sent entry 1, total … W*, and the channel's charts start filling. If it says *ThingSpeak refused (400 / 0)*, the key is wrong.

The key is stored inside `flows.json`. Don't put the file in a public repository with your real key in it.

## 3. What to show on ThingSpeak

- **Private View / Public View**: one chart per field. Field 6 shows the neighbourhood load rise in the evening. Fields 7 and 8 jump whenever you break a meter from the dashboard.
- **Add Visualizations → Numeric Display / Gauge** on field 6 makes a neat live widget.
- **Sharing → Share channel view with everyone** gives a public link you can give the teacher.

## 4. Read it back in Python

`notebooks/1_iot_data_analysis.ipynb` has a ThingSpeak section. Before starting Jupyter, set:

```powershell
$env:THINGSPEAK_CHANNEL_ID = "your channel id"
$env:THINGSPEAK_READ_KEY = "your read key"
```

The read key is only needed if the channel is private. The notebook downloads the last 500 entries and plots the total load and the alerts.
