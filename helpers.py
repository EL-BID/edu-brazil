import requests
import pandas as pd


def osrm_table(origins, destinations):
    """
    This function returns the distance and duration between two points using the OSRM server.
    """

    size_origins = len(origins)
    size_destinations = len(destinations)

    # Concat the two dataframes
    coordinates = pd.concat([origins, destinations], axis=0)

    # Get the coordinates of the hexagons
    coordinates_param = ";".join(
        (coordinates["lon"].astype(str) + "," + coordinates["lat"].astype(str)).tolist()
    )

    # Create the url
    params = {
        "annotations": "distance,duration",
        "sources": ";".join([str(i) for i in range(size_origins)]),
        "destinations": ";".join(
            [str(i) for i in range(size_origins, size_origins + size_destinations)]
        ),
    }
    url = f"http://localhost:5000/table/v1/profile/{coordinates_param}"

    # Get the response
    response = requests.get(url, params=params)

    # Check if the response is valid
    if response.status_code == 200:
        # Extract the data
        data = response.json()
        # Extract the distance and duration
        distance = data["distances"]
        duration = data["durations"]
        # Return the distance and duration
        return distance, duration
    else:
        raise Exception("OSRM server error", response.status_code, response.text)
