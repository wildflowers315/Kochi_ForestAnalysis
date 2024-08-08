''''''
# Analysis on Japanese Forest in Kochi Prefecture
''''''

# Import packages
import ee
import geemap
import zipfile
import os 
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import geopandas as gpd
import json

#%%
# Initialize Earth Engine
EE_PROJECT_ID = "my-project-423921" 
ee.Authenticate()
ee.Initialize(project=EE_PROJECT_ID)

#%%
# Download Kochi forest vector data from the following link to downloads folder and unzip it.
# https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A45.html

kochi_vector_data = 'A45-19_39_GML.zip'
downloads_folder = 'downloads'
zip_file_path = os.path.join(downloads_folder, kochi_vector_data)
print(zip_file_path)
extract_to_folder = downloads_folder

# # Only needed at the first time.
# with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
#     zip_ref.extractall(extract_to_folder)

#%%    

# List all files in the extracted folder
files = os.listdir(extract_to_folder)

# Find the GeoJSON or Shapefile
geojson_file = None
# shapefile = None

for file in files:
    if file.endswith('.geojson'):
        geojson_file = os.path.join(extract_to_folder, file)
        gdf_geojson = gpd.read_file(geojson_file)
        
    # elif file.endswith('.shp'):
    #     shapefile = os.path.join(extract_to_folder, file)
    #     gdf_shapefile = gpd.read_file(shapefile)

# Convert to JGD2011 CRS (EPSG:6668)
gdf_geojson = gdf_geojson.to_crs(epsg=6668)
# gdf_shapefile = gdf_shapefile.to_crs(epsg=6668)

# Define the column names + geometry
japanese_column_list = [
    "小班ID", "森林管理局", "森林管理署", "林班主番", "林班枝番", "小班主番", "小班枝番", 
    "局名称", "署名称", "小班名称", "林小班名称", "材積", "国有林名称", "県市町村名称", 
    "樹種1", "樹立林齢1", "最新林齢1", "樹種2", "樹立林齢2", "最新林齢2", "樹種3", 
    "樹立林齢3", "最新林齢3", "計画区名称", "林種の細分", "機能類型", "面積", 
    "保安林１", "保安林２", "保安林３", "保安林４", "保護林", "緑の回廊", 'geometry'
]

drop_columns = ["小班ID", "森林管理局", "森林管理署", "局名称", "署名称","林班枝番","小班名称", "林小班名称","最新林齢1", "最新林齢2", 
               "最新林齢3","保安林１", "保安林２", "保安林３", "保安林４", "保護林", "緑の回廊",]


# english_column_names = [
#     "Sub-compartment ID", "Forest Management Bureau", "Forest Management Office", 
#     "Main Forest Compartment Number", "Sub Forest Compartment Number", 
#     "Main Sub-compartment Number", "Sub-compartment Branch Number", 
#     "Bureau Name", "Office Name", "Sub-compartment Name", 
#     "Forest Sub-compartment Name", "Timber Volume", "National Forest Name", 
#     "Prefecture/City/Town Name", "Tree Species 1", "Established Forest Age 1", 
#     "Latest Forest Age 1", "Tree Species 2", "Established Forest Age 2", 
#     "Latest Forest Age 2", "Tree Species 3", "Established Forest Age 3", 
#     "Latest Forest Age 3", "Planning Area Name", "Subdivision of Forest Type", 
#     "Functional Type", "Area", "Protection Forest 1", "Protection Forest 2", 
#     "Protection Forest 3", "Protection Forest 4", "Conservation Forest", 
#     "Green Corridor", 'geometry'
# ]

# Apply the column names to the GeoDataFrame
gdf_geojson.columns = japanese_column_list
# gdf_shapefile.columns = english_column_names

gdf_geojson = gdf_geojson.drop(drop_columns, axis=1)
gdf_geojson['材積/ha'] = gdf_geojson['材積'] / gdf_geojson['面積']

columnUnique_dict = {col: gdf_geojson[col].unique() for col in gdf_geojson.columns}

print(gdf_geojson.head())
# print(gdf_shapefile.head())
print(gdf_geojson.shape)

print(gdf_geojson.loc[0])
# %%
# Visualization of polygon with Sentinel-2 RGB data.

gdf_geojson = gdf_geojson[gdf_geojson['計画区名称']=='安芸']
gdf_geojson = gdf_geojson[gdf_geojson['県市町村名称']=='北川村']


# Create a map
Map = geemap.Map()

# Convert the GeoDataFrame to a GeoJSON dictionary
geojson_dict = json.loads(gdf_geojson.to_json())

# Convert GeoJSON dictionary to Earth Engine FeatureCollection
ee_fc = geemap.geojson_to_ee(geojson_dict)

# Center the map on the FeatureCollection
Map.centerObject(ee_fc, 12)

# Add the GeoDataFrame to the map as a layer
Map.addLayer(ee_fc, {}, "GeoJSON Data")

# Add Sentinel-2 RGB data with cloud mask

# Define the parameters
# QA_BAND = 'cs'
# CLEAR_THRESHOLD = 0.60
# csPlus = ee.ImageCollection('GOOGLE/CLOUD_SCORE_PLUS/V1/S2_HARMONIZED')

# # Function to mask cloudy pixels based on the QA band
# def mask_clouds(image):
#     return image.updateMask(image.select(QA_BAND).gte(CLEAR_THRESHOLD))

# sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
#                 .filterBounds(ee_fc) \
#                 .filterDate('2021-01-01', '2021-12-31') \
#                 .map(lambda img: img.addBands(csPlus.filter(ee.Filter.equals('system:index', img.get('system:index'))).first())) \
#                 .map(mask_clouds) \
#                 .median().clip(ee_fc)

startDate = '2022-04-01'
endDate = '2022-11-01'
CLOUD_FILTER = 20
# CLD_PRB_THRESH = 50
# NIR_DRK_THRESH = 0.15
# CLD_PRJ_DIST = 1
# BUFFER = 50

sentinel2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
                .filterBounds(ee_fc) \
                .filterDate(startDate, endDate) \
                .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', CLOUD_FILTER)) \
                .median().clip(ee_fc)
                
rgb_params = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}
Map.addLayer(sentinel2, rgb_params, 'Sentinel-2 RGB')

# Save the map to an HTML file
Map.save('downloads/polygon_map.html')

#%%

# Plot the GeoDataFrame using Matplotlib

# Check for invalid geometries and drop them
gdf_geojson = gdf_geojson[gdf_geojson.is_valid]
gdf_geojson = gdf_geojson.dropna(subset=['geometry', '材積/ha'])

norm = mcolors.Normalize(vmin=gdf_geojson['材積/ha'].min(), vmax=gdf_geojson['材積/ha'].max())
cmap = plt.cm.Greens

fig, ax = plt.subplots(figsize=(10, 10))
# gdf_geojson.plot(ax=ax, color='blue', edgecolor='black')
gdf_geojson.plot(column='材積/ha', cmap=cmap, norm=norm, ax=ax, legend=True, legend_kwds={'label': "Timber Volumes /ha"})

ax.set_title('GeoJSON Data Visualization')
ax.set_xlabel('Longitude')
ax.set_ylabel('Latitude')

# # Set axis limits to avoid aspect ratio issues
# minx, miny, maxx, maxy = gdf_geojson.total_bounds
# ax.set_xlim(minx, maxx)
# ax.set_ylim(miny, maxy)

plt.show()