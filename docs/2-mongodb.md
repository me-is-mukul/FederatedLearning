# MongoDB

Node-RED writes to `mongodb://localhost:27017`, database **`gridguard_iot`**. Make sure the MongoDB service is running (Windows: *Services* → *MongoDB Server* → Start).

## Collections

| Collection | One document per | Fields |
|---|---|---|
| `readings` | meter per meter minute | `meter_id`, `household_id`, `session`, `ts` (meter time), `power_w`, `voltage_v`, `flags`, `received_at` |
| `alerts` | flagged reading | `meter_id`, `session`, `ts`, `problem`, `power_w` |
| `diagnosis` | meter per meter hour | `meter_id`, `session`, `hour_start`, `avg_w`, `max_w`, `min_w`, `energy_kwh`, `frozen_share`, `spikes`, `negative_share`, `heavy_minutes`, `diagnosis`, `reason` |

`session` is the time Node-RED started the simulator. Each restart is a new session, which keeps runs apart.

## Looking at the data

**MongoDB Compass**: connect to `mongodb://localhost:27017` and open `gridguard_iot`.

**mongosh** examples:

```javascript
use gridguard_iot
db.readings.countDocuments()
db.readings.find({meter_id: "MTR-01"}).sort({received_at: -1}).limit(5)
db.alerts.aggregate([{$group: {_id: {meter: "$meter_id", problem: "$problem"}, count: {$sum: 1}}}])
db.diagnosis.find({diagnosis: {$ne: "normal"}}, {meter_id: 1, hour_start: 1, diagnosis: 1, reason: 1, _id: 0})
```

**Notebook**: `notebooks/1_iot_data_analysis.ipynb` loads the latest session into pandas and draws the graphs.

To start fresh, drop the database (`db.dropDatabase()` inside `use gridguard_iot`). Node-RED recreates it automatically.
