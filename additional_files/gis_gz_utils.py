#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Set of tools for writing and visualizing files"""

__author__ = 'Joram Schito'
__copyright__ = 'Copyright 2017, ETH Zurich'
__credits__ = 'Joram Schito'
__license__ = 'ETH Zurich'
__version__ = '3.0.2'
__maintainer__ = 'Joram Schito'
__email__ = 'joram@joramschito.ch'
__status__ = 'Development'

import os
import sys
import csv
import json
import re
import math
import psycopg2
import numpy as np
import fiona
import rasterio
import matplotlib.pyplot as plt
from fiona.crs import from_epsg
import geopandas
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.crs import CRS
from rasterio.mask import mask
from pyproj import Proj, transform
from shapely.geometry import mapping, shape, Point
from collections import OrderedDict
from pprint import pprint


def show_raster(array_1, array_2):
    """
    Visualizes two rasters next to each other
    :param array_1: The raster that should be displayed on the left
    :param array_2: The raster that should be displayed on the right
    :return:
    """

    # Create a figure with one row and two columns
    fig = plt.figure(figsize=(1, 2))

    # Add a first subplot on the left
    fig.add_subplot(121)
    plt.imshow(array_1)

    # Add another subplot on the right
    fig.add_subplot(122)
    plt.imshow(array_2)

    # Show the plot and return
    plt.show()
    return


def show_points(df):
    """
    Shows the points passed with the data frame
    :param df: The data frame that contains the points that should be visualized
    :return:
    """

    # Plot the district map
    district_map = geopandas.read_file('data\\stadtkreis.json')
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.set_aspect('equal')
    district_map.plot(ax=ax, color='white', edgecolor='black')

    # Translate the points from the dataframe to Point objects, import them to a geodataframe with LV95 as source
    # CRS, project the geodataframe to WGS84 and display it
    geometry = [Point(xy) for xy in zip(df['X_LV95'], df['Y_LV95'])]
    gdf = geopandas.GeoDataFrame(df, geometry=geometry, crs={'init': 'epsg:2056'})
    gdf = gdf.to_crs({'init': 'epsg:4326'})
    gdf.plot(ax=ax, color='red')

    # Show the whole plot and return
    plt.draw()
    """plt.pause(0.3)
    plt.close()"""
    return


def project_vector(src_path, tgt_path, src=None, tgt_crs=None, tgt_schema=None):
    """
    Project a fiona object to a specific CRS and save it to the file specified in the passed arguments
    :param src_path: The path to the source vector file
    :param tgt_path: The path of the target file, including the ending. The driver is selected in this function
    :param src: If provided, take the source Fiona object which has been already opened by another function
    :param tgt_crs: The target CRS. If not defined, the projected CRS defined in the config file is chosen.
    :param tgt_schema: The target schema that should be used in the target file (take source scheme if None)
    :return:
    """

    print('Operating:')
    print(tgt_path)

    # Open a Fiona object if it has not been passed
    close_vector_file = False
    if src is None:
        src = fiona.open(src_path)
        close_vector_file = True

    # Define the target CRS: If sth is passed, take it. If nothing is passed, take the projected CRS from config file
    if tgt_crs is None:
        tgt_crs = const.crs_projected

    # Define the scheme: If something is passed, take it as it is. If nothing is passed, take the source schema.
    if tgt_schema is None:
        tgt_schema = src.schema

    # Define the projection
    in_proj = Proj(init=src.crs['init'])
    out_proj = Proj(init=tgt_crs['init'])
    out_proj_epsg_number = int(tgt_crs['init'].rsplit(':')[1])

    # Derive the driver from the output file ending
    file_ending = '.' + tgt_path.rsplit('.')[-1]
    tgt_driver = const.fiona_drivers[file_ending]

    # Delete the target file if it already exists
    if os.path.exists(tgt_path):
        os.remove(tgt_path)

    # Open the target file and iterate through the entries while creating an inner and an outer list per row (i)
    # NOTE that crs=from_epsg()... is most robust
    with fiona.open(tgt_path,
                    'w',
                    driver=tgt_driver,
                    crs=from_epsg(out_proj_epsg_number),
                    schema=tgt_schema,
                    encoding='utf-8'
                    ) as tgt:
        for i in src:
            # The following levels of nested lists are possible:
            # * 0 for 'Point'
            # * 1 for 'LineString', 'MultiPoint'
            # * 2 for 'Polygon', 'MultiLineString'
            # * 3 for 'MultiPolygon'

            # First, open an empty record that should be written to the file in the end
            record = []

            # Level 0
            if i['geometry']['type'] == 'Point':
                # print("in level 0")
                # Retrieve the x and y coordinate and if it exists, also the z coordinate, transform them and
                # append them to the same list structure as we iterated through
                (x, y, *z) = i['geometry']['coordinates']
                (x2, y2) = transform(in_proj, out_proj, x, y)
                record = (x2, y2, *z)

            # Level 1
            if i['geometry']['type'] == 'LineString' or i['geometry']['type'] == 'MultiPoint':
                # print("in level 1")
                for level_1 in i['geometry']['coordinates']:
                    (x, y, *z) = level_1
                    (x2, y2) = transform(in_proj, out_proj, x, y)
                    record.append((x2, y2, *z))

            # Level 2
            if i['geometry']['type'] == 'Polygon' or i['geometry']['type'] == 'MultiLineString':
                # print("in level 2")
                for level_1 in i['geometry']['coordinates']:
                    level_2_list = []
                    for level_2 in level_1:
                        (x, y, *z) = level_2
                        (x2, y2) = transform(in_proj, out_proj, x, y)
                        level_2_list.append((x2, y2, *z))
                    record.append(level_2_list)

            # Level 3
            if i['geometry']['type'] == 'MultiPolygon':
                # print("in level 3")
                for level_1 in i['geometry']['coordinates']:
                    level_2_list = []
                    for level_2 in level_1:
                        level_3_list = []
                        for level_3 in level_2:
                            (x, y, *z) = level_3
                            (x2, y2) = transform(in_proj, out_proj, x, y)
                            level_3_list.append((x2, y2, *z))
                        level_2_list.append(level_3_list)
                    record.append(level_2_list)

            # Write the new coordinates to the record
            i['geometry']['coordinates'] = record
            tgt.write(i)

    # Close the Fiona object, if it has been opened within this function
    if close_vector_file:
        src.close()

    return


def write_array_to_raster_with_blueprint(array, blueprint_raster, out_path):
    """
    Write an array to a blueprint raster.
    NOTE: The array must have the same dimensions as the blueprint raster.
    :param ndarray array: The array containing the data to be written into the bluepront raster
    :param str blueprint_raster: The full path to the blueprint raster
    :param str out_path: The full output path including the TIFF ending
    :return: nothing as a file is written
    """

    with rasterio.open(blueprint_raster, 'r', driver='GTiff') as src:
        profile = src.profile
        profile['nodata'] = const.no_data_value_negative
        profile['dtype'] = str(array.dtype)  # determine the dtype of the array
        profile['compress'] = 'lzw'

    # Write the array to the raster
    with rasterio.open(out_path, 'w', **profile) as dst:
        dst.write(array.astype(profile['dtype']), 1)
        dst.write_mask(True)

    return


def write_dicts_to_csv(full_path, header_row, *args):
    """
    Writes the dictionaries passed to a one-row csv with * columns
    NOTE: Check https://stackoverflow.com/questions/39757609/write-multiple-rows-from-dict-using-csv
    :param string full_path: full path to the target csv including the format .csv
    :param boolean header_row: True or False: Should a header be written?
    :param dict, list args: dict or list of dict that should be written into a column. Format: {'header': value}
    :return: Nothing. This function writes a csv file depending on the arguments passed.
    """

    # Create a general dictionary from the passed arguments
    general_dict = {}
    for element in args:

        # Distinguish between lists of dicts and regular, single dicts.
        # Consider the arguments passed as dicts nested in a list
        if type(element) == list:
            for list_element in element:
                for key, value in list_element.items():
                    general_dict[key] = value

        # Consider the arguments passed as single dictionaries
        else:
            for key, value in element.items():
                general_dict[key] = value

    # Order the dictionary elements alphabetically
    ordered_dict = OrderedDict(sorted(general_dict.items(), key=lambda t: t[0]))

    # Create a CSV and write the passed arguments into one row including a header
    with open(full_path, 'w') as csv_file:
        writer = csv.DictWriter(csv_file,
                                fieldnames=ordered_dict.keys(),
                                delimiter=str(const.csv_separator),
                                lineterminator='\n'
                                )
        if header_row:
            writer.writeheader()
        writer.writerow(ordered_dict)

    return


def write_geometries_to_files(shapely_objects, out_path, blueprint=None, properties_schema=None,
                              properties_entries=None):
    """
    Writes shapely objects to an output file with the same properties for each row. Replaces write_vector_file()
    :param list shapely_objects: The dictionary containing all shapely objects
    :param out_path: The output path including the target file ending
    :param blueprint: The path to a blueprint shapefile. Remember that the schemes should be the same across all files
    :param dict properties_schema: The attribute scheme that must be written into the output. If the same schema as the
    blueprint should be used, then pass it here separately
    :param dict properties_entries: The properties that should be written into the output file
    :return: Nothing, as files are generated
    """

    # Check, whether the properties_entries have a subdictionary. If so, raise an Exception, as this is not implemented
    # yet.
    try:
        properties_have_subdictionary = isinstance(type(properties_entries.values()), dict)
    except AttributeError:
        properties_have_subdictionary = False

    if properties_have_subdictionary:
        raise Exception('***ERROR!!! A dictionary with many properties has been passed while this function is only '
                        'capable to write one property for all rows at the same time. Thus, reconsider the lower '
                        'part of this function.')

    # Check whether a schema and properties have been passed and write the information into two dictionaries
    if (properties_schema is None) or (properties_entries is None):
        new_schemes = dict()
        new_entries = dict()
    else:
        new_schemes = properties_schema
        new_entries = properties_entries

    # INFO: in_object must be a Shapely geometry object (LineString, Point, MultiPoint, etc.)
    # NOTE that all geometry objects must be of the same type!!!
    # Determine the geometry type and define the target schema (crs is passed as an argument)
    geometry = shapely_objects[0].geometryType()
    target_schema = {'properties': new_schemes,
                     'geometry': geometry}

    # If a blueprint file has been passed, retrieve its driver and CRS
    if blueprint:
        # Open a blueprint vector file and edit the profile. Set the driver according to the output path ending
        blueprint = fiona.open(blueprint, 'r')
        driver = blueprint.driver
        crs = blueprint.crs
        # crs = from_epsg(const.crs_projected_epsg)
    else:
        driver = const.fiona_drivers['.{}'.format(out_path.rsplit('.')[-1])]
        crs = from_epsg(const.crs_projected_epsg)

    # Write the objects to an output file
    with fiona.open(out_path, 'w', driver=driver, schema=target_schema, crs=crs, encoding='utf-8') as dst:
        for i in shapely_objects:
            rec = dict()
            rec['geometry'] = mapping(i)
            rec['properties'] = new_entries
            dst.write(rec)

    # If a blueprint has been opened, close it again.
    if blueprint:
        blueprint.close()

    if const.working_device == 'pc':
        print('GeoJSON file written.')

    return


def write_multipoint_to_csv(out_path, list_with_dicts):
    """
    Write a multipoint object to a CSV. Note that either a file or a MultiPoint object can be provided.
    :param out_path: The full output path in which the CSV should be written
    :param list_with_dicts: A list with dictionaries that are written to a CSV by using csv.DictWriter
    :return:
    """

    # Last step: Write the rows to a CSV
    with open(out_path, 'w') as csv_file:
        writer = csv.DictWriter(csv_file,
                                fieldnames=list_with_dicts[0].keys(),
                                delimiter=str(const.csv_separator),
                                lineterminator='\n'
                                )
        writer.writeheader()
        for entry in list_with_dicts:
            writer.writerow(entry)

    return


def write_something_to_textfile(destination_folder, file_name, txt_content):
    """
    Writes a text content to a text file.
    :param string destination_folder: The path to the destination folder
    :param string file_name: The file name including the target format
    :param string txt_content: The text content to be written into the text file
    """

    file_name_with_ending = str(file_name)
    full_path = os.path.join(destination_folder, file_name_with_ending)
    if os.path.exists(full_path):
        try:
            os.chmod(full_path, 0o777)
        except:
            print('ERROR!!! There was a problem with changing the permissions.')
    text_file = open(full_path, 'w')
    text_file.write(str(txt_content))
    text_file.close()


def main():
    in_path = os.path.join(os.path.dirname(__file__), "restricted_areas.json")
    print(in_path)

    with fiona.open(in_path, 'r') as src:
        crs = src.crs
        driver = src.driver
        schema = src.schema
        '''print(crs)
        print(driver)
        print(schema)
        exit()'''
        '''print(src['properties'])
        print(src['geometry'])
        quit()'''

        for i in src:
            '''pprint (i['properties'])
            pprint (i['geometry']['type'])
            pprint (i['geometry']['coordinates'])'''

            """shapely_object = shape(i['geometry'])
            print(shapely_object.area)"""
            coordinates = i['geometry']['coordinates']
            #print(coordinates)

            for j in coordinates:
                print(j)

                for k in j:
                    for l in k:
                        print(l)

        p1 = Proj.crs
        p2 = Proj(init = 'epsg=4326')

        (x, y) = pyproj.transform(p1, p2, coordinates[0], coordinates[1])


def main_2():
    with rasterio.open('V:\\GIS_GZ\\joram\\CS.tif', 'r') as src:
        record = src.read()
        hello = src.profile.copy()
        hello['nodata'] = 9999
        with rasterio.open('V:\\GIS_GZ\\joram\\CS_copy.tif', 'w', **hello) as dst:
            dst.write(record)


if __name__ == '__main__':
    main()
