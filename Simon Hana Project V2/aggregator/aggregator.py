import os
import json
import time
import logging
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import AutoMinorLocator
import pika

logging.basicConfig(level=logging.INFO, format="%(asctime)s [aggregator] %(message)s")
log = logging.getLogger(__name__)
 # Basic properties for the graph
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
NBINS = 68
XLO, XHI, BW = 80, 250, 2.5
SAMPLE_COLORS = {
    "Data": "black",
    r"Background $Z,t\bar{t},t\bar{t}+V,VVV$": "#6b59d3",
    r"Background $ZZ^{*}$": "#ff0000",
    r"Signal ($m_H$ = 125 GeV)": "#00cdff",
}



# had to make sure that the connect would retry as previous versions would just give up
def connect(host):
    credentials = pika.PlainCredentials('user', 'password')
    for i in range(15):
        try:
            conn = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=host,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
            )
            log.info("Connected to RabbitMQ")
            return conn
        except Exception as e:
            log.warning("retry %d: %s", i+1, e)
            time.sleep(5)
    raise RuntimeError("Cannot connect to RabbitMQ")

def significance(hists):
    sig_name = r"Signal ($m_H$ = 125 GeV)"
    bg_names = [k for k in hists if k != "Data" and "Signal" not in k]
    mc_tot = sum(hists[k] for k in bg_names)
    n_sig = hists[sig_name][17:20].sum() + mc_tot[17:20].sum()
    n_bg = mc_tot[17:20].sum()
    sig = n_sig / np.sqrt(n_bg + 0.3 * n_bg**2) if n_bg > 0 else 0.0
    log.info("n_sig=%.2f  n_bg=%.2f  sig=%.3f", n_sig, n_bg, sig)
    return n_sig, n_bg, sig

def make_plot(hists, path):
    edges = np.arange(XLO, XHI + BW, BW)
    cx = edges[:-1] + BW/2

    fig, ax = plt.subplots(figsize=(12, 8))
    data_y = hists["Data"]
    ax.errorbar(cx, data_y, yerr=np.sqrt(data_y), fmt="ko", ms=4, label="Data", zorder=5)

    bg_names = [k for k in hists if k != "Data" and "Signal" not in k]
    mc_x = [hists[k] for k in bg_names]
    mc_cols = [SAMPLE_COLORS[k] for k in bg_names]
    mc_h = ax.hist([cx]*len(mc_x), bins=edges, weights=mc_x,
                   stacked=True, color=mc_cols, label=bg_names)
    mc_tot = mc_h[0][-1]

    mc_err = np.sqrt(sum(hists[k]**2 for k in bg_names))
    ax.bar(cx, 2*mc_err, bottom=mc_tot - mc_err, width=BW,
           color="none", hatch="////", alpha=0.5, label="Stat. Unc.")

    sig_name = r"Signal ($m_H$ = 125 GeV)"
    ax.hist(cx, bins=edges, weights=hists[sig_name], bottom=mc_tot,
            color=SAMPLE_COLORS[sig_name], label=sig_name)

    ax.set_xlim(XLO, XHI)
    ax.set_ylim(bottom=0)
    ax.xaxis.set_minor_locator(AutoMinorLocator())
    ax.yaxis.set_minor_locator(AutoMinorLocator())
    ax.tick_params(which="both", direction="in", top=True, right=True)
    ax.set_xlabel(r"4-lepton invariant mass $m_{4\ell}$ [GeV]", fontsize=13, x=1, ha="right")
    ax.set_ylabel(f"Events / {BW} GeV", y=1, ha="right")

    for y, s, kw in [
        (0.95, "ATLAS Open Data", {"fontsize":14}),
        (0.89, "for education", {"fontsize":11,"style":"italic"}),
        (0.83, r"$\sqrt{s}=13\ \mathrm{TeV},\ \int\mathcal{L}\,dt=36.6\ \mathrm{fb}^{-1}$", {"fontsize":12}),
        (0.77, r"$H \rightarrow ZZ^* \rightarrow 4\ell$", {"fontsize":13}),
    ]:
        ax.text(0.05, y, s, transform=ax.transAxes, va="top", **kw)

    ax.legend(frameon=False, fontsize=10, loc="upper right")
    plt.tight_layout()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()
    log.info("Plot saved: %s", path)

def main():
    host = RABBITMQ_HOST
    conn = connect(host)   
    channel = conn.channel()

    # Declare queues
    channel.queue_declare(queue="tasks", durable=True)
    channel.queue_declare(queue="results", durable=True)
    channel.queue_declare(queue="control", durable=True)

    log.info("Waiting for control message...")
    total_tasks = None
    while total_tasks is None:
        method, props, body = channel.basic_get(queue="control", auto_ack=True)
        if body:
            msg = json.loads(body)
            total_tasks = msg.get("total_tasks")
    log.info("Expecting %d results", total_tasks)

    hists = {k: np.zeros(NBINS) for k in SAMPLE_COLORS}
    received = 0
    while received < total_tasks:
        method, props, body = channel.basic_get(queue="results", auto_ack=True)
        if body:
            msg = json.loads(body)
            if msg.get("END"):
                continue
            name = msg["sample_name"]
            hists[name] += np.array(msg["hist_values"])
            received += 1
            if received % 10 == 0:
                log.info("Progress: %d/%d", received, total_tasks)
        else:
            time.sleep(0.2)

    log.info("All results collected.")
    n_sig, n_bg, sig = significance(hists)

    outdir = os.environ.get("RESULTS_DIR", "/results")
    os.makedirs(outdir, exist_ok=True)
    with open(f"{outdir}/significance.txt", "w") as f:
        f.write(f"n_sig = {n_sig:.2f}\nn_bg  = {n_bg:.2f}\nsig   = {sig:.3f} sigma\n")
    make_plot(hists, f"{outdir}/HZZ_invariant_mass.png")

    conn.close()

if __name__ == "__main__":
    main()