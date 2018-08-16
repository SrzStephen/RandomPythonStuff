from random import choice, randint
from serial import Serial
from time import sleep
from datetime import datetime,date
from requests import get, ConnectTimeout, ConnectionError
from sys import maxsize
from Secrets import APIKeys
from time import sleep
class offlineAGPS():
    def __init__(self,maxdays=1):
        ##takes a searchstring ,returns formatted list.
        self.dataList = []
        self.lastrequest = date(1994,1,1) ##construct dummy datetime object that'll be overwritten
        self.maxdays = maxdays
        self.reqstring = ""

    def getdata(self):
        ##Always do glonass and gps
        if (date.today()-self.lastrequest).days >=self.maxdays:
            try:
                bdata = get("https://offline-live1.services.u-blox.com/GetOfflineData.ashx?token="+str(APIKeys().AGPS)+
                        "gnss=gps,glo:"+"days=1",stream=False)
                self.dataList = str(bdata.content.hex()).upper()
                self.dataList = str(self.str2bytestr(self.dataList)).split("B5 62")[1:]
                self.lastrequest = date.today()

            except (ConnectionError, ConnectTimeout):
                sleep(100)
                return self.getdata()

        return self.dataList

    def parseCurrentDate(self):
        ##TODO: if using longer than 1 day need to break up message
        ##basically: Pull out month year day from any stings that start with b562 1320
        ##readd b562 to stop any stupidity, parse it out then strip it.
        str = "refer to UBX-MGA-ANO"
        return "#TODO"

    def str2bytestr(self, string):
        # bytes from AGPS come in as large string
        # they need to be converted to sets of two
        returnVal  =  ' '.join(string[i:i + 2] for i in range(0, len(string), 2))
        return returnVal


class onlineAGPS():
    def __init__(self):
        self.dataList = []

    def getdata(self,reqstring):
        try:
            bdata = get(reqstring , stream=False)# data comes in as a bytestring
                # and a problem presents itself. Sometimes the string will contain the header b562
                #  eg BB 56 28
                # split the string into sets of 2
            self.dataList = str(bdata.content.hex()).upper()
            self.dataList = str(self.str2bytestr(self.dataList)).split("B5 62")[1:]
            return self.dataList
        except (ConnectionError, ConnectTimeout):
            sleep(100)
            return self.getdata(reqstring)
            #  if the request was made less than minRequestPeriod ago then just use the cached value

    def str2bytestr(self, string):
        # bytes from AGPS come in as large string
        # they need to be converted to sets of two
        returnVal  =  ' '.join(string[i:i + 2] for i in range(0, len(string), 2))
        return returnVal



class RandomConfig:
    # randomiser=
    def __init__(self,offlineOnly = True):
        # if something is unset then leave it as an error (-1)
        self.offlineOnly = offlineOnly
        # GNSS Setup
        self.gal = -1
        self.glo = -1
        self.bei = -1
        self.gps = -1
        # UploadedData
        self.AGPSlastRequestMillis = -1
        self.auxData = 0
        self.almData = 0
        self.ephData = 0
        #  required for changes to AGPS Code
        self.AGPSRebuildRequired = True
        self.AGPSString = -1

        # #
        self.offlineALM = 0
        self.returnList = []
        self.useOnline = 0
        self.useOffline = 0
        self.__onlineAGPSOBJECT = onlineAGPS() ##gets setup later
        self.__offlineAGPSOBJECT = offlineAGPS() ##gets setup later
        self.GNSSSTRING = ""
        self.date = date(1994,1,1) ##dummy date

    def disableExtraMessage(self):
        mylist = [
            "06 01 08 00 F0 01 00 00 00 00 00 00 00 2A",
            "06 01 08 00 F0 02 00 00 00 00 00 00 01 31",
            "06 01 08 00 F0 04 00 00 00 00 00 00 03 3F",
            "06 01 08 00 F0 05 00 00 00 00 00 00 04 46",
            "06 01 08 00 F0 06 00 00 00 00 00 00 05 4D",
        ]
        return mylist

    def listdisableCoreMessages(self):
        # its nessessary to disable the GPSs output while uploading so I dont have to wait so long to get an ack/nack
        mylist = ["06 01 08 00 F0 03 00 00 00 00 00 00 02 38", "06 01 08 00 F0 00 00 00 00 00 00 00 FF 23"]
        return mylist

    def listenableCoreMessages(self):
        # its nesessary to renable the messages I need..GGA and GSV
        mylist = ["06 01 08 00 F0 03 00 01 01 00 00 00 04 41", "06 01 08 00 F0 00 00 01 01 00 00 00 01 2C"]
        return mylist

    def buildList(self):
        mlist = []
        # remove extra messages
        for optmessage in self.disableExtraMessage():
            mlist.append(optmessage)
        if self.offlineOnly:
            if choice([True,False]): # use or dont use
                if self.offlineAGPS(): # if offline config is actually doable
                    dataList = self.__offlineAGPSOBJECT.getdata()
                    for entry in dataList:
                        mlist.append(entry)
        else:
            # After sniffing the connection between Ucenter and the GPS, I've concluded
            # that the whole "You need to write 512 bytes to flash first
            # is fake news. This way is slower, but it works.
            if self.onlineAGPS():
                dataList = self.__onlineAGPSOBJECT.getdata(self.AGPSString)
                for entry in dataList:
                    mlist.append(entry)
        self.returnList = mlist


    def returnHeaders(self):
        # headers
        # Todo: From adrians discussion
        # Keep gal,bei,gps almdata,ephdata,offlinealm
        header = "gal,glo,bei,gps,auxdata,almdata,ephdata,offlinealm"
        return header

    # only nonstandard thing here is the AGPS - Need to return time last requested in MS.
    def returnConfigString(self):
        configString = str(self.gal) + "," + str(self.glo) + "," + str(self.bei) + "," + str(self.gps) + \
                       "," + str(self.auxData) + "," + str(self.almData) + "," +\
                       str(self.ephData)+","+str(self.offlineALM)


        return configString

    def printstr(self):
        printstring = "GAL:" + str(self.gal) + "\n"
        printstring += "GLO:" + str(self.glo) + "\n"
        printstring += "BEI:" + str(self.bei) + "\n"
        printstring += "GPS:" + str(self.gps) + "\n"
        printstring += "alm eph offlinealm " + str(self.almData)+" "+str(self.ephData)+" "+str(self.offlineALM) +"\n"
        print(printstring)

    def calcsum(self, packet):
        # Calculate checksum and return both bits
        if type(packet) is str:
            # convert to hex so I can do bitwise stuff
            try:
                packet = bytearray.fromhex(packet)
            except:
                aaaa = 1
                b =2

        CK_A, CK_B = 0, 0
        for i in range(len(packet)):
            CK_A = CK_A + packet[i]
            CK_B = CK_B + CK_A
        CK_A = CK_A & 0xFF
        CK_B = CK_B & 0xFF
        # turn to hexstr

        rA = hex(CK_A).split('x')[1].upper()
        rB = hex(CK_B).split('x')[1].upper()
        # note 0x07 gets returned as 0x7. Deal with this.
        if len(rA) == 1:
            rA = "0" + rA
        if len(rB) == 1:
            rB = "0" + rB
        return " " + str(rA) + " " + str(rB)

    def num2hex(self, num, length=1):
        # hex returns 0x, stip that
        hstring = str(hex(num)).split("x")[1]
        if len(hstring) == 1:
            hstring = "0" + hstring
            if length == 2:
                # Need to append 00 pad (little endian format)
                hstring += " 00"

        elif len(hstring) == 2:
            if length == 2:
                # Need to append 00 pad (little endian format)
                hstring += " 00"

        # If i've got 2 bytes, I'm going to need to flip them (little endian)
        elif len(hstring) == 3:
            hstring = hstring[1:] + " 0" + hstring[0]

        elif len(hstring) == 4:
            hstring = hstring[2:] + " " + hstring[0:2]

        return hstring

    def gnsstype(self):
        # This almost isn't dumb.
        # refer to https://www.u-blox.com/sites/default/files/MAX-M8-FW3_DataSheet_%28UBX-15031506%29.pdf
        # Note: Firmware has 32 tracking channels and doesn't support GAL
        rndgnss, string = choice([

        ("gps glo",    "06 3E 14 00 00 00 20 02 00 04 10 00 01 00 01 01 06 04 10 00 01 00 01 01"),
        ("gps bei",    "06 3E 14 00 00 00 20 02 00 04 10 00 01 00 01 01 03 04 10 00 00 00 01 01"),
        ("glo bei",    "06 3E 14 00 00 00 20 02 03 04 10 00 00 00 01 01 06 04 10 00 01 00 01 01"),
        ("gps",        "06 3E 0C 00 00 00 20 01 00 04 20 00 01 00 01 01"),
        ("glo",        "06 3E 0C 00 00 00 20 01 06 04 20 00 01 00 01 01"),
        ("bei",        "06 3E 0C 00 00 00 20 01 03 04 20 00 00 00 01 01")
        ])

        self.gps = 0
        self.glo = 0
        self.bei = 0
        self.gal = 0

        if "gal" in rndgnss:
            self.gal = 1
        if "glo" in rndgnss:
            self.glo = 1
        if "bei" in rndgnss:
            self.bei = 1
        if "gps" in rndgnss:
            self.gps = 1
            # doesn't include checksum or ubx header
            # OK so there was a lot in this section
            # Things kept failing
            # Rather than code in all the conditions, its easier to just hardcode things in
            #####################################################################
            ######################################################################
        self.GNSSSTRING = string + self.calcsum(string)
        return self.GNSSSTRING


    def jammingFN(self):
        # Randomise jamming on/off (should impact cpu usage therefore current, not sure how it'll impact signal
        rndjam = choice([0, 1])
        if rndjam == 0:
            self.jamming = 0
            sendstr = "06 39 08 00 F3 AC 62 AD 1E 13 00 00"
        else:
            self.jamming = 1
            sendstr = "06 39 08 00 F3 AC 62 AD 1E 53 00 00"
        sendstr = sendstr + self.calcsum(sendstr)
        return (sendstr)

    def nav5(self):
        # Nav5 messages. minimum elevation, number of satelites and their C/NO signal strength (dbm)
        # self.dynamicModel -- I REMOVED THIS OPTION BECAUSE IT SEEMED UNNESSESSARY (put back in if moving)
        self.minimumElevation = randint(10 / 5, 90 / 5) * 5  # do it in increments of 5
        self.numSV = randint(4, 10)
        self.minCNO = randint(10 / 5, 50 / 5) * 5  # "Normal" value is 30.
        sendstr = "06 24 24 00 FF FF 02 03 00 00 00 00 10 27 00 00 " + self.num2hex(self.minimumElevation)
        sendstr += " 00 FA 00 FA 00 64 00 2C 01 00 00 " + self.num2hex(self.numSV) + " " + self.num2hex(
            self.minCNO) + " 10 27 00 00 00 00 00 00 00 00"
        sendstr = sendstr + self.calcsum(sendstr)
        return sendstr

    def extendpowerman(self):
        # # #
        # I could do structure packing with struct.pack to do this
        # But it's too much effort. Just hardcode it
        self.peakCurrentlimit = choice([0, 1])
        self.waitUpdateEPH = choice([0, 1])
        self.waitUpdateRTC = choice([0, 1])
        self.waitTimeFix = choice([0, 1])
        combinedpacket = 80 + 10 * self.waitUpdateEPH + self.waitUpdateRTC * 8 + self.waitTimeFix * 4 + self.peakCurrentlimit * 1
        # # #
        #
        if combinedpacket > 99:
            combinedpacket = "9D"
        if combinedpacket == 93:
            combinedpacket = "8D"
        self.cycTracking = choice([0, 1])
        self.optTarget = choice([0, 1])
        self.updatePeriod = randint(0, 10000 / 100) * 100
        self.searchPeriod = randint(0, 10000 / 100) * 100
        self.onTime = randint(0, 1000 / 10) * 10
        self.minAqTime = randint(0, 1000 / 10) * 10
        sendstr = "06 3B 30 00 02 06 00 00 " + self.num2hex(self.optTarget * 2) + " " + str(combinedpacket)+" "+ str(self.cycTracking * 2 + 40)
        sendstr += " 01 " + self.num2hex(self.updatePeriod, 2) + " 00 00 " + self.num2hex(self.searchPeriod,
                                                                                          2) + " 00 00 00 00 00 00"
        sendstr += " " + self.num2hex(self.onTime, 2) + " " + self.num2hex(self.minAqTime,
                                                                           2) + " 2C 01 00 00 4F C1 03 00 87 02 00 00 FF 00 00 00 64 40 01 00 00 00 00 00"
        sendstr = sendstr + self.calcsum(sendstr)
        return sendstr

    def powerman(self):
        self.fullpower = 0
        self.balanced = 0
        self.aggressive1hz = 0
        self.aggressive4hz = 0

        rselect = choice([0, 1, 3])
        # python doesn't have a switch statement. There are dictionary methods to do this.
        # Don't judge
        if rselect == 0:
            self.fullpower = 1
        elif rselect == 1:
            self.balanced = 1
        elif rselect == 3:
            self.aggressive1hz = 1

        sendstr = "06 86 08 00 00 " + self.num2hex(rselect) + " 00 00 00 00 00 00"
        sendstr = sendstr + self.calcsum(sendstr)
        return sendstr

    def rxmFN(self):
        self.rxm = choice([0, 1])
        # RXM won't work when glonass signals are used. override
        if self.glo:
            self.rxm = 0

        # 1 represents continous, 2 = power save
        sendstr = "06 11 02 00 08 " + self.num2hex(self.rxm)
        sendstr = sendstr + self.calcsum(sendstr)
        return sendstr

    def offlineAGPS(self):
        self.__ClearAGPSREFS()

        # For now just 1 day
        gnss = ""
        alm = ""
        if self.glo:
            gnss = "glo"

        if self.gps:
            gnss = "gps"

        if len(gnss) >2:
            self.useOffline = 1
            return True
        else:
            return False
        return False


    def __ClearAGPSREFS(self):
        # sets all the self values to 0
        self.auxData = 0
        self.almData = 0
        self.ephData = 0
        self.AGPSString = ""
        self.AGPSlastRequestMillis = 0
        self.offlineALM = 0
        self.useOnline = 0
        self.useOffline=0

    def onlineAGPS(self):

        self.__ClearAGPSREFS()
        # special case
        # I want to randomly decide not to use eph data about 1/10th of the time
        if randint(0, 10) == 5:
            self.AGPSlastRequestMillis = 0
            self.AGPSRebuildRequired = 0
            return ""

        self.AGPSlastRequestMillis = self.millis()
        self.auxData = choice([0, 1])
        self.almData = choice([0, 1])
        self.ephData = choice([0, 1])

        # We've already got a choice of gnss networks
        gnss = ""
        if self.glo:
            gnss += "glo,"
        elif self.gal:
            gnss += "gal,"
        elif self.gps:
            gnss += "gps,"
        elif self.bei:
            gnss += "bds,"
        if len(gnss) > 2:
            gnss = ";gnss=" + gnss[:-1] + ";"
        else:
            gnss = ""
        # there's going to be a trailing comma.. Kill it
        # next build datatype
        datatype = ""
        if self.auxData:
            datatype += "aux,"
        if self.ephData:
            datatype += "eph,"
        if self.almData:
            datatype += "alm,"

        if len(datatype) > 2:
            datatype = "datatype=" + datatype[:-1] + ";"
        else:
            datatype = ""

        if len(datatype) > 2 or len(gnss) > 2:
            # The lat/long thing is only for minimising size of package
            # If satellites aren't in view at a given country it'll filter it.
            # I've made the assumption that WA is the location
            self.useOnline = 1
            message = "https://online-live1.services.u-blox.com/GetOnlineData.ashx?token=" + str(APIKeys().AGPS) + str(gnss) + str(
                datatype) + "lat=-31.9310886;lon=115.8185961;alt=50;pacc=90000;filteronpos"
            self.AGPSString = message
            return message
        else:
            return ""

    def millis(self):
        dt = datetime.now()
        ms = (dt.day * 24 * 60 * 60 + dt.second) * 1000 + dt.microsecond / 1000.0
        return ms

