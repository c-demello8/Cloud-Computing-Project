This is my folder for my project on Higgs Boson Analysis, utilising Docker for containerization and scalable deployment.

Use the following commands
# For Inital Run
docker compose build

docker compose down -v

docker compose up --build --scale worker=4

# To see the produced graph
wait for completion, then Ctrl+C

docker run --rm \
  -v simonhanaprojectv2_results_vol:/results \
  -v "$(pwd)/results":/out \
  alpine sh -c "cp -r /results/. /out/"


```mermaid
flowchart LR

    subgraph Producers
        P1[Producer 1]
        P2[Producer 2]
        P3[Producer 3]
    end

    A[Aggregator]

    subgraph Workers
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
    end

    P1 --> A
    P2 --> A
    P3 --> A

    A --> W1
    A --> W2
    A --> W3
```



