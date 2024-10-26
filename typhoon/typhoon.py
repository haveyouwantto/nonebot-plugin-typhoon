import requests
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import io
from typing import List

import re

# Define the palette based on the typhoon classification
palette = {
    "TD": "green",  # Tropical Depression
    "TS": "blue",  # Tropical Storm
    "STS": "yellow",  # Severe Tropical Storm
    "TY": "darkorange",  # Typhoon
    "STY": "hotpink",  # Severe Typhoon
    "Super TY": "red",  # Super Typhoon
}


# Importing necessary type hinting
from typing import List, Optional


def extract_match(text):
    # Define the regex pattern
    pattern = r"\(([A-Za-z ]+)\)$"

    # Search for the pattern in the input text
    match = re.search(pattern, text)

    # If a match is found, return the captured group (the uppercase letter)
    if match:
        return match.group(1)
    return None  # Return None if there's no match


class Typhoon:
    def __init__(
        self,
        _id,
        name,
        issue,
        current,
        pre_typhoon=None,
        past=None,
        wind_range=None,
    ):
        self.id: str = _id
        self.name: str = name
        self.issue = issue
        self.current: TyphoonStatus = current
        self.pre_typhoon: List[TyphoonStatus] = (
            pre_typhoon if pre_typhoon is not None else []
        )
        self.past: List[TyphoonStatus] = past if past is not None else []
        self.wind_range = wind_range if wind_range is not None else []

    def __repr__(self):
        return (
            f"Typhoon(id={self.id!r}, name={self.name!r}, "
            f"current={self.current!r}, pre_typhoon={self.pre_typhoon!r}, "
            f"past={self.past!r}, "
            f"wind_range={self.wind_range!r})"
        )

    def __str__(self):
        return self.__repr__()


class TyphoonStatus:
    def __init__(
        self,
        latitude,
        longitude,
        cat=None,
        sus=None,
        gust=None,
        pressure=None,
        move_speed=None,
        forecast=None
    ):
        self.lat: float = latitude
        self.long: float = longitude
        self.cat: Optional[str] = cat
        self.sus: Optional[float] = sus
        self.gust: Optional[float] = gust
        self.pressure: Optional[float] = pressure
        self.forecast: Optional[TyphoonForecast] = forecast

    def __repr__(self):
        return (
            f"TyphoonStatus(lat={self.lat}, long={self.long}, "
            f"cat={self.cat!r}, sus={self.sus}, gust={self.gust}, "
            f"pressure={self.pressure},forecast={self.forecast})"
        )

    def __str__(self):
        return self.__repr__()


class TyphoonForecast:
    def __init__(self, hour, data):
        self.hour: float = hour
        self.data: TyphoonStatus = data

    def __repr__(self):
        return f"TyphoonForecast(hour={self.hour}, data={self.data!r})"

    def __str__(self):
        return self.__repr__()


class TyphoonAdapter:
    def get_typhoon_list(self) -> List["Typhoon"]:
        """Method to be overridden by adapters for fetching the list of typhoons."""
        raise NotImplementedError("This method should be overridden by subclasses")

    def get_typhoon(self, _id: str) -> "Typhoon":
        """Method to be overridden by adapters for fetching a specific typhoon by ID."""
        raise NotImplementedError("This method should be overridden by subclasses")


class CAdapter(TyphoonAdapter):
    BASE_URL = "https://data.istrongcloud.com/v2/data/complex/"

    def get_typhoon_list(self) -> List["Typhoon"]:
        # Fetch the list of typhoons from JMA API
        response = requests.get(f"{self.BASE_URL}currMerger.json")
        typhoon_list_data = response.json()

        # Create a list to hold Typhoon objects
        typhoon_list = []

        # Loop through each typhoon in the list and fetch its detailed data
        for ty in typhoon_list_data:

            # Create a Typhoon object using helper method
            typhoon = self.init_typhoon(ty)  # Reuse the get_typhoon method
            typhoon_list.append(typhoon)

        return typhoon_list

    def init_typhoon(self, ty) -> "Typhoon":
        # Fetch detailed typhoon data using JMA API
        typhoon_data = ty
        name = typhoon_data["ename"]
        current_status = TyphoonStatus(
            typhoon_data["points"][-1]["lat"],
            typhoon_data["points"][-1]["lng"],
            extract_match(typhoon_data["points"][-1]["strong"]),
            typhoon_data["points"][-1]["speed"],
            typhoon_data["points"][-1]["speed"],
            typhoon_data["points"][-1]["pressure"],
            typhoon_data["points"][-1]["move_speed"],
        )

        # Create a Typhoon object
        typhoon = Typhoon(
            typhoon_data["tfbh"], name, typhoon_data["end_time"], current_status
        )

        # Append wind range data
        typhoon.wind_range = [
            typhoon_data["points"][-1]["radius7"],
            typhoon_data["points"][-1]["radius7"],
        ]

        for point in typhoon_data["points"]:
            status = TyphoonStatus(
                    point["lat"],
                    point["lng"],
                    extract_match(point["strong"]),
                    point["speed"],
                    point["speed"],
                    point["pressure"],
                )
            typhoon.past.append(status)
            if point.get("forecast") is not None:
                status.forecast = []
                for forecast in point["forecast"]:
                    forecast_set = []
                    for point2 in forecast["points"]:
                        forecast_set.append(
                            TyphoonForecast(
                                point2["time"],
                                TyphoonStatus(
                                    point2["lat"],
                                    point2["lng"],
                                    extract_match(point2["strong"]),
                                    point2["speed"],
                                    point2["speed"],
                                    point2["pressure"],
                                ),
                            )
                        )
                    status.forecast.append(forecast_set)

        return typhoon

    def get_typhoon(self, _id):
        lst = self.get_typhoon_list()

        for ty in lst:
            if ty.id == _id:
                return ty


# Plot the typhoon tracks and wind ranges with forecasts
def plot_typhoons(typhoon: Typhoon, plt, ax):

    # Extract position and name for the typhoon
    lat, lon = typhoon.current.lat, typhoon.current.long  # Get latitude and longitude
    name = typhoon.name  # Get typhoon name

    # Get the classification of the typhoon (e.g., 'TD', 'TS', etc.)
    classification = typhoon.current.cat

    # Use the classification to get the corresponding color from the palette
    typhoon_color = palette.get(
        classification, "gray"
    )  # Default to gray if classification not found

    # Plot the typhoon's current position with its classification color
    ax.plot(lon, lat, marker="o", color=typhoon_color, markersize=8)

    # Add typhoon name near the position
    plt.text(lon, lat, name, fontsize=12, color="tab:red", ha="left")

    # Plot wind range if available
    gale = typhoon.wind_range[0]  # Get gale warning data for the northern half
    gale_south = typhoon.wind_range[1]  # Get gale warning data for the southern half

    radius_km_north = float(gale) / 111  # Convert distance to degrees (north half)
    radius_km_south = (
        float(gale_south) / 111
    )  # Convert distance to degrees (south half)

    if radius_km_north > 0:
        # Northern half wind range (0 to π)
        angles_north = np.linspace(
            0, np.pi, 100
        )  # Generate angles from 0 to pi (north half)
        x_vals_north = lon + radius_km_north * np.cos(
            angles_north
        )  # X-coordinates for the semi-circle
        y_vals_north = lat + radius_km_north * np.sin(
            angles_north
        )  # Y-coordinates for the semi-circle

        # Combine the semi-circle points with the center to close the polygon
        points_north = np.vstack(
            [np.column_stack([x_vals_north, y_vals_north]), [lon, lat]]
        )

        # Plot the filled semi-transparent northern half polygon
        semi_circle_north = Polygon(
            points_north, color="green", alpha=0.2, transform=ccrs.PlateCarree()
        )
        ax.add_patch(semi_circle_north)

    if radius_km_south > 0:
        # Southern half wind range (π to 2π)
        angles_south = np.linspace(
            np.pi, 2 * np.pi, 100
        )  # Generate angles from pi to 2*pi (south half)
        x_vals_south = lon + radius_km_south * np.cos(
            angles_south
        )  # X-coordinates for the semi-circle
        y_vals_south = lat + radius_km_south * np.sin(
            angles_south
        )  # Y-coordinates for the semi-circle

        # Combine the semi-circle points with the center to close the polygon
        points_south = np.vstack(
            [np.column_stack([x_vals_south, y_vals_south]), [lon, lat]]
        )

        # Plot the filled semi-transparent southern half polygon
        semi_circle_south = Polygon(
            points_south, color="green", alpha=0.2, transform=ccrs.PlateCarree()
        )
        ax.add_patch(semi_circle_south)

    # Plot the past path using the pastPath API data (assumed to be available)
    if typhoon.past:
        lat, lon = typhoon.past[0].lat, typhoon.past[0].long
        for point in typhoon.past:
            past_lat = point.lat  # Extract latitudes from past path data
            past_lon = point.long  # Extract longitudes from past path data

            # Plot the past path as a solid gray line
            ax.plot(
                [lon, past_lon],
                [lat, past_lat],
                color=palette.get(point.cat, "gray"),
                linestyle="-",
                linewidth=2,
            )
            # ax.plot(past_lon, past_lat, marker="x", color="black", markersize=6)

            lon, lat = past_lon, past_lat

            if point.forecast is not None:
                
                # Plot forecast tracks with dotted lines and markers using the palette

                for forecast_set in point.forecast:
                    lat2=lat
                    lon2=lon
                    for point2 in forecast_set:
                        forecast_lat = point2.data.lat  # Forecast latitude
                        forecast_lon = point2.data.long  # Forecast longitude
                        forecast_classification = point2.data.cat
                        # Get forecast classification (TD, TS, etc.)

                        forecast_color = palette.get(
                            forecast_classification, "gray"
                        )  # Get corresponding color for forecast classification

                        # Draw dotted line to forecast position
                        ax.plot(
                            [lon2, forecast_lon],
                            [lat2, forecast_lat],
                            linestyle=":",
                            color=forecast_color,
                            linewidth=1
                        )

                        # Plot marker for the forecast position
                        ax.plot(
                            forecast_lon, forecast_lat, marker="x", color=forecast_color, markersize=4
                        )

                        # plt.text(forecast_lon, forecast_lat, forecast.hour, fontsize=8, color="black", ha="left")

                        # Update current position for the next forecast point
                        lon2, lat2 = forecast_lon, forecast_lat



# Main function to run the whole process
async def realtime_summary():
    adapter = CAdapter()
    typhoon_list = adapter.get_typhoon_list()
    fig = plt.figure(figsize=(10, 6), dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Add map features
    ax.add_feature(cfeature.OCEAN, edgecolor="gray")

    # Set the extent (longitude: 100E-180E, latitude: 4N-60N)
    ax.set_extent([100, 180, 4, 50], crs=ccrs.PlateCarree())

    # Format gridlines
    gl = ax.gridlines(draw_labels=True, crs=ccrs.PlateCarree(), linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    ax.xaxis.set_major_formatter(LongitudeFormatter())

    for typhoon in typhoon_list:
        # Plot the typhoon data with forecasts and past path
        plot_typhoons(typhoon, plt, ax)

    plt.title("Typhoon Tracks | Issued " + typhoon_list[0].issue)

    tempfile = io.BytesIO()
    fig.savefig(tempfile, bbox_inches="tight", pad_inches=0.1)
    return tempfile


async def plot_typhoon(_id):
    adapter = CAdapter()
    typhoon = adapter.get_typhoon(_id)

    # Extract latitude and longitude for extent setting
    forecast_points = []

    for point in typhoon.past:
        if point.forecast is not None:
            for forecast_set in point.forecast:
                for point2 in forecast_set:
                    forecast_points.append(point2.data)

    lats = (
        [typhoon.current.lat + point / 111 for point in typhoon.wind_range]
        + [point.lat for point in typhoon.past]
        + [point.lat for point in forecast_points]
    )
    longs = (
        [typhoon.current.long + point / 111 for point in typhoon.wind_range]
        + [point.long for point in typhoon.past]
        + [point.long for point in forecast_points]
    )

    # Set the latitude and longitude range dynamically
    lat_range = [min(lats) - 2, max(lats) + 2]
    lon_range = [min(longs) - 2, max(longs) + 2]

    fig = plt.figure(figsize=(10, 6), dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Add map features
    ax.add_feature(cfeature.OCEAN, edgecolor="gray")

    # Set the extent (latitude and longitude limits)

    ax.set_extent(
        [lon_range[0], lon_range[1], lat_range[0], lat_range[1]], crs=ccrs.PlateCarree()
    )

    # Format gridlines
    gl = ax.gridlines(draw_labels=True, crs=ccrs.PlateCarree(), linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    ax.xaxis.set_major_formatter(LongitudeFormatter())

    # Plot the typhoon data with forecasts and past path
    plot_typhoons(typhoon, plt, ax)

    plt.title("Typhoon %s | Issued %s" % (typhoon.name, typhoon.issue))

    tempfile = io.BytesIO()
    fig.savefig(tempfile, bbox_inches="tight", pad_inches=0.1)
    return tempfile
