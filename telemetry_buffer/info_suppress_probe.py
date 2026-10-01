"""Probe: escalation + recognition timeline on the DP replay (INFO-SUPPRESS-V1).

Runs one anchor-corner cell truncated at NUM_EPOCHS, records per-epoch
trigger_status, cumulative symptomatic (truth), quarantined count, and
recorded onsets. Answers: does outbreak_recognized (>= SUSPECTED) land,
and when, vs the record's day-12-14 news window.
"""
import json
import sys

REPO = "/home/ubuntu/repos/Crusher-to-the-Bridge"
sys.path.insert(0, REPO)

from picard_framework.covid_theta_fit import build_fit_run_spec, build_fit_sim  # noqa: E402

NUM_EPOCHS = 400
THETA = 2.37e11
SEED = 20200205
SCENARIO = "diamond_princess_2020"


def main() -> None:
    raw = build_fit_run_spec(SCENARIO, THETA, SEED, num_epochs=NUM_EPOCHS, repo_root=REPO)
    sim = build_fit_sim(raw, repo_root=REPO)
    sim.initialize()

    timeline = []
    for _ in range(NUM_EPOCHS):
        sim.step()
        st = sim.state
        n_symp = len(st.ever_ill_ids)
        n_q = len(st.quarantined_ids)
        n_rec_onsets = len(sim.modalities["syndromic"]._onset_observations)
        timeline.append({
            "epoch": sim.epoch,
            "day": round(sim.epoch / 24.0, 2),  # clock-exempt: epoch->day on the hourly clock
            "status": st.trigger_status,
            "ever_ill": n_symp,
            "quarantined": n_q,
            "conf_cases": len(st.cumulative_confirmed_case_ids),
            "rec_onsets": n_rec_onsets,
        })
        if st.escalation_log and st.escalation_log[-1]["epoch"] == sim.epoch:
            print("ESCALATION", st.escalation_log[-1])

    out = {
        "scenario": SCENARIO,
        "theta": THETA,
        "seed": SEED,
        "num_epochs": NUM_EPOCHS,
        "escalation_log": st.escalation_log,
        "timeline": timeline,
    }
    path = f"{REPO}/telemetry_buffer/info_suppress_probe_{SEED}.json"
    with open(path, "w") as f:
        json.dump(out, f, indent=1)
    print("wrote", path)
    # Print transitions and day-level summary
    prev = None
    for row in timeline:
        if row["status"] != prev:
            print(f"day {row['day']:>6} epoch {row['epoch']:>4} -> {row['status']} (ever_ill={row['ever_ill']}, q={row['quarantined']}, rec={row['rec_onsets']})")
            prev = row["status"]


if __name__ == "__main__":
    main()
