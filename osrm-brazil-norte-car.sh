#!/bin/bash

# exit when any command fails
set -e

# keep track of the last executed command
trap 'last_command=$current_command; current_command=$BASH_COMMAND' DEBUG
# echo an error message before exiting
trap 'if [[ $? -ne 0 ]]; then echo "\"${last_command}\" command failed with exit code $?."; fi' EXIT

# Process and run server command sequence
cd ~/data/osrm/south-america_brazil/norte
mkdir -p logs;
docker pull osrm/osrm-backend > $(pwd)/logs/car.txt;
# container 1 country 2 continent 3 profile 4
echo "Downloading osm data from geofabrik ... (1/5)"
# wget https://download.geofabrik.de/south-america/brazil/$2-latest.osm.pbf -a $(pwd)/logs/$4.txt;
echo "Done (1/5)"
echo "Running osrm extract process ... (2/5)"
docker run -t --name osrm_extract -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/norte-latest.osm.pbf >> $(pwd)/logs/car.txt ;
echo "Done (2/5)"
echo "Running osrm partition process ... (3/5)"
docker run -t --name osrm_partition -v $(pwd):/data osrm/osrm-backend osrm-partition /data/norte-latest.osm.pbf >> $(pwd)/logs/car.txt;
echo "Done (3/5)"
echo "Running osrm customize process ... (4/5)"
docker run -t --name osrm_customize -v $(pwd):/data osrm/osrm-backend osrm-customize /data/norte-latest.osm.pbf >> $(pwd)/logs/car.txt;
echo "Done (4/5)"
echo "Removing osrm processing containers ... (5/5)"
docker container rm osrm_extract osrm_partition osrm_customize >> $(pwd)/logs/car.txt;
echo "Done (5/5)"
echo "Starting osrm server ..."
CONTAINER_ID=$(docker run -d -t --name osrm_routing_server_south-america_brazil_norte_car -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/norte-latest.osm.pbf);
echo "Docker Container ID: ${CONTAINER_ID}"