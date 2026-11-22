from datetime import datetime

import altair as alt
import pandas as pd
import requests
import streamlit as st

import gridguard as gg

st.set_page_config(page_title="GridGuard", page_icon=":material/bolt:", layout="wide")

CAUSE_COLORS = {
    "benign": "#2a78d6",
    "genuine_change": "#1baf7a",
    "meter_fault": "#eb6834",
    "malicious": "#e34948",
    "uncertain": "#898781",
    "bad_signature": "#6250d6",
}
CAUSE_LETTER = {"benign": "OK", "genuine_change": "CH", "meter_fault": "FX", "malicious": "AT", "uncertain": "?", "bad_signature": "SIG"}
APPLIANCE_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]
DARK = getattr(getattr(st.context, "theme", None), "type", "light") == "dark"
INK = "#f0efec" if DARK else "#0b0b0b"

st.markdown(
    """
    <style>
    .hero {padding: 1.4rem 1.6rem; border-radius: 16px; margin-bottom: 1rem;
           background: linear-gradient(120deg, rgba(42,120,214,.18), rgba(27,175,122,.14));
           border: 1px solid rgba(127,127,127,.25);}
    .hero h1 {margin: 0; font-size: 2.2rem;}
    .hero p {margin: .3rem 0 0 0; opacity: .85; font-size: 1.05rem;}
    .steps {display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: .7rem; margin-top: 1rem;}
    .step {padding: .8rem; border-radius: 12px; background: rgba(127,127,127,.10); font-size: .92rem;}
    .step b {display: block; margin-bottom: .2rem;}
    .block {font-family: monospace; font-size: .8rem; padding: .55rem .7rem; border-radius: 10px;
            border: 1px solid rgba(127,127,127,.35); margin-bottom: .45rem;}
    .broken {border-color: #e34948; background: rgba(227,73,72,.12);}
    </style>
    <div class="hero">
      <h1>GridGuard</h1>
      <p>Homes train one shared AI model on their smart-meter data without sharing the data itself.
         When a home sends a strange update, GridGuard works out <b>why</b>: an attacker, a broken meter, or a real change like a new EV.</p>
      <div class="steps">
        <div class="step"><b>1. Measure</b>Each home's meter records total power every minute.</div>
        <div class="step"><b>2. Learn locally</b>Each home trains the model on its own data and signs the result.</div>
        <div class="step"><b>3. Investigate</b>The server checks the signature, the meter evidence and the update itself.</div>
        <div class="step"><b>4. Decide</b>Accept, accept half, quarantine, or reject, and write it to a tamper-proof log.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_home, tab_train, tab_chain, tab_live = st.tabs(
    [":material/home: Explore a home", ":material/hub: Train the federation", ":material/link: Audit chain", ":material/sensors: Live meters"]
)


@st.cache_data
def household(seed, event, days=5):
    frame = gg.make_household(seed, days)
    category, kind = gg.EVENTS[event]
    return gg.add_event(frame, kind, 3, seed) if category in ("fault", "change") else frame


with tab_home:
    st.subheader("What does a smart meter see?")
    st.write("The meter only records the **total** (black line). The coloured areas are what each appliance really used; the AI has to learn to recover them from the total alone. Add an event and watch what changes from day 4.")
    left, right = st.columns([1, 3])
    with left:
        seed = st.slider("Home number", 0, 7, 2)
        event = st.selectbox("Event from day 4", list(gg.EVENTS), index=0)
        day = st.slider("Day to view", 1, 5, 4)
        frame = household(seed, event)
        reference = frame["aggregate"].iloc[: 2 * gg.DAY]
        evidence = gg.meter_evidence(frame["aggregate"].iloc[2 * gg.DAY : 5 * gg.DAY], reference)
        verdict = gg.find_cause(evidence, {"size": 1.0, "direction": 0.5}, 1.0)
        st.metric("GridGuard's reading of this meter", verdict.replace("_", " "))
        st.caption("Assuming the model update itself looks normal.")
    with right:
        view = frame.iloc[(day - 1) * gg.DAY : day * gg.DAY].reset_index(names="time")
        parts = view.melt(id_vars="time", value_vars=gg.APPLIANCES, var_name="appliance", value_name="watts")
        areas = alt.Chart(parts).mark_area(opacity=0.75).encode(
            x=alt.X("time:T", title=None),
            y=alt.Y("watts:Q", stack=True, title="power (W)"),
            color=alt.Color("appliance:N", scale=alt.Scale(domain=gg.APPLIANCES, range=APPLIANCE_COLORS), legend=alt.Legend(orient="top", title=None)),
            tooltip=["time:T", "appliance:N", alt.Tooltip("watts:Q", format=".0f")],
        )
        meter = alt.Chart(view).mark_line(color=INK, strokeWidth=1.2).encode(x="time:T", y="aggregate:Q", tooltip=["time:T", alt.Tooltip("aggregate:Q", title="meter reading", format=".0f")])
        st.altair_chart((areas + meter).properties(height=360).interactive(bind_y=False), width="stretch")
    with st.expander("The six numbers this home sends instead of its raw data"):
        st.dataframe(pd.DataFrame([evidence]).T.rename(columns={0: "value"}).style.format("{:.4f}"))
        st.write(
            "- **spikes / stuck / negative at night** point to a broken meter.\n"
            "- **negative by day** (solar), **heavy load** (EV) and **usage change** point to a real change in the home.\n"
            "- The raw readings never leave the house."
        )


def error_chart(history):
    data = pd.DataFrame(history)
    return (
        alt.Chart(data)
        .mark_line(point=alt.OverlayMarkDef(size=60, filled=True), strokeWidth=2.5)
        .encode(
            x=alt.X("round:O", title="training round", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("error_w:Q", scale=alt.Scale(type="log"), title="model error in watts (log scale, lower is better)"),
            color=alt.Color("strategy:N", scale=alt.Scale(domain=["GridGuard", "FedAvg"], range=["#2a78d6", "#eb6834"]), legend=alt.Legend(orient="top", title=None)),
            tooltip=["strategy", "round", alt.Tooltip("error_w:Q", title="error (W)", format=".1f")],
        )
        .properties(height=320)
    )


def decision_grid(decisions):
    data = pd.DataFrame(decisions)
    data["code"] = data["cause"].map(CAUSE_LETTER)
    data["action"] = data["cause"].map(gg.ACTIONS)
    domain = [c for c in CAUSE_COLORS if c in set(data["cause"])]
    base = alt.Chart(data).encode(
        x=alt.X("round:O", title="training round", axis=alt.Axis(labelAngle=0)),
        y=alt.Y("client:N", title=None),
        tooltip=["client", "round", alt.Tooltip("truth", title="really is"), alt.Tooltip("cause", title="GridGuard says"), "action"],
    )
    cells = base.mark_rect(cornerRadius=5, stroke="white", strokeWidth=2).encode(
        color=alt.Color("cause:N", scale=alt.Scale(domain=domain, range=[CAUSE_COLORS[c] for c in domain]), legend=alt.Legend(orient="top", title=None))
    )
    return (cells + base.mark_text(color="white", fontWeight="bold", fontSize=11).encode(text="code")).properties(height=34 * data["client"].nunique() + 40)


def show_summary(fed):
    s = fed.summary()
    cols = st.columns(4)
    cols[0].metric("FedAvg final error", f"{s['fedavg_error_w']:.1f} W")
    cols[1].metric("GridGuard final error", f"{s['gridguard_error_w']:.1f} W", delta=f"{s['gridguard_error_w'] - s['fedavg_error_w']:.1f} W", delta_color="inverse")
    cols[2].metric("Causes identified correctly", f"{s['correct_cause']:.0%}")
    cols[3].metric("Honest homes wrongly excluded", f"{s['honest_excluded']:.0%}")
    cols = st.columns(3)
    cols[0].metric("Attacks blocked", "-" if s["attacks_blocked"] is None else f"{s['attacks_blocked']:.0%}")
    cols[1].metric("Faulty meters quarantined", "-" if s["faults_quarantined"] is None else f"{s['faults_quarantined']:.0%}")
    cols[2].metric("Audit chain", "intact" if s["audit_log_ok"] else "BROKEN")


with tab_train:
    st.subheader("Set up the neighbourhood")
    st.write("Eight homes train together. Choose what happens in each home and from which round, then press **Train**. FedAvg (the normal method) and GridGuard train side by side on exactly the same data.")
    rounds = st.slider("Training rounds", 4, 12, 10)
    table = pd.DataFrame(
        [{"home": f"house-{i:02d}", "event": gg.DEFAULT_SCENARIO.get(f"house-{i:02d}", ("normal", 1))[0], "from round": gg.DEFAULT_SCENARIO.get(f"house-{i:02d}", ("normal", 1))[1]} for i in range(8)]
    )
    edited = st.data_editor(
        table,
        hide_index=True,
        disabled=["home"],
        column_config={
            "event": st.column_config.SelectboxColumn(options=list(gg.EVENTS), required=True),
            "from round": st.column_config.NumberColumn(min_value=1, max_value=12, step=1, required=True),
        },
    )
    if st.button("Train", type="primary", icon=":material/play_arrow:"):
        scenario = {row["home"]: (row["event"], int(row["from round"])) for _, row in edited.iterrows()}
        fed = gg.Federation(scenario, rounds=rounds)
        st.session_state.pop("fed", None)
        progress = st.progress(0.0, text="Preparing homes")
        chart_slot, grid_slot = st.empty(), st.empty()
        for r in range(1, rounds + 1):
            progress.progress((r - 1) / rounds, text=f"Round {r} of {rounds}: homes are training")
            fed.step()
            chart_slot.altair_chart(error_chart(fed.history), width="stretch")
            grid_slot.altair_chart(decision_grid(fed.decisions), width="stretch")
        progress.empty()
        fed.run_id = datetime.now().strftime("run-%Y%m%d-%H%M%S")
        st.session_state.fed = fed
        st.rerun()

    fed = st.session_state.get("fed")
    if fed is not None:
        show_summary(fed)
        st.altair_chart(error_chart(fed.history), width="stretch")
        st.markdown("**Every decision GridGuard made** (hover a square to compare with the truth)")
        st.caption("OK benign · CH genuine change (accepted at half weight) · FX meter fault (quarantined) · AT attack (rejected) · ? unsure (held back) · SIG bad signature (rejected)")
        st.altair_chart(decision_grid(fed.decisions), width="stretch")
        trust = pd.DataFrame([{"home": cid, **t} for cid, t in fed.trust.items()]).set_index("home")
        st.markdown("**Trust scores after training**")
        st.dataframe(trust, column_config={c: st.column_config.ProgressColumn(c, min_value=0.0, max_value=1.0, format="%.2f") for c in trust.columns})
        save_left, save_right = st.columns(2)
        if save_left.button("Save run to MongoDB", icon=":material/database:"):
            try:
                gg.save_to_mongo(fed, fed.run_id)
                st.success(f"Saved {fed.run_id} to the gridguard.runs collection")
            except Exception as error:
                st.error(f"MongoDB not reachable: {error}")
        if save_right.button("Upload run to AWS S3", icon=":material/cloud_upload:"):
            if not gg.S3_BUCKET:
                st.warning("Set the S3_BUCKET environment variable and run `aws configure` first.")
            else:
                try:
                    st.success(f"Uploaded to {gg.upload_to_s3(fed, fed.run_id)}")
                except Exception as error:
                    st.error(f"Upload failed: {error}")


with tab_chain:
    fed = st.session_state.get("fed")
    if fed is None:
        st.info("Train the federation first; every decision it makes is written here.")
    else:
        st.subheader("A tamper-proof record of every decision")
        st.write("Each record stores the fingerprint (SHA-256 hash) of the record before it. Change anything in an old record and every fingerprint after it stops matching, so the edit is caught.")
        target = st.number_input("Record to secretly edit", 0, len(fed.log.records) - 1, 3)
        a, b = st.columns(2)
        if a.button("Secretly flip its decision", icon=":material/edit:"):
            entry = fed.log.records[target]["entry"]
            entry["cause"] = "malicious" if entry["cause"] == "benign" else "benign"
        if b.button("Undo all edits", icon=":material/undo:"):
            for record, decision in zip(fed.log.records, fed.decisions):
                record["entry"]["cause"] = decision["cause"]
        broken = fed.log.first_broken()
        if broken is None:
            st.success("Chain verified: every record matches its fingerprint.")
        else:
            st.error(f"Tampering detected at record {broken}. Everything from here on can no longer be trusted.")
        for record in fed.log.records[max(0, target - 2) : target + 4]:
            bad = broken is not None and record["index"] >= broken
            e = record["entry"]
            st.markdown(
                f"<div class='block {'broken' if bad else ''}'>#{record['index']} · round {e['round']} · {e['client']} · {e['cause']} → {e['action']}"
                f"<br>previous {record['previous'][:24]}… · this {record['hash'][:24]}…</div>",
                unsafe_allow_html=True,
            )


@st.cache_resource
def mongo():
    from pymongo import MongoClient

    return MongoClient(gg.MONGO_URI, serverSelectionTimeoutMS=1500).gridguard


with tab_live:
    st.subheader("Real-time meters through MQTT, Node-RED and MongoDB")
    st.write("Start the broker and Node-RED with `docker compose up -d --build`, then the meters with `python gridguard.py meters`. Use the buttons to break a meter or add an EV and watch Node-RED flag it.")
    meter_id = st.selectbox("Meter", [f"MTR-{i:02d}" for i in range(5)])
    buttons = st.columns(6)
    for column, (label, mode) in zip(buttons, [("Normal", None), ("Stuck", "stuck"), ("Spikes", "spike"), ("Reversed", "reverse"), ("EV", "ev"), ("Solar", "solar")]):
        if column.button(label, width="stretch"):
            try:
                requests.post(f"{gg.NODE_RED_URL}/control", json={"meter_id": meter_id, "mode": mode}, timeout=3).raise_for_status()
                st.toast(f"{meter_id}: {label}")
            except requests.RequestException as error:
                st.error(f"Node-RED not reachable: {error}")

    @st.fragment(run_every=3)
    def live_view():
        try:
            db = mongo()
            rows = list(db.readings.find({"meter_id": meter_id}, {"_id": 0}).sort("ts", -1).limit(180))
            alerts = list(db.alerts.find({}, {"_id": 0}).sort("ts", -1).limit(8))
        except Exception as error:
            st.warning(f"MongoDB not reachable: {error}")
            return
        if not rows:
            st.info("No readings yet. Are Node-RED and the meters running?")
            return
        data = pd.DataFrame(rows)
        data["time"] = pd.to_datetime(data["ts"])
        latest = data.iloc[0]
        st.metric(f"{meter_id} right now", f"{latest['power_w']:.0f} W", help=", ".join(latest.get("flags") or []) or "no flags")
        chart = alt.Chart(data).mark_line(color="#2a78d6", strokeWidth=2).encode(
            x=alt.X("time:T", title=None), y=alt.Y("power_w:Q", title="power (W)"), tooltip=["time:T", "power_w:Q", "flags"]
        )
        st.altair_chart(chart.properties(height=280), width="stretch")
        if alerts:
            st.markdown("**Latest alerts from Node-RED**")
            st.dataframe(pd.DataFrame(alerts)[["ts", "meter_id", "flags", "power_w"]], hide_index=True, width="stretch")

    live_view()
