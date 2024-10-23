import requests
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
import numpy as np
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import io


# Define the palette based on the typhoon classification
palette = {
    'TD': 'limegreen',     # Tropical Depression
    'TS': 'blue',      # Tropical Storm
    'STS': 'yellow',   # Severe Tropical Storm
    'TY': 'darkorange',    # Typhoon
    'STY': 'violet',     # Severe Typhoon
    'SuperTY': 'red'   # Super Typhoon
}

def get_typhoon_list():
    response=requests.get("https://www.jma.go.jp/bosai/typhoon/data/targetTc.json")
    return response.json()

# Function to get the typhoon data from the JMA API
def get_typhoon_data(name):
    response = requests.get('https://www.jma.go.jp/bosai/typhoon/data/'+name+'/specifications.json')
    return response.json()

# Function to get the past path data from a hypothetical /pastPath API
def get_past_path_data(name):
    response = requests.get('https://www.jma.go.jp/bosai/typhoon/data/'+name+'/forecast.json')
    return response.json()

# Plot the typhoon tracks and wind ranges with forecasts
def plot_typhoons(name, plt, ax):
    typhoon_data = get_typhoon_data(name)
    past_path_data = get_past_path_data(name)
    
    # Extract typhoon data (example uses just one typhoon for clarity)
    typhoon = typhoon_data

    # Extract position and name for the typhoon
    lat, lon = typhoon[1]['position']['deg']  # Get latitude and longitude
    name = typhoon[0]['name']['en']  # Get typhoon name

    # Get the classification of the typhoon (e.g., 'TD', 'TS', etc.)
    classification = typhoon[1]['category']['en']

    # Use the classification to get the corresponding color from the palette
    typhoon_color = palette.get(classification, 'gray')  # Default to gray if classification not found

    # Plot the typhoon's current position with its classification color
    ax.plot(lon, lat, marker='o', color=typhoon_color, markersize=8)

    # Add typhoon name near the position
    plt.text(lon, lat, name, fontsize=12, color='tab:red', ha='left')

    # Plot wind range if available
    gale = typhoon[1]['galeWarning'][0]  # Get gale warning data for the northern half
    gale_south = typhoon[1]['galeWarning'][1]  # Get gale warning data for the southern half

    radius_km_north = float(gale.get('range', {}).get('km', 0)) / 111  # Convert distance to degrees (north half)
    radius_km_south = float(gale_south.get('range', {}).get('km', 0)) / 111  # Convert distance to degrees (south half)

    if radius_km_north > 0:
        # Northern half wind range (0 to π)
        angles_north = np.linspace(0, np.pi, 100)  # Generate angles from 0 to pi (north half)
        x_vals_north = lon + radius_km_north * np.cos(angles_north)  # X-coordinates for the semi-circle
        y_vals_north = lat + radius_km_north * np.sin(angles_north)  # Y-coordinates for the semi-circle
        
        # Combine the semi-circle points with the center to close the polygon
        points_north = np.vstack([np.column_stack([x_vals_north, y_vals_north]), [lon, lat]])
        
        # Plot the filled semi-transparent northern half polygon
        semi_circle_north = Polygon(points_north, color='green', alpha=0.2, transform=ccrs.PlateCarree())
        ax.add_patch(semi_circle_north)

    if radius_km_south > 0:
        # Southern half wind range (π to 2π)
        angles_south = np.linspace(np.pi, 2 * np.pi, 100)  # Generate angles from pi to 2*pi (south half)
        x_vals_south = lon + radius_km_south * np.cos(angles_south)  # X-coordinates for the semi-circle
        y_vals_south = lat + radius_km_south * np.sin(angles_south)  # Y-coordinates for the semi-circle
        
        # Combine the semi-circle points with the center to close the polygon
        points_south = np.vstack([np.column_stack([x_vals_south, y_vals_south]), [lon, lat]])
        
        # Plot the filled semi-transparent southern half polygon
        semi_circle_south = Polygon(points_south, color='green', alpha=0.2, transform=ccrs.PlateCarree())
        ax.add_patch(semi_circle_south)

    # Plot forecast tracks with dotted lines and markers using the palette
    forecast_points = typhoon[2:]
    for forecast in forecast_points:
        forecast_lat = forecast['position']['deg'][0]  # Forecast latitude
        forecast_lon = forecast['position']['deg'][1]  # Forecast longitude
        forecast_classification = forecast['category']['en']  # Get forecast classification (TD, TS, etc.)
        
        forecast_color = palette.get(forecast_classification, 'gray')  # Get corresponding color for forecast classification
        
        # Draw dotted line to forecast position
        ax.plot([lon, forecast_lon], [lat, forecast_lat], linestyle=':', color=forecast_color)
        
        # Plot marker for the forecast position
        ax.plot(forecast_lon, forecast_lat, marker='x', color=forecast_color, markersize=6)
        
        # Update current position for the next forecast point
        lon, lat = forecast_lon, forecast_lat

    # Plot the past path using the pastPath API data (assumed to be available)
    if past_path_data:
        typhoon_path = past_path_data[1]['track']["typhoon"]
        lat, lon = typhoon_path[0]
        for point in typhoon_path:
            past_lon = point[1]  # Extract longitudes from past path data
            past_lat = point[0]  # Extract latitudes from past path data
        
            # Plot the past path as a solid gray line
            ax.plot([lon,past_lon], [lat,past_lat], color='black', linestyle='-', linewidth=2)
            lon,lat=past_lon,past_lat
            
        pre_typhoon = past_path_data[1]['track']["preTyphoon"]
        lat, lon = pre_typhoon[0]
        for point in pre_typhoon:
            past_lon = point[1]  # Extract longitudes from past path data
            past_lat = point[0]  # Extract latitudes from past path data
        
            # Plot the past path as a solid gray line
            ax.plot([lon,past_lon], [lat,past_lat], color='black', linestyle=':', linewidth=2)
            lon,lat=past_lon,past_lat

    plt.title('Typhoon Tracks | Issued '+typhoon[0]['issue']['UTC'])

# Main function to run the whole process
async def realtime_summary():
    typhoon_list = get_typhoon_list()
    fig = plt.figure(figsize=(10, 6), dpi=300)
    ax = plt.axes(projection=ccrs.PlateCarree())

    # Add map features
    ax.add_feature(cfeature.COASTLINE)
    ax.add_feature(cfeature.OCEAN)
    ax.add_feature(cfeature.LAND, edgecolor='black')

    # Set the extent (longitude: 100E-180E, latitude: 4N-60N)
    ax.set_extent([100, 180, 4, 50], crs=ccrs.PlateCarree())

    # Format gridlines
    gl = ax.gridlines(draw_labels=True, crs=ccrs.PlateCarree(), linestyle="--")
    gl.top_labels = False
    gl.right_labels = False
    ax.xaxis.set_major_formatter(LongitudeFormatter())

    for typhoon in typhoon_list:
        # Plot the typhoon data with forecasts and past path
        plot_typhoons(typhoon['tropicalCyclone'], plt, ax)
     
    tempfile=io.BytesIO()
    fig.savefig(tempfile,bbox_inches='tight', pad_inches =0.1)
    return tempfile
