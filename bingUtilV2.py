import geopandas as gpd
import pandas as pd
import math
import sqlite3
import folium
import fiona
import sys
import requests
import subprocess
import os
import shutil
import json
from shapely.geometry import MultiPolygon, Polygon, LineString, MultiLineString
from haversine import haversine, Unit
import time

def getCOW(ccode, file):
    """
    Pass in the country code, get back a tuple with the abbreviaton
    and the full country name as strings.

    Input:
        ccode: should be an int that is a country code
        file: the file object of the COW csv file
    Output:
        name: a tuple of a 3 letter abbreviation string and full name string for a country
    """

    size = 243
    name = ('not', 'found')
    #244 lines of fun to traverse:
    for i in range(size):
        if file['CCode'][i] == ccode:
            abr = file['StateAbb'][i]
            nme = file['StateNme'][i]
            name = (abr,nme)
    return name

def getCode(name, file):
    """
    Pass in the country name, get back the code.

    Input:
        name: the correctly spelled an capitalized country  name
        file: the file object of the COW csv file
    Output:
        name: a tuple of a 3 letter abbreviation string and full name string for a country
    """

    size = 243
    code = 0
    #244 lines of fun to traverse:
    for i in range(size):
        if file['StateNme'][i] == name:
            code = file['CCode'][i]
    return code

def get_shape_line(land1, land2, borderFile, cow):
    """
    Takes a couple of strings of country names and gives you
    back what line of the shapefile to start reading on

    Input:
        land1: Correctly spelled and capitalized country name
        land2: A different correctly spelled country name that has a
               land border in common with land1
        borderFile: the shapefile where the borders live
        cow: the Correlates of War csv file with all of the country codes
    Output:
        line: an int that represents the shapefile land border between
              land1 and land2
    """

    line = -1

    size = 319

    l1c = getCode(land1, cow)
    l2c = getCode(land2, cow)
    for i in range(size):
        if borderFile['LEFT_FID'][i] == l1c:
            if borderFile['RIGHT_FID'][i] == l2c:
                line = i
        if borderFile['LEFT_FID'][i] == l2c:
            if borderFile['RIGHT_FID'][i] == l1c:
                line = i
    if line < 0:
        raise Exception("Are you sure these two have a land border?")

    return line

def fetch_key(location):
    """
    You give fetch_key a file location and it gives you back
    the Bing Maps API key stored in a .txt file at that location.

    Input:
        location: a string containing the location of a .txt file
    Output:
        key: the Bing Maps API key stored in the file passed in
    """
    keyfile = open(location, 'r')
    key = keyfile.readline()

    return key

def handles(zoom, size, key):
    """
    This method takes input and generates the Bing Maps handles neeeded
    to fetch the data from Bing Maps.

    Inputs:
        zoom: an int, the zoom level of the image
        size: also an in, the size of a square tile
        key: a string, but this one is the API key
    Outputs:
        handle: a tuple of strings containing the lead, jpeg, and json handles
    """
    lead = "https://dev.virtualearth.net/REST/v1/Imagery/Map/Aerial/"
    jpeg = "/" + str(zoom) + "?mapSize=" + str(size) + "," + str(size) + "&mapMetadata=0&key=" + key
    json = "/" + str(zoom) + "?mapSize=" + str(size) + "," + str(size) + "&mapMetadata=1&key=" + key

    handle = (lead, jpeg, json)

    return handle

def buildMList(bf, line):
    """
    This method builds a single country queue of border to scrape.
    Adds flag points between border segments so we don't scrape ocean or
    other non-bordery spots.

    Inputs:
        bf: a file object with the border shapefile
        line: the current line of bf to scrape

    Output:
        bQ: a list of lists of tuples of lat/long pairs to scrape for border pics
    """
    #Get the border geometry
    mline = bf['geometry'][line]

    #Set up output
    bQ = []
    #Loop the geometry
    for j in range(len(mline)):
        #Get the coords of the next line segment
        bord = list(mline[j].coords)
        bQ_t = []
        for i in range(len(bord)):
            bQ_t.append(bord[i])
        bQ.append(bQ_t)
    return bQ

def buildList(bf, line):
    """
    This method builds a single country queue of border to scrape.
    Will return a flag if no border is present.
    Point format: (Lon, Lat)

    Inputs:
        bf: a file object with the border shapefile
        line: the current line of bf to scrape

    Output:
        bQ: a list of a list of tuples of lat/long pairs to scrape for border pics
    """
    #Get the border geometry
    bord = list(bf['geometry'][line].coords)

    #Set up output
    bQ = []
    bQ_0 = []
    #Loop the geometry
    for i in range(len(bord)):
        #Get the coords of the next line segment
        bQ_0.append(bord[i])
    #Put the list in the list
    bQ.append(bQ_0)
    return bQ

def makeMove(bf, line, cow):
    """
    Makes the directories for storing the data and creates a nametag .txt file

    Input:
        bf: the border shapefile
        line: where we are (for country names)
        cow: the COW csv file

    """
    #Time for a new naming scheme, reset fileCount
    country1 = getCOW(bf['LEFT_FID'][line], cow)
    country2 = getCOW(bf['RIGHT_FID'][line], cow)

    #Make and enter directory for this border
    outerFold = str(country1[0]).lower() + '-' + str(country2[0]).lower()
    subprocess.call(["mkdir", outerFold])
    os.chdir(outerFold)

    name = str(country1[1]) + '-' + str(country2[1]) + ".txt"
    nameFile = open(name, "w")
    nameFile.close()

    return

def innerMove(bf, line, count, cow):
    """
    Moves into an inner folder for data cleanliness

    Input:
         bf: the border shapefile
         line: what line we're on in the bf
         count: how many files have been made so far
    Output:
        outerFold: the name of the folder created. Handy to pass to scrape().

    """
    #Get the country names
    country1 = getCOW(bf['LEFT_FID'][line], cow)
    country2 = getCOW(bf['RIGHT_FID'][line], cow)
    num = str(count).zfill(4)

    #Make and enter directory for this border
    outerFold = str(country1[0]).lower() + '-' + str(country2[0]).lower() + '-' + num
    subprocess.call(["mkdir", outerFold])
    os.chdir(outerFold)

    return outerFold

def scrape(point, handle, lead, jpeg, json):
    """
    Does the scrape. Or tries to. If it can't, then it flags the file instead.

    Input:
        point: a tuple with the form (lat, long) for pinging Bing
        line: the current shapefile line, needed for names
        handle: the filename for the current directory
        lead: the lead handle
        jpeg: the jpeg tail
        json: the json tail
    """

    #Time to ping the Bing
    callLat = point[0]
    callLong = point[1]
    #Build the urls:
    url1 = lead + str(callLat) + ',' + str(callLong) + jpeg
    url2 = lead + str(callLat) + ',' + str(callLong) + json
    #Now the fancy part happens
    try:
        response1 = requests.get(url1, timeout=5)
        response2 = requests.get(url2, timeout=5)
        response1.raise_for_status()
        response2.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        print ("Http Error:",errh)
        fileE = open('ErrorH', "wb")
        fileE.write(url1 + '\n' + url2 + '\n' + errh)
    except requests.exceptions.ConnectionError as errc:
        print ("Error Connecting:",errc)
        fileE = open('ErrorC', "wb")
        fileE.write(url1 + '\n' + url2 + '\n' + errc)
    except requests.exceptions.Timeout as errt:
        print ("Timeout Error:",errt)
        fileE = open('ErrorT', "wb")
        fileE.write(url1 + '\n' + url2 + '\n' + errt)
    except requests.exceptions.RequestException as err:
        print ("Uh oh, something else went wrong",err)
        fileE = open('ErrorG', "wb")
        fileE.write(url1 + '\n' + url2 + '\n' + err)
    #Not actually a requests call, so it's safe
    response3 = str(callLat) + "," + str(callLong)

    #File names:
    header1 = handle + ".jpeg"
    header2 = handle + ".json"
    header3 = handle + ".txt"
    #Create files
    file1 = open(header1, "wb")
    file1.write(response1.content)
    file1.close()
    file2 = open(header2, "wb")
    file2.write(response2.content)
    file2.close()
    file3 = open(header3, "w")
    file3.write(response3)
    ##Collect URLs in case of bad status code to easily manually scrape
    if response1.status_code != 200 or response2.status_code != 200:
        file3.write("\n\n" + "jpeg url: " + url1)
        file3.write("\n\n" + "json url: " + url2)
    file3.close()
    #And we're done
    return

def rectScrape(list, step):
    """
    This one takes a list of all of the points on a border from a shapefile and
    makes it make sense for scraping by sampling spots along the border to [hopefully]
    minimize overlap between tiles.

    Input:
        list: the list of lists of points you started with
        step: the distance (in km) of the step size betwen tile centers

    Output:
        olist: the rectified list of lists that is *optimal* for a given step
    """
    olist = []

    #The loop that does the important things
    for i in range(len(list)):
        this = list[i]
        N = len(this)
        inlist = []
        for j in range(N-1):
            #The skip telltale is a "latitude" value > 400
            if this[j][0] > 400:
                continue
            here = this[j]
            next = this[j+1]
            dist = haversine(here, next, unit=Unit.KILOMETERS)
            if dist < step:
                inlist.append(here)
                jdx = inch(this,j,step)
                #Delete the stepped over points from consideration to trim
                for k in range(j,jdx):
                    this[k] = (404,404)
            else:
                #We have a long segment to scrape! Yay!
                strides = int(math.floor(dist/step)) #We'll add the end in the next pass
                #Establish segment deltas
                dx = (next[0] - here[0]) / strides
                dy = (next[1] - here[1]) / strides
                for j in range(strides):
                    #Add the first point
                    inlist.append(here)
                    #Unpack and step
                    x,y = here
                    x += dx
                    y += dy
                    here = (x,y)

        olist.append(inlist)
    rectCheck(olist, step)
    return olist


def inch(list, idx, step):
    """
    Takes a list of geographic points and keeps incrementing until the distance
    between two points is at least half of step. If it can't get past the distance,
    it returns the end of the list.

    Input:
        list: a list of (lat,lon) tuples of geographic points
        idx: the index of the place we're starting looking in the list
        step: how far apart tile centers are in an ideal world

    Output:
        kdx: the index of the endpoint in the original list

    """
    N = len(list)
    kdx = N-1
    #This threshold is for max coverage, sparser scrapes can be achieved by altering thresh
    thresh = step
    start = list[idx]
    for i in range(idx+1, N):
        end = list[i]
        dist = haversine(start, end, unit=Unit.KILOMETERS)
        if dist >= thresh:
            return i
    return kdx

##################################################################################
##DIAGNOSTIC#METHODS##############################################################
##################################################################################
def odometer(list):
    """
    Takes a list in and calculates the total distance.
    Like a car odometer.
    Get it?
    """
    N = len(list)
    sum = 0
    for i in range(N):
        this = list[i]
        n = len(this)
        for j in range(n-1):
            dist = haversine(this[j],this[j+1],unit=Unit.KILOMETERS)
            sum += dist
    sum = '{0:.4f}'.format(sum)
    print("The scrape length is " + str(sum) + " km")

def rectCheck(list, step):
    """
    Checks the rectified bQ for errorz
    """

    N = len(list)
    minT = step *.75
    maxT = step * 1.25
    bigFlags = 0
    smolFlags = 0
    flagsList = []

    for i in range(N):
        this = list[i]
        n = len(this)
        for j in range(n-1):
            dist = haversine(this[j], this[j+1],unit=Unit.KILOMETERS)

            if dist > maxT:
                dist = '{0:.4f}'.format(dist)
                # print("Distance of "+str(dist)+" km")
                flagsList.append((this[j],this[j+1]))
                bigFlags += 1
            elif dist < minT:
                dist = '{0:.4f}'.format(dist)
                # print("Distance of "+str(dist)+" km")
                flagsList.append((this[j],this[j+1]))
                smolFlags += 1
    print("There were " +str(bigFlags) + " points found with big dist.")
    print("There were " +str(smolFlags) + " points found with smol dist.")
    return flagsList, smolFlags, bigFlags


def formatTest(bf, csv):
    """
    This guy is just for printing out the entire shapefile in pairs and lengths
    for testing reasons, not actually used in scraping, but still kind of useful.
    """

    for i in range(319):
        left = getCOW(bf['LEFT_FID'][i], csv)[1]
        right = getCOW(bf['RIGHT_FID'][i], csv)[1]
        len = str(bf['Shape_Leng'][i])
        print("L: " + left + ' R: ' + right + " len: " + len)

    return

def delta_traverse(bf, idx, cow, out):
    """
    This figures out the haversine distance between the points in the shapefile and
    prints out some important diagnostic metrics like largest gap, smallest gap, and
    total length.

    Input:
        bf: the border shapefile
        idx: what line of the bf we're looking at presently
        cow: the Corellates of War csv file to get the country names
        out: the .txt file to write the output to
    """
    c1 = getCOW(bf['LEFT_FID'][idx], cow)
    c2 = getCOW(bf['RIGHT_FID'][idx], cow)
    geom = bf['geometry'][idx]
    totalLen = 0

    bigD = 0
    smolD = 1e10
    q = []

    if geom.geom_type == 'LineString':
        #String behavior
        x = list(geom.coords)
        for l in range(len(x)):
            q.append(x[l])
    elif geom.geom_type == 'MultiLineString':
        #Slightly more complex MString behavior
        for i in geom:
            x = list(i.coords)
            for k in range(len(x)):
                q.append(x[k])

    #Now we loop and crunch
    for j in range(len(q)):
        #Bail on the first run since there isn't a pred
        if j == 0:
            continue
        pred = q[j-1]
        cur = q[j]
        dist = haversine(pred, cur, unit=Unit.KILOMETERS)
        totalLen += dist
        if dist > bigD:
            bigD = dist
        if dist < smolD:
            smolD = dist

    bigD = '{0:.3f}'.format(bigD)
    smolD = '{0:.3f}'.format(smolD)
    totalLen = '{0:.3f}'.format(totalLen)
    avgLen = '{0:.3f}'.format(float(totalLen)/len(q))

    #Now we print some things out:
    sep = '\n~^~v~^~v~^~v~^~v~^~v~^~v~^~v~^~v~^~v\n'
    l1 = 'Border: ' + c1[1] + ', ' + c2[1] + '\n'
    l2 = 'Total points: ' + str(len(q)) + '\n'
    l3 = 'Largest gap: ' + str(bigD) + 'km' + '\n'
    l4 = 'Smallest gap: ' + str(smolD) + 'km' + '\n'
    l5 = 'Overall Length: ' + str(totalLen) + 'km' + '\n'
    l6 = 'Average gap: ' + str(avgLen) + 'km' + '\n'
    out.write(sep)
    out.write(l1)
    out.write(l2)
    out.write(l3)
    out.write(l4)
    out.write(l5)
    out.write(l6)

    return float(bigD), float(smolD), float(totalLen), float(avgLen)
