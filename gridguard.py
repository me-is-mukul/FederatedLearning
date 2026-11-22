import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd
import torch
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from torch import nn

APPLIANCES = ["fridge", "kettle", "washing_machine"]
SCALES = [200.0, 3000.0, 2500.0]
DAY = 1440
WINDOW = 59
WARMUP = 3

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
NODE_RED_URL = os.getenv("NODE_RED_URL", "http://localhost:1880")
S3_BUCKET = os.getenv("S3_BUCKET", "")

EVENTS = {
    "normal": (None, None),
    "attack: sign flip": ("attack", "sign_flip"),
    "attack: scaling": ("attack", "scaling"),
    "attack: tampering": ("attack", "tamper"),
    "fault: stuck meter": ("fault", "stuck"),
    "fault: spiking meter": ("fault", "spike"),
    "fault: reversed meter": ("fault", "reverse"),
    "change: EV charger": ("change", "ev"),
    "change: solar panels": ("change", "solar"),
}
LABELS = {None: "benign", "attack": "malicious", "fault": "meter_fault", "change": "genuine_change"}
ACTIONS = {"benign": "accept", "genuine_change": "accept ½", "malicious": "reject", "meter_fault": "quarantine", "uncertain": "defer", "bad_signature": "reject"}
DEFAULT_SCENARIO = {
    "house-01": ("attack: sign flip", 3),
    "house-02": ("attack: scaling", 3),
    "house-03": ("fault: stuck meter", 3),
    "house-04": ("fault: reversed meter", 4),
    "house-05": ("change: EV charger", 3),
    "house-06": ("change: solar panels", 4),
    "house-07": ("attack: tampering", 5),
}


def block(load, start, length, power):
    start, end = int(start), min(len(load), int(start) + int(length))
    if start < end:
        load[start:end] += power


def make_household(seed, days):
    rng = np.random.default_rng(seed)
    n = days * DAY
    minute = np.arange(n) % DAY
    base = rng.uniform(50, 150) * (1 + 0.05 * np.sin(2 * np.pi * minute / DAY)) + rng.uniform(100, 300) * ((minute > 1050) & (minute < 1380))
    fridge, kettle, washer = np.zeros(n), np.zeros(n), np.zeros(n)
    on, off, t = rng.uniform(15, 22), rng.uniform(30, 45), rng.uniform(0, 60)
    while t < n:
        block(fridge, t, on, rng.uniform(80, 130))
        t += on + off * rng.uniform(0.85, 1.15)
    for day in range(days):
        for _ in range(rng.poisson(4)):
            block(kettle, day * DAY + rng.choice([rng.uniform(380, 540), rng.uniform(960, 1320)]), rng.integers(2, 5), 2500)
        if rng.random() < 0.5:
            t = day * DAY + rng.uniform(480, 1200)
            block(washer, t, 15, 2000)
            block(washer, t + 15, 40, rng.uniform(150, 300))
            block(washer, t + 55, 10, rng.uniform(400, 600))
    total = base + fridge + kettle + washer + rng.normal(0, 2, n)
    frame = pd.DataFrame({"aggregate": np.round(np.maximum(total, 0), 1), "fridge": fridge, "kettle": kettle, "washing_machine": washer})
    frame.index = pd.date_range("2026-01-05", periods=n, freq="60s")
    return frame


def add_event(frame, kind, start_day, seed):
    rng = np.random.default_rng(seed)
    x = frame["aggregate"].to_numpy(copy=True)
    start = start_day * DAY
    minute = np.arange(len(x)) % DAY
    if kind == "ev":
        for day in range(start_day, len(x) // DAY):
            if rng.random() < 0.8:
                block(x, day * DAY + rng.uniform(1080, 1320), rng.integers(120, 300), 7000)
    elif kind == "solar":
        x[start:] -= 3000 * np.clip(np.sin(np.pi * (minute[start:] - 390) / 720), 0, None)
    elif kind == "spike":
        hits = start + np.flatnonzero(rng.random(len(x) - start) < 0.004)
        x[hits] += rng.uniform(5000, 15000, len(hits))
    elif kind == "stuck":
        t = start
        while t < len(x):
            t += int(rng.integers(100, 400))
            length = int(rng.integers(30, 240))
            x[t : t + length] = x[min(t, len(x) - 1)]
            t += length
    elif kind == "reverse":
        x[start:] = -x[start:]
    result = frame.copy()
    result["aggregate"] = np.round(x, 1)
    return result


class Seq2Point(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(1, 16, 9, padding=4), nn.ReLU(),
            nn.Conv1d(16, 16, 7, padding=3), nn.ReLU(), nn.MaxPool1d(2),
            nn.Conv1d(16, 24, 5, padding=2), nn.ReLU(), nn.Flatten(),
            nn.Linear(24 * (WINDOW // 2), 64), nn.ReLU(), nn.Linear(64, len(APPLIANCES)),
        )

    def forward(self, x):
        return self.net(x.unsqueeze(1))


def windows(frame, stride=2):
    agg = frame["aggregate"].to_numpy(dtype=np.float32) / 2000
    target = frame[APPLIANCES].to_numpy(dtype=np.float32) / np.array(SCALES, dtype=np.float32)
    starts = np.arange(0, len(agg) - WINDOW + 1, stride)
    return torch.tensor(np.lib.stride_tricks.sliding_window_view(agg, WINDOW)[starts]), torch.tensor(target[starts + WINDOW // 2])


def train_local(weights, frame, seed):
    model = Seq2Point()
    load(model, weights)
    x, y = windows(frame)
    torch.manual_seed(seed)
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    for _ in range(2):
        for batch in torch.randperm(len(x)).split(128):
            optimizer.zero_grad()
            nn.functional.mse_loss(model(x[batch]), y[batch]).backward()
            optimizer.step()
    return [new.detach() - old for new, old in zip(model.parameters(), weights)], len(x)


def load(model, weights):
    with torch.no_grad():
        for param, value in zip(model.parameters(), weights):
            param.copy_(value)


def error_in_watts(weights, frames):
    model = Seq2Point()
    load(model, weights)
    model.eval()
    with torch.no_grad():
        errors = [((model(x).clamp(min=0) - y).abs() * torch.tensor(SCALES)).mean(dim=0) for x, y in (windows(f, 1) for f in frames)]
    return float(torch.stack(errors).mean())


def meter_evidence(current, reference):
    x = current.to_numpy(dtype=float)
    minute = current.index.hour.to_numpy() * 60 + current.index.minute.to_numpy()
    run, stuck = 0, 0
    for same in np.diff(x) == 0:
        run = run + 1 if same else 0
        stuck += run >= 9
    level = (np.clip(x, 0, None).mean() + 10) / (np.clip(reference.to_numpy(dtype=float), 0, None).mean() + 10)
    return {
        "spikes": float(np.mean(x[1:-1] - np.maximum(x[:-2], x[2:]) > 4000)),
        "stuck": float(stuck / len(x)),
        "negative_at_night": float(np.mean(x[minute < 240] < -20)),
        "negative_by_day": float(np.mean(x[(minute >= 420) & (minute < 1020)] < -20)),
        "usage_change": float(np.log(level)),
        "heavy_load": float(np.mean(np.convolve(x > 5000, np.ones(60), "valid") >= 60)),
    }


def update_evidence(updates):
    flat = {cid: torch.cat([w.flatten() for w in u]) for cid, u in updates.items()}
    median = float(np.median([v.norm() for v in flat.values()]))
    result = {}
    for cid, v in flat.items():
        others = torch.stack([o for other, o in flat.items() if other != cid])
        result[cid] = {"size": float(v.norm()) / median, "direction": float(nn.functional.cosine_similarity(v, others.median(dim=0).values, dim=0))}
    return result


def find_cause(meter, update, integrity):
    fault = meter["spikes"] > 0.001 or meter["stuck"] > 0.05 or meter["negative_at_night"] > 0.3
    solar = meter["negative_by_day"] > 0.1 and meter["negative_at_night"] < 0.05
    change = solar or meter["heavy_load"] > 0.01 or abs(meter["usage_change"]) > 0.4
    odd = update["size"] > 3 or update["direction"] < 0 or (integrity < 0.5 and update["direction"] < 0.1)
    if fault:
        return "meter_fault"
    if odd:
        return "uncertain" if change else "malicious"
    return "genuine_change" if change else "benign"


def new_trust():
    return {"integrity": 1.0, "reliability": 1.0, "adaptability": 0.5}


def update_trust(t, cause):
    if cause == "benign":
        t["integrity"] = min(1.0, t["integrity"] + 0.1 * t["integrity"] * (1 - t["integrity"]) + 0.01)
        t["reliability"] = min(1.0, t["reliability"] + 0.1)
    elif cause in ("malicious", "bad_signature"):
        t["integrity"] *= 0.5
    elif cause == "meter_fault":
        t["reliability"] *= 0.6
    elif cause == "genuine_change":
        t["adaptability"] = min(1.0, t["adaptability"] + 0.1)
    elif cause == "uncertain":
        t["integrity"] *= 0.95


def weight_for(t, cause):
    if t["integrity"] < 0.25:
        return 0.0
    return {"benign": t["integrity"], "genuine_change": 0.5 * t["integrity"] * t["adaptability"]}.get(cause, 0.0)


def fingerprint(update):
    return hashlib.sha256(b"".join(w.numpy().astype("float32").tobytes() for w in update)).hexdigest()


def signed_message(cid, round_number, update, evidence):
    return json.dumps({"client": cid, "round": round_number, "hash": fingerprint(update), "evidence": evidence}, sort_keys=True).encode()


def signature_ok(public_key, signature, message):
    try:
        public_key.verify(signature, message)
        return True
    except InvalidSignature:
        return False


class AuditLog:
    def __init__(self):
        self.records = []

    def add(self, entry):
        record = {"index": len(self.records), "entry": entry, "previous": self.records[-1]["hash"] if self.records else "0" * 64}
        record["hash"] = hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()
        self.records.append(record)

    def first_broken(self):
        previous = "0" * 64
        for record in self.records:
            body = {k: record[k] for k in ("index", "entry", "previous")}
            if record["previous"] != previous or hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() != record["hash"]:
                return record["index"]
            previous = record["hash"]
        return None


def average(weights, updates, factors):
    total = sum(factors)
    if total == 0:
        return weights
    return [w + sum(f * u[i] for u, f in zip(updates, factors)) / total for i, w in enumerate(weights)]


class Federation:
    def __init__(self, scenario=DEFAULT_SCENARIO, clients=8, rounds=10):
        self.rounds, self.round = rounds, 0
        self.clients = []
        for i in range(clients):
            cid = f"house-{i:02d}"
            event, start = scenario.get(cid, ("normal", 1))
            category, kind = EVENTS[event]
            frame = make_household(i, WARMUP + rounds)
            if category in ("fault", "change"):
                frame = add_event(frame, kind, WARMUP + start - 1, i)
            self.clients.append({"id": cid, "frame": frame, "category": category, "kind": kind, "start": start, "key": Ed25519PrivateKey.generate()})
        self.test_homes = [make_household(900 + i, 2) for i in range(2)]
        torch.manual_seed(0)
        start_weights = [p.detach().clone() for p in Seq2Point().parameters()]
        self.weights = {"FedAvg": start_weights, "GridGuard": [w.clone() for w in start_weights]}
        self.trust = {c["id"]: new_trust() for c in self.clients}
        self.log = AuditLog()
        self.history, self.decisions = [], []

    def label(self, client, round_number):
        return LABELS[client["category"]] if client["category"] and round_number >= client["start"] else "benign"

    def client_round(self, client, weights, r):
        data = client["frame"].iloc[(WARMUP + r - 2) * DAY : (WARMUP + r) * DAY]
        evidence = meter_evidence(data["aggregate"], client["frame"]["aggregate"].iloc[: 2 * DAY])
        update, samples = train_local(weights, data, seed=r * 100 + int(client["id"][-2:]))
        attacking = client["category"] == "attack" and r >= client["start"]
        if attacking and client["kind"] == "sign_flip":
            update = [-5 * u for u in update]
        if attacking and client["kind"] == "scaling":
            update = [20 * u for u in update]
        signature = client["key"].sign(signed_message(client["id"], r, update, evidence))
        if attacking and client["kind"] == "tamper":
            update = [update[0] + 0.01] + update[1:]
        return {"client": client, "update": update, "samples": samples, "evidence": evidence, "signature": signature}

    def gridguard(self, messages, r):
        verified = []
        for m in messages:
            cid = m["client"]["id"]
            if signature_ok(m["client"]["key"].public_key(), m["signature"], signed_message(cid, r, m["update"], m["evidence"])):
                verified.append(m)
            else:
                update_trust(self.trust[cid], "bad_signature")
                self.decisions.append({"round": r, "client": cid, "truth": self.label(m["client"], r), "cause": "bad_signature", "weight": 0.0})
        info = update_evidence({m["client"]["id"]: m["update"] for m in verified})
        limit = 2 * np.median([info[m["client"]["id"]]["size"] for m in verified])
        updates, factors = [], []
        for m in verified:
            cid = m["client"]["id"]
            cause = find_cause(m["evidence"], info[cid], self.trust[cid]["integrity"])
            update_trust(self.trust[cid], cause)
            factor = m["samples"] * weight_for(self.trust[cid], cause)
            shrink = min(1.0, limit / info[cid]["size"])
            updates.append([u * shrink for u in m["update"]])
            factors.append(factor)
            self.decisions.append({"round": r, "client": cid, "truth": self.label(m["client"], r), "cause": cause, "weight": factor, **info[cid], **m["evidence"], **self.trust[cid]})
        for d in self.decisions[-len(messages):]:
            self.log.add({"round": r, "client": d["client"], "cause": d["cause"], "action": ACTIONS[d["cause"]]})
        return updates, factors

    def step(self):
        r = self.round = self.round + 1
        fed = [self.client_round(c, self.weights["FedAvg"], r) for c in self.clients]
        self.weights["FedAvg"] = average(self.weights["FedAvg"], [m["update"] for m in fed], [m["samples"] for m in fed])
        guarded = [self.client_round(c, self.weights["GridGuard"], r) for c in self.clients]
        self.weights["GridGuard"] = average(self.weights["GridGuard"], *self.gridguard(guarded, r))
        for name, weights in self.weights.items():
            self.history.append({"round": r, "strategy": name, "error_w": error_in_watts(weights, self.test_homes)})
        return [d for d in self.decisions if d["round"] == r]

    def summary(self):
        d = pd.DataFrame(self.decisions)
        found = d["cause"].replace("bad_signature", "malicious")
        last = {h["strategy"]: h["error_w"] for h in self.history if h["round"] == self.round}
        return {
            "fedavg_error_w": last["FedAvg"],
            "gridguard_error_w": last["GridGuard"],
            "correct_cause": float((found == d["truth"]).mean()),
            "attacks_blocked": float((d[d.truth == "malicious"].weight == 0).mean()) if (d.truth == "malicious").any() else None,
            "honest_excluded": float(d[d.truth.isin(["benign", "genuine_change"])].cause.isin(["malicious", "meter_fault", "bad_signature"]).mean()),
            "faults_quarantined": float((d[d.truth == "meter_fault"].cause == "meter_fault").mean()) if (d.truth == "meter_fault").any() else None,
            "audit_log_ok": self.log.first_broken() is None,
        }


def save_to_mongo(fed, run_id):
    from pymongo import MongoClient

    db = MongoClient(MONGO_URI, serverSelectionTimeoutMS=1500).gridguard
    db.runs.insert_one({"run_id": run_id, "summary": fed.summary(), "history": fed.history, "decisions": fed.decisions, "audit_log": fed.log.records})


def upload_to_s3(fed, run_id):
    import boto3

    body = json.dumps({"summary": fed.summary(), "history": fed.history, "decisions": fed.decisions, "audit_log": fed.log.records}, default=float)
    boto3.client("s3").put_object(Bucket=S3_BUCKET, Key=f"gridguard/{run_id}.json", Body=body.encode())
    return f"s3://{S3_BUCKET}/gridguard/{run_id}.json"


def run_meters(count, interval, start_hour=None):
    import paho.mqtt.client as mqtt

    meters = {}
    for i in range(count):
        meters[f"MTR-{i:02d}"] = {"house": f"house-{i:02d}", "trace": make_household(100 + i, 7)["aggregate"].to_numpy(), "mode": None, "held": None}
    rng = np.random.default_rng(0)

    def on_command(client, userdata, msg):
        command = json.loads(msg.payload)
        for meter_id, meter in meters.items():
            if msg.topic.endswith("/" + meter_id) or msg.topic.endswith("/all"):
                meter["mode"], meter["held"] = command.get("mode"), None
                print(meter_id, "->", meter["mode"] or "normal")

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.on_message = on_command
    client.on_connect = lambda c, userdata, flags, reason, properties: c.subscribe("gridguard/control/+")
    client.connect(MQTT_HOST, 1883)
    client.loop_start()
    now = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    if start_hour is not None:
        now = now.replace(hour=start_hour, minute=0)
    first = now.hour * 60 + now.minute
    print(f"{count} meters publishing to {MQTT_HOST}, Ctrl+C to stop")
    for step in range(10**9):
        ts = now + timedelta(minutes=step)
        minute = ts.hour * 60 + ts.minute
        for meter_id, m in meters.items():
            power = float(m["trace"][(first + step) % len(m["trace"])])
            power += 7000 if m["mode"] == "ev" and 1140 <= minute < 1380 else 0
            power -= 3000 * max(0.0, np.sin(np.pi * (minute - 390) / 720)) if m["mode"] == "solar" else 0
            power += rng.uniform(5000, 15000) if m["mode"] == "spike" and rng.random() < 0.03 else 0
            power = -power if m["mode"] == "reverse" else power
            if m["mode"] == "stuck":
                m["held"] = power if m["held"] is None else m["held"]
                power = m["held"]
            reading = {"meter_id": meter_id, "household_id": m["house"], "ts": ts.strftime("%Y-%m-%dT%H:%M:%SZ"), "power_w": round(power, 1)}
            client.publish(f"gridguard/meters/{meter_id}/reading", json.dumps(reading))
        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="GridGuard: python gridguard.py train | meters")
    parser.add_argument("command", choices=["train", "meters"])
    parser.add_argument("--rounds", type=int, default=10)
    parser.add_argument("--meters", type=int, default=5)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--start-hour", type=int, choices=range(24), default=None)
    args = parser.parse_args()
    if args.command == "meters":
        run_meters(args.meters, args.interval, args.start_hour)
    else:
        federation = Federation(rounds=args.rounds)
        for _ in range(args.rounds):
            federation.step()
            fed, guard = federation.history[-2:]
            print(f"round {federation.round:2d}   FedAvg error {fed['error_w']:7.1f} W   GridGuard error {guard['error_w']:6.1f} W")
        print(json.dumps(federation.summary(), indent=2))
