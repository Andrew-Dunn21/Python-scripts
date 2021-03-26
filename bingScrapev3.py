"""
Author: Andrew Dunn
Date: 11/19/2020
Spec:
This absolute unit was created to scrape the Bing Maps dataset to collect
overhead aerial imagery of international land borders for academic research.
THIS CODE WILL NOT RUN WITHOUT A COPY OF bingUtil.py IN THE SAME DIRECTORY!
Enjoy the spaghetti!
Version: 3.0

"""
import geopandas as gpd
import folium
import pandas as pd
import math
import sqlite3
import fiona
import sys
import requests
import subprocess
import os
import shutil
import json
from haversine import haversine, Unit
import time
from shapely.geometry import MultiPolygon, Polygon, LineString, MultiLineString
from bingUtilV2 import get_shape_line, fetch_key, handles, getCode, getCOW, buildList, \
     makeMove, innerMove, scrape, buildMList, rectScrape, odometer


#Create file objects to pass around
borderFile = gpd.read_file('Borders2/Int_Borders_version_2.shp')
bingKey = fetch_key('bing_key.txt')
csvCOW = pd.read_csv('cs_landborders_2017/cow-country-code.csv')
#Defining the constants:
imgSize = 1280 #Adjust this to scale the image
zoom = 16 #Also adjust this for scaling
step = 2 #Maybe turn this knob, too. It represents the distance between tile centers
exL = borderFile['geometry'][1] #LineString example
exM = borderFile['geometry'][0] #MultiLineString example
allLines = 319
#Handles:
lead, jpeg, json = handles(zoom, imgSize, bingKey)


#If there's an arg given, use it to get the correct shapeline
if len(sys.argv) == 1:
    #No arg means start from the start of the shapefile
    shapeLine = 0
elif len(sys.argv) == 3:
    shapeLine = get_shape_line(sys.argv[1], sys.argv[2], borderFile, csvCOW)
else:
    raise Exception("This isn't how this is supposed to go")


#Now we loop the countries in the shapefile and (try to) store the things:
for i in range(shapeLine, allLines):
    #Make the outer folder and move in
    makeMove(borderFile, i, csvCOW)
    #Get the list of points to scrape
    bQ = []
    print(getCOW(borderFile['LEFT_FID'][i], csvCOW)[1] + ', ' + getCOW(borderFile['RIGHT_FID'][i], csvCOW)[1])

    if type(borderFile['geometry'][i]) == type(exL):
        print("LineString path")
        bQ = buildList(borderFile, i)
    elif type(borderFile['geometry'][i]) == type(exM):
        print("MultiLineString path")
        bQ = buildMList(borderFile, i)
    #Make bQ good for scraping
    bQ = rectScrape(bQ, step)
    #reset the fileCount
    fileCount = 0
    #loop the points to scrape
    ##REWRITE THIE ISH TO WORK WITH THE NEW bQ FORMAT#####
    for j in range(len(bQ)):
        this = bQ[j]
        for k in range(len(this)):

            #Set up the inner folder
            hand = innerMove(borderFile, i, fileCount, csvCOW)
            #scrape each point, this guy does the heavy lifting
            # scrape(this[k], hand, lead, jpeg, json)
            #Stall for time so we don't make Bing mad again
            #time.sleep(5)
            #Increment fileCount
            fileCount += 1
            #Step out into the outer folder again
            os.chdir('..')
    #Step out again to start the next country
    os.chdir('..')

    if i == 3:
        raise Exception("Staaahp")
#Yay! We did it!

print("That's the whole planet  ¯\_(ツ)_/¯")
