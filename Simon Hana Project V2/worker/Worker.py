import os
import json
import time
import logging
import traceback
import numpy as np
import uproot
import awkward as ak
import vector
import pika

logging.basicConfig(level=logging.INFO, format="%(asctime)s [worker] %(message)s")
log = logging.getLogger(__name__)


xlo, xhi, bw = 80, 250, 2.5
nbins = int((xhi - xlo) / bw)


base_vars = ["lep_pt", "lep_eta", "lep_phi", "lep_e", "lep_charge", "lep_type",
             "trigE", "trigM", "lep_isTrigMatched", "lep_isLooseID",
             "lep_isMediumID", "lep_isLooseIso"]


mc_vars = ["filteff", "kfac", "xsec", "mcWeight",
           "ScaleFactor_PILEUP", "ScaleFactor_ELE",
           "ScaleFactor_MUON", "ScaleFactor_LepTRIGGER",
           "sum_of_weights"]


def avail(keys, want):
    return [k for k in want if k in keys]


def run_file(url, mc, lumi):
    hist = np.zeros(nbins)
    nok = 0

    with uproot.open(url + ":analysis") as t:
        keys = t.keys()
        bvars = avail(keys, base_vars)
        wvars = avail(keys, mc_vars) if mc else []
        cols = list(set(bvars + wvars))

        if mc and "sum_of_weights" in wvars:
            sumw_global = t["sum_of_weights"].array()[0]   # scalar
        else:
            sumw_global = 1.0

        for ev in t.iterate(cols, library="ak", step_size=1000):
            # Trigger cuts
            if "trigE" in keys and "trigM" in keys:
                ev = ev[ev.trigE | ev.trigM]
            if not len(ev):
                continue

            if "lep_isTrigMatched" in keys:
                ev = ev[ak.sum(ev.lep_isTrigMatched, axis=1) >= 1]
            if not len(ev):
                continue

            ev = ev[ev["lep_pt"][:, 0] > 20]
            if not len(ev):
                continue
            ev = ev[ev["lep_pt"][:, 1] > 15]
            if not len(ev):
                continue
            ev = ev[ev["lep_pt"][:, 2] > 10]
            if not len(ev):
                continue

            if all(b in keys for b in ["lep_isLooseID", "lep_isMediumID", "lep_isLooseIso", "lep_type"]):
                pid = ev.lep_type
                eid = ev.lep_isLooseID
                mid = ev.lep_isMediumID
                iso = ev.lep_isLooseIso
                mask = ak.sum(((pid == 13) & mid & iso) | ((pid == 11) & eid & iso), axis=1) == 4
                ev = ev[mask]
            if not len(ev):
                continue

            lt = ev["lep_type"]
            fs = lt[:, 0] + lt[:, 1] + lt[:, 2] + lt[:, 3]
            ev = ev[(fs == 44) | (fs == 48) | (fs == 52)]
            if not len(ev):
                continue

            q = ev["lep_charge"]
            ev = ev[q[:, 0] + q[:, 1] + q[:, 2] + q[:, 3] == 0]
            if not len(ev):
                continue

            nok += len(ev)

            p = vector.zip({"pt": ev["lep_pt"][:, :4],
                            "eta": ev["lep_eta"][:, :4],
                            "phi": ev["lep_phi"][:, :4],
                            "E": ev["lep_e"][:, :4]})
            
            m = ak.to_numpy((p[:, 0] + p[:, 1] + p[:, 2] + p[:, 3]).M)

            # Weights
            if mc:
                # Global normalisation factor
                w = lumi * 1000.0 / sumw_global
                for var in ["filteff", "kfac", "xsec", "mcWeight",
                            "ScaleFactor_PILEUP", "ScaleFactor_ELE",
                            "ScaleFactor_MUON", "ScaleFactor_LepTRIGGER"]:
                    if var in wvars:
                        w = w * np.abs(ak.to_numpy(ev[var]).astype(float))
            else:
                w = np.ones(len(m))

            h, _ = np.histogram(m, bins=nbins, range=(xlo, xhi), weights=w)
            hist += h

    log.info("passed=%d  sum=%.2f", nok, hist.sum())
    return hist


def connect(host):
    credentials = pika.PlainCredentials('user', 'password')   
    for i in range(12):
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
    raise RuntimeError("Cannot reach RabbitMQ")



def main():
    host = os.environ.get("RABBITMQ_HOST", "localhost")
    conn = connect(host)
    channel = conn.channel()

    channel.queue_declare(queue="tasks", durable=True)
    channel.queue_declare(queue="results", durable=True)
    channel.basic_qos(prefetch_count=1)

    def callback(ch, method, properties, body):
        task = json.loads(body)
        mc = (task["sample_type"] == "mc")
        log.info("got %s | %s", task["task_id"][:8], task["sample_name"])

        try:
            hist = run_file(task["file_url"], mc, task["lumi"])
            out = {**task,
                "hist_values": hist.tolist(),
                "success": True,
                "error": None}
            
        except Exception:
            err = traceback.format_exc()
            log.error("failed:\n%s", err)
            out = {**task,
                "hist_values": np.zeros(nbins).tolist(),
                "success": False,
                "error": err}

        ch.basic_publish(exchange="",
                         routing_key="results",
                         body=json.dumps(out),
                         properties=pika.BasicProperties(delivery_mode=2))
        
        ch.basic_ack(method.delivery_tag)


    channel.basic_consume(queue="tasks", on_message_callback=callback)
    log.info("Waiting for tasks ...")
    channel.start_consuming()


if __name__ == "__main__":
    main()