import Configs
import Devices
import Weather
import csv
from random import choice
from datetime import datetime,date

def __millis():
    dt = datetime.now()
    ms = (dt.day * 24 * 60 * 60 + dt.second) * 1000 + dt.microsecond / 1000.0
    return ms
gpsDevice = '/dev/ttyUSB0'
arduinoDevice = "/dev/ttyUSB1"

gps = Devices.GPS(gpsDevice)
arduino = Devices.Arduino(arduinoDevice)


location = '/home/pi/Thesis/data/'
file = "configlist.csv"

rain = Weather.Rainfall()
envdata = Weather.OWMData()
owndata = Weather.OwnWeather('http://192.168.1.53:500')
rownum = 2

##todo check if file exists
##todo also check if 2.csv exists. Exit on both cases
with open(location + file, "a+") as writefile:
    configFile = csv.writer(writefile, delimiter=",")
    ConfigMaker = Configs.RandomConfig(offlineOnly=False)
    completeheaders = str(
        "Row") + "," + ConfigMaker.returnHeaders() + ",owntemp,ownhumidity"+\
                      ",rainfall,cloud,humidity,restarttype,current,timetaken,datetime"

    configFile.writerow([completeheaders])
    writefile.close()
    # Loop until I hit ctrl C
    while True:
        with open(location + file, "a+") as writefile:
            configFile = csv.writer(writefile, delimiter=",")
            # need to define what this restart is
           # restart = choice(["hot","cold","RTCOnly","ALMRTC"])
            restart = "cold"
            print(restart)
            if (date.today() - ConfigMaker.date).total_seconds() > 15*60:
                # Convert difference in milis to hour
                ConfigMaker.AGPSRebuildRequired = True

            # generate new random configs
            ConfigMaker.gnsstype()  # Get gnss type without appending it to buildlist
            configs = ConfigMaker.buildList()
            ConfigMaker.printstr()
            # request data from servers
            rain.request()
            envdata.request()
            # get ready to write
            mytemp, myhumid = owndata.getData()
            cmString = ConfigMaker.returnConfigString()
            partialwriterow = cmString + ","+ mytemp+","+myhumid+ "," + str(rain.rainfallThisHour) + "," + str(envdata.cloud) + \
                              "," + str(envdata.humidity) + "," + restart
            # partial writerow needs the current and time taken which come from the arduino

            # configmaker contains the configs needed as returnlist which then get sent to the GPS via sendconfigs
            gps.restart(restart)
            previous = datetime.now()
            arduino.start()
            #  ##disable core messages
            print("Writing configs")
            gps.sendConfigs([ConfigMaker.GNSSSTRING]) #Triggers a reset
            gps.sendConfigs(ConfigMaker.disableExtraMessage(), report=False)
            gps.sendConfigs(ConfigMaker.listdisableCoreMessages())
            gps.AckNackConfigured = False  ##aks get reset by reset
            gps.sendConfigs(["06 01 08 00 05 01 00 01 00 00 00 00 16 D7"],report=False) # ACK
            gps.sendConfigs(["06 01 08 00 05 00 00 01 00 00 00 00 15 D0"],report=False)  # NAK
            gps.sendConfigs(["06 01 08 00 13 60 00 01 00 00 00 00 83 E0"],report=False)  # MGA ACK
            gps.sendConfigs(ConfigMaker.returnList, report=False)
            gps.sendConfigs(ConfigMaker.listenableCoreMessages(), report=False)  ##reenable core messages
            # get satelite data - returns a list of SVs seen, with azimuth, SNR and elevation.
            print("Logging")
            svlist = gps.logUntilDone()
            # this will return once a 3d fix is obtained (via GGA string). at this point lock has been obtained
            arduino.end()
            spenttime = str((datetime.now() - previous).total_seconds())
            print("Writing")
            if gps.FailedLockInTime:
                configFile.writerow([str(rownum) + "," + partialwriterow + "," + "inf" + "," + "inf"+","+datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            else:
                configFile.writerow([str(rownum) + "," + partialwriterow + "," + str(
                    arduino.power) + "," + str(spenttime)+","+datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
            ##save satelite data as a new file with name=row so I can reference it later
            with open(str(location+str(rownum)) + ".csv", "w+") as satFile:
                wr = csv.writer(satFile, delimiter=",")
                for rrow in svlist:
                    wr.writerow([rrow[0:-1]])


            rownum = rownum+1
            satFile.close()
            ##configFile.writerow(partialwriterow + "," + str(arduino.power) + "," + str(arduino.timeTaken))
        writefile.close()
    print("DONE")