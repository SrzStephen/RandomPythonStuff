from serial import Serial
from time import sleep
from datetime import datetime,date
import pynmea2


class GPS():
    def __init__(self, gps):
        self.NumMSGForACK = 20
        self.messageAfterSending = []
        self.deviceConnected = False
        self.AckNackConfigured = False
        self.FailedLockInTime = False
        if "/dev/ttyUSB" in gps:
            self.device = Serial(gps, baudrate=9600, timeout=2, write_timeout=5)
            sleep(1)
            self.deviceConnected = self.device.is_open

    def __listNackAck(selfs):
        # returns a list letting me have acks and naks
        mylist = [
                "06 01 08 00 05 01 01 01 01 01 01 00 1A E6"
                "06 01 08 00 05 00 01 01 01 01 01 00 19 DF",
                  "06 01 08 00 13 60 01 01 01 01 01 00 87 EF",]
        return mylist

    def logUntilDone(self):
        writelist = []

        ##see here for pynmea Types
        ##https://github.com/Knio/pynmea2/blob/master/pynmea2/types/talker.py
        csvline = ""
        messagenumber = 1
        lockNotAchieved = True
        pynmea2.NMEAStreamReader(stream=None, errors='ignore')
        timestart = date.today()
        while lockNotAchieved:
            if (date.today()-timestart).total_seconds()> 60*15:  # timeout after 15 min
                FailedLockInTime = True
                return writelist
            line = str(self.device.readline())[2:-5]
            try:
                pynmea = pynmea2.parse(line, check=False)

                ##I can read halfway into another line, errors=ignore
                if pynmea.sentence_type == "GGA":
                    if pynmea.gps_qual > 0:
                        lockNotAchieved = False

                elif pynmea.sentence_type == "GSV":
                    ##plan: uniquecycle,sv,elevation,azimuth,snr
                    ##I get 1 unique GSV cycle/sec
                    if pynmea.num_messages == pynmea.msg_num:
                        messagenumber += 1

                    writelist = self.makeSGVString(messagenumber, pynmea.sv_prn_num_1, pynmea.elevation_deg_1,
                                                   pynmea.azimuth_1, pynmea.snr_1, writelist)

                    writelist = self.makeSGVString(messagenumber, pynmea.sv_prn_num_2, pynmea.elevation_deg_2,
                                                   pynmea.azimuth_2, pynmea.snr_2, writelist)

                    writelist = self.makeSGVString(messagenumber, pynmea.sv_prn_num_3, pynmea.elevation_deg_3,
                                                   pynmea.azimuth_3, pynmea.snr_3, writelist)

                    writelist = self.makeSGVString(messagenumber, pynmea.sv_prn_num_4, pynmea.elevation_deg_4,
                                                   pynmea.azimuth_4, pynmea.snr_4, writelist)

            except (pynmea2.nmea.ParseError, pynmea2.nmea.ChecksumError):
                continue
        return writelist

    def makeSGVString(self, numb, sv, elevation, azimuth, snr, writelist):
        ##only append if its not totally blank
        if not (elevation == "" and azimuth == "" and snr == ""):
            mystr = str(numb) + "," + str(sv) + "," + str(elevation) + "," + str(azimuth) + "," + str(snr)
            writelist.append(mystr)
        return writelist

    def restart(self, type):
        if "hot" in type:
            self.sendConfigs(["06 04 04 00 00 00 01 00 0E 64"])
        if "cold" in type:
            self.sendConfigs(["06 04 04 00 FF B9 01 00 C6 8B"])
        if "RTCOnly" in type:
            self.sendConfigs(["06 04 04 00 00 01 01 00 0F 67"])
        if "ALMRTC" in type:
            self.sendConfigs(["06 04 04 00 FD B8 01 00 C3 80"])

    def __parseUntilACKNAK(self, string):
        acknacknotfound = True
        nummsg = 0
        while acknacknotfound:
            try:
                if nummsg == self.NumMSGForACK:
                    return False
                line = str(self.device.readline())[2:-5].upper()
                pynmea = pynmea2.parse(line, check=False)
                if "MGA" in pynmea.sentence_type:
                    print("MGAMESSAGEFOUND")
                #if pynmea.sentence_type == "GGA":
                    # if pynmea.gps_qual > 0:
                    #    return "FIX"
                nummsg = nummsg + 1

            except pynmea2.nmea.ChecksumError:
                nummsg = nummsg + 1
                pass

            except pynmea2.nmea.ParseError:
                nummsg = nummsg + 1
                # it's likely that the first entry won't have a \r\n so won't register as a line
                if len(line) > 2:
                    response = self.__checkisConfig(line)
                    if response:
                        if response == "NAK":
                            print("Message: {} returned NAK! FAILED!".format(string[0:6]))
                            nummsg = self.NumMSGForACK
                            return ("NAK")

                        elif response == "ACK":
                            print("Message: {} returned ACK".format(string[0:6]))
                            return ("ACK")
                else:
                    continue
        return False

    def __checkisConfig(self, line):
        storeString = line.split('\\x')[1:]
        lastString = " ".join(storeString).split("b5b 05")[-1].lstrip()
        lastString = lastString[0:2]
        ## empty string is considered false
        if lastString == "01":
            return "ACK"
        if lastString == "00":
            return "NAK"

        else:
            response = self.__checkIsMGA(line)
            if response:
                return response
            else:
                return False

    def __checkIsMGA(self, line):
        storeString = line.split('\\x')[1:]
        lastString = " ".join(storeString).split("b5b 05")[-1].lstrip()
        lastString = lastString[0:2]
        ## empty string is considered false
        if lastString == "01":
            return "ACK"
        if lastString == "00":
            return "NAK"
        else:
            return lastString

    def sendConfigs(self, configList, report=False):
        # Sends configurations as a list
        mgadelay = 0
        if not self.AckNackConfigured:  # If it's not configured, ensure acks nacks enabled first
            self.AckNackConfigured = True  # if I set this after i'd get recursion
            self.sendConfigs(self.__listNackAck(), report=False)

        startime = self.__millis()
        for itemindex, bItem in enumerate(configList):
            if str(bItem).lstrip()[0:2] == "13":
                # report = False
                mgadelay = .5


            completeMessage = "B5 62 " + str(bItem).lstrip()  ##for some reason theres some whitespace
            byteMessage = bytearray.fromhex(completeMessage)
            self.device.flushInput()
            self.device.flushOutput()
            self.device.flush()
            self.device.write(byteMessage)
            sleep(0.5+mgadelay)
            if report:
                status = self.__parseUntilACKNAK(str(bItem))
                if status == "FIX":
                    print("got a fix")
                    return

                if not status:
                    msgcode = str(bItem.lstrip())[0:6]
                    msgclass = msgcode[0:2]
                    if msgclass == "06":
                        msgclass = "CFG"
                    elif msgclass == "13":
                        msgclass = "MGA"
                    else:
                        msgclass = "???"

                    print("Message {} {}: {} of {} Didn't return in time".format(msgclass, msgcode,
                                                                                 str(itemindex + 1), len(configList)))
        # return time sending configs took.
        return self.__millis() - startime

    def __millis(self):
        dt = datetime.now()
        ms = (dt.day * 24 * 60 * 60 + dt.second) * 1000 + dt.microsecond / 1000.0
        return ms

    def millis(self): # __millis() wasn't being accepted in part of the loop
        dt = datetime.now()
        ms = (dt.day * 24 * 60 * 60 + dt.second) * 1000 + dt.microsecond / 1000.0
        return ms

class Arduino():
    ##The way I was doing things previously will cause 2 problems
    ##1.Filesize will be stupidly large
    ##2.It was pretty resource heavy (I have a feeling that the reason for inconsistency in times
    ##was due to serial buffer filling faster than I could read it.
    ##Solution: Send "S" to Arduino to accumulate a sin-gle value
    ##Send "E" to arduino to end its count
    def __init__(self, devstring):
        self.deviceConnected = False
        self.power = -1

        if "/dev/ttyUSB" in devstring:
            self.device = Serial(devstring, baudrate=9600, timeout=10, write_timeout=10)
            if self.device.is_open:
                self.deviceConnected = True

        self.__startTime = self.__millis()
        self.timeTaken = -1

    def start(self):
        self.device.write(bytearray.fromhex("31"))
        self.__startTime = self.__millis()

    def end(self):
        self.device.write(bytearray.fromhex("30"))

        line = self.device.readline()
        while len(line) < 2:
            line = self.device.readline()
        ##linestructure 'bxxxyyy
        self.power = float(line[0:-2])/1000000
        self.timeTaken = self.__millis() - self.__startTime

    def __millis(self):
        dt = datetime.now()
        ms = (dt.day * 24 * 60 * 60 + dt.second) * 1000 + dt.microsecond / 1000.0
        return ms
