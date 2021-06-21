#!/usr/bin/python
# Minimal Motion Detection Logic written by Claude Pageau Dec-2014

import time
import datetime
import picamera
import picamera.array
from fractions import Fraction
import cloudinary
import cloudinary.uploader
import cloudinary.api
from os import listdir
from os.path import isfile, join
import os

# Logging
verbose = True     # False= Non True=Display showMessage

# Motion Settings
threshold = 30     # How Much a pixel has to change
sensitivity = 300  # How Many pixels need to change for motion detection

# Camera Settings
testWidth = 128
testHeight = 80
nightShut = 5.5    # seconds Night shutter Exposure Time default = 5.5  Do not exceed 6 since camera may lock up
nightISO = 800
if nightShut > 6:
    nightShut = 5.9
SECONDS2MICRO = 1000000  # Constant for converting Shutter Speed in Seconds to Microseconds    
nightMaxShut = int(nightShut * SECONDS2MICRO)
nightMaxISO = int(nightISO)
nightSleepSec = 8   # Seconds of long exposure for camera to adjust to low light

cloudinary.config( 
  cloud_name = "dqlgtokk8", 
  api_key = "434278526675149", 
  api_secret = "_pqv4v5VEuFeMuB5WuIG-UsSXxk" 
)

#-----------------------------------------------------------------------------------------------           
def showTime(Depende):
    rightNow = datetime.datetime.now()
    if Depende:
        currentTime = "%04d%02d%02d-%02d:%02d:%02d" % (rightNow.year, rightNow.month, rightNow.day, rightNow.hour, rightNow.minute, rightNow.second)
    else:
        currentTime = "%04d%02d%02d-%02d_%02d_%02d" % (rightNow.year, rightNow.month, rightNow.day, rightNow.hour, rightNow.minute, rightNow.second)
    return currentTime    

#-----------------------------------------------------------------------------------------------           
def Upload():
    tiempo = showTime(False)
    nombre_carpeta = "/"+ str(tiempo) + "/"
    directorio = "/tmp/"
    imagenes = [r for r in listdir(directorio) if isfile(join(directorio,r))]
    for foto in imagenes:   
        if foto != ".X0-lock":
            cloudinary.uploader.upload("/tmp/"+foto,folder = nombre_carpeta,use_filename = True)
            print("Foto subida")
            os.remove("/tmp/"+ foto)
        
#-----------------------------------------------------------------------------------------------           
def setInitialTime(tiempo):
    horas = tiempo.split('-')[1]
    division = horas.split(':')
    tinicial = int(division[2]) + int(division[1])*60 + int(division[0])*3600
    return tinicial

def Calculotiempo(inicial):
    daytime = showTime(True)
    actual = setInitialTime(daytime)
    if actual-inicial >= 10:
        return True
    else:
        return False
#-----------------------------------------------------------------------------------------------           
def userMotionCode(daytime,inicio):
    # Users can put code here that needs to be run prior to taking motion capture images
    # Eg Notify or activate something.
    # User code goes here
    
    with picamera.PiCamera() as camera:
        camera.rotation = 90
        camera.capture("/tmp/"+str(daytime)+".jpg")
        camera.stop_preview()
    if inicio:
        Tinicio = setInitialTime(daytime)
        inicio = False
    else:
        return [inicio]
    return [inicio,Tinicio]
    
#-----------------------------------------------------------------------------------------------             
def showMessage(functionName, messageStr):
    if verbose:
        now = showTime(True)
        print ("%s %s - %s " % (now, functionName, messageStr))
    return

#-----------------------------------------------------------------------------------------------               
def checkForMotion(data1, data2):
    # Find motion between two data streams based on sensitivity and threshold
    motionDetected = False
    pixColor = 1 # red=0 green=1 blue=2
    pixChanges = 0;
    for w in range(0, testWidth):
        for h in range(0, testHeight):
            # get the diff of the pixel. Conversion to int
            # is required to avoid unsigned short overflow.
            pixDiff = abs(int(data1[h][w][pixColor]) - int(data2[h][w][pixColor]))
            if  pixDiff > threshold:
                pixChanges += 1
            if pixChanges > sensitivity:
                break; # break inner loop
        if pixChanges > sensitivity:
            break; #break outer loop.
    if pixChanges > sensitivity:
        motionDetected = True
    return motionDetected 
    
#-----------------------------------------------------------------------------------------------             
def getStreamImage(daymode):
    # Capture an image stream to memory based on daymode
    isDay = daymode
    with picamera.PiCamera() as camera:
        time.sleep(.5)
        camera.resolution = (testWidth, testHeight)
        with picamera.array.PiRGBArray(camera) as stream:
            if isDay:
                camera.exposure_mode = 'auto'
                camera.awb_mode = 'auto' 
            else:
                # Take Low Light image            
                # Set a framerate of 1/6fps, then set shutter
                # speed to 6s and ISO to 800
                camera.framerate = Fraction(1, 6)
                camera.shutter_speed = nightMaxShut
                camera.exposure_mode = 'off'
                camera.iso = nightMaxISO
                # Give the camera a good long time to measure AWB
                # (you may wish to use fixed AWB instead)
                time.sleep( nightSleepSec )
            camera.capture(stream, format='rgb')
            return stream.array

#-----------------------------------------------------------------------------------------------           
def Main():
    dayTime = True
    msgStr = "Checking for Motion dayTime=%s threshold=%i sensitivity=%i" % ( dayTime, threshold, sensitivity)
    showMessage("Main",msgStr)
    stream1 = getStreamImage(dayTime)
    primero = True
    Tinicio = 24*3600
    while True:
        stream2 = getStreamImage(dayTime)
        if checkForMotion(stream1, stream2):
            time = showTime(True)
            out =userMotionCode(time,primero)
            if len(out) == 2:
                Tinicio = out[1]
        stream1 = stream2
        if Calculotiempo(Tinicio):
            Upload()
            primero = True
            Tinicio = 24*3600
            print('Carpeta subida')
    return
     
#-----------------------------------------------------------------------------------------------           
if __name__ == '__main__':
    try:
        Main()
    finally:
        print("")
        print("+++++++++++++++++++")
        print("  Exiting Program")
        print("+++++++++++++++++++")
        print("")
               
            
