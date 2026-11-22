import torch

import gridguard as gg

NORMAL_UPDATE = {"size": 1.0, "direction": 0.5}


def evidence(frame):
    return gg.meter_evidence(frame["aggregate"].iloc[3 * gg.DAY :], frame["aggregate"].iloc[: 2 * gg.DAY])


def test_household_is_repeatable():
    assert gg.make_household(1, 2).equals(gg.make_household(1, 2))
    assert (gg.make_household(1, 2)["aggregate"] >= 0).all()


def test_detector_names_each_cause():
    home = gg.make_household(2, 5)
    assert gg.find_cause(evidence(home), NORMAL_UPDATE, 1.0) == "benign"
    for kind in ["spike", "stuck", "reverse"]:
        assert gg.find_cause(evidence(gg.add_event(home, kind, 3, 1)), NORMAL_UPDATE, 1.0) == "meter_fault"
    for kind in ["ev", "solar"]:
        assert gg.find_cause(evidence(gg.add_event(home, kind, 3, 1)), NORMAL_UPDATE, 1.0) == "genuine_change"
    assert gg.find_cause(evidence(home), {"size": 1.0, "direction": -0.5}, 1.0) == "malicious"


def test_flipped_update_points_the_wrong_way():
    updates = {f"c{i}": [torch.ones(10) + 0.1 * torch.randn(10)] for i in range(5)}
    updates["bad"] = [-5 * torch.ones(10)]
    info = gg.update_evidence(updates)
    assert info["bad"]["direction"] < 0 and info["bad"]["size"] > 3


def test_signature_and_audit_chain():
    key = gg.Ed25519PrivateKey.generate()
    update = [torch.ones(3)]
    signature = key.sign(gg.signed_message("house-01", 1, update, {"a": 1.0}))
    assert gg.signature_ok(key.public_key(), signature, gg.signed_message("house-01", 1, update, {"a": 1.0}))
    assert not gg.signature_ok(key.public_key(), signature, gg.signed_message("house-01", 1, [update[0] + 0.01], {"a": 1.0}))
    log = gg.AuditLog()
    for i in range(4):
        log.add({"round": i})
    assert log.first_broken() is None
    log.records[2]["entry"]["round"] = 99
    assert log.first_broken() == 2


def test_federation_round_blocks_attacker():
    scenario = {"house-01": ("attack: sign flip", 1), "house-02": ("attack: tampering", 1)}
    fed = gg.Federation(scenario, clients=6, rounds=1)
    causes = {d["client"]: (d["cause"], d["weight"]) for d in fed.step()}
    assert causes["house-01"] == ("malicious", 0.0)
    assert causes["house-02"] == ("bad_signature", 0.0)
    assert all(causes[h][1] > 0 for h in ["house-00", "house-03", "house-04", "house-05"])
    assert len(fed.history) == 2 and fed.log.first_broken() is None
