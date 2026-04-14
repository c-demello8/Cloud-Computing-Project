Hi welcome to my project,

Hope you are having a good day.

You will find three different seperate folders, one with the producer, one with the aggregator and one with worker file.


Also a notebook, of the starting code and also the broken down code into the three sections :)

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

