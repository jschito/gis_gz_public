import os
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from pprint import pprint

# Define important paths
table = os.path.join('data', 'bfs_totale_bevoelkerung_kanton_zuerich_1981_2018.csv')
shapes = os.path.join('data', 'kanton_zuerich_gemeindegebiet.json')

# Read the data into Pandas and GeoPandas
geometries = gpd.read_file(shapes)
table_data = pd.read_table(table, encoding='latin-1', delimiter=';')

# Join the columns of the DataFrame to the GeoDataFrame and extract the area to a new column
df = geometries.merge(table_data, on='BFS_NUMMER')
df['area'] = df.geometry.area

# As duplicate entries for one BFS_NUMMER might exist (due to exclaves), sum up the areas
# for all rows that correspond to the same BFS_NUMMER
all_unique_bfs_nr = list(dict.fromkeys(df.BFS_NUMMER))
for bfs_nr in all_unique_bfs_nr:
    rows = df.loc[df.BFS_NUMMER == bfs_nr]
    number_of_rows = len(rows)
    if number_of_rows > 1:
        total_area = rows.area.sum()
        df.loc[df.BFS_NUMMER == bfs_nr, 'area'] = total_area

# Normalize the entries and store the normalized values to new columns named "normalized_{YEAR}"
year_columns = list(table_data.columns[2:])
for entry in year_columns:
    new_label = 'normalized_{}'.format(entry.rsplit('_')[-1])
    df[new_label] = df[entry] / df['area'] * 1000000

# Plot the results by using different classification methods and different numbers of classes
df.plot(scheme='fisher_jenks', column='normalized_2016', k=6, cmap='YlGn')

