import os
import json
import time
import uuid
import logging
import pika
import atlasopenmagic as atom

logging.basicConfig(level=logging.INFO, format="%(asctime)s [producer] %(message)s")
log = logging.getLogger(__name__)

RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST", "localhost")
LUMI = 36.6
SKIM = "exactly4lep"
RELEASE = "2025e-13tev-beta"

SAMPLE_DEFS = {
    "Data": {"dids": ["data"], "type": "data"},
    r"Background $Z,t\bar{t},t\bar{t}+V,VVV$": {
        "dids": [410470,410155,410218,410219,412043,
                 364243,364242,364246,364248,
                 700320,700321,700322,700323,700324,700325],
        "type": "mc"
    },
    r"Background $ZZ^{*}$": {"dids": [700600], "type": "mc"},
    r"Signal ($m_H$ = 125 GeV)": {
        "dids": [345060,346228,346310,346311,346312,346340,346341,346342],
        "type": "mc"
    },
}

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

def main():
    log.info("Loading release %s", RELEASE)
    atom.set_release(RELEASE)
    datasets = atom.build_dataset(SAMPLE_DEFS, skim=SKIM, protocol="https", cache=True)

    tasks = []
    for name, info in datasets.items():
        for url in info.get("list", []):
            tasks.append({
                "task_id": str(uuid.uuid4()),
                "sample_name": name,
                "sample_type": SAMPLE_DEFS[name]["type"],
                "file_url": url,
                "lumi": LUMI
            })

    total = len(tasks)
    log.info("Total tasks: %d", total)

    host = RABBITMQ_HOST
    conn = connect(host)   
    channel = conn.channel()

    channel.queue_declare(queue="tasks", durable=True)
    channel.queue_declare(queue="results", durable=True)
    channel.queue_declare(queue="control", durable=True)


    channel.queue_purge("tasks")
    channel.queue_purge("results")
    channel.queue_purge("control")

  
    channel.basic_publish(
        exchange="",
        routing_key="control",
        body=json.dumps({"total_tasks": total}),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    log.info("Sent control message: total_tasks=%d", total)


    for t in tasks:
        channel.basic_publish(
            exchange="",
            routing_key="tasks",
            body=json.dumps(t),
            properties=pika.BasicProperties(delivery_mode=2)
        )
    log.info("Published %d tasks", total)

    channel.basic_publish(
        exchange="",
        routing_key="results",
        body=json.dumps({"END": True}),
        properties=pika.BasicProperties(delivery_mode=2)
    )
    log.info("Sent END marker")

    conn.close()
    log.info("Producer finished.")

if __name__ == "__main__":
    main()