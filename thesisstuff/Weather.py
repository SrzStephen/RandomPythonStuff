import time
from bs4 import BeautifulSoup
from unicodedata import normalize
from Secrets import APIKeys
from sys import maxsize
from requests import get, ConnectionError, ConnectTimeout


# Todo: change based on adrians comments
# Connectionerrors, Connectiontimeout need to be logged
# Reasoning: real world system



class AGRICData:
    def __init__(self,station='BG001'):
        self.__reqString = 'https://api.agric.wa.gov.au/v1/weatherstations/' +\
                 self.station + '/latest.json?'+ APIKeys().AGRICKey
        self.station = station #kings park default

        self.lastCalled = 0 #avoid initial NaN
        self.humidity = 0
        self.airTemp = 0
        self.dewPoint = 0
        self.windSpeed = 0

    def request(self):
        if (time.time() - self.lastCalled )> 120: ## if it was already requested in last 2 min
            response = get(self.__reqString)
            if response.status_code == 200: ##command worked.
                ## successful request
                self.__parseRequest(response.json()['result'][0])
                return True
            else:
                return False


    def __parseRequest(self,text):
        self.humidity = text['humidity']
        self.airTemp = text['air_temp']
        self.windSpeed = text['wind_speed_ave']

    def changeStation(self,station):
        self.station = station
        #floriet nearby - FL
        return True


class OWMData:
    # openWeatherMap
    def __init__(self, postCode=6000):
        self.reqString = 'http://api.openweathermap.org/data/2.5/weather?zip=' \
                         + str(postCode) + ',au&appid=' + APIKeys().OpenWeather

        self.validData = False
        self.cloud = -1
        self.humidity = -1

    def request(self):
        try:
            response = get(self.reqString)
            if response.status_code == 200:
                self.__parse(response.json())  # json is a function..
        except(ConnectionError):
            self.cloud = "Connection"
            self.humidity = "Connection"

        except (ConnectTimeout):
            self.cloud = "Timeout"
            self.humidity = "Timeout"

    def __parse(self, jdata):
        self.cloud = jdata['clouds']['all']
        self.humidity = jdata['main']['humidity']
        self.lastcalled = time.time()

    def jsontest(self):
        response = get(self.reqString)
        if response.status_code == 200:
            return response.json()


class Rainfall:
    # Changes suggested: Instead of inf retrying, just continue and log what happened
    # connectionerrror will be 502, connecttimeout will be internet connection died
    def __init__(self):
        self.rainfallThisHour = -1
        self.rainfallLastHour = -1

    def request(self):
        try:
            response = get('http://www.bom.gov.au/cgi-bin/wrap_fwo.pl?IDW60207.html')
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html5lib')
                table = soup.find_all('tr')
                for tr in table:
                    try:
                        cols = tr.find_all('td')
                        name = normalize("NFKD", cols[0].get_text())
                        if name == "Perth Metro AWS*":
                            # items 7 and 8 contain last hour and current hour rainfall in mm, extract and return
                            self.rainfallThisHour = float(normalize("NFKD", cols[8].get_text()).strip())
                            self.rainfallLastHour = float(normalize("NFKD", cols[7].get_text()).strip())
                            return self.rainfallThisHour
                    except (IndexError):
                        pass


        except(ConnectionError):
            self.rainfallThisHour = "ConnectionError"
            self.rainfallLastHour = "ConnectionError"
        except(ConnectTimeout):
            self.rainfallThisHour = "ConnectionTimeout"
            self.rainfallLastHour = "ConnectionTimeout"
        return False


class OwnWeather:
    def __init__(self, ipadd):
        self.ipaddress = ipadd

    def getData(self):
        try:
            response = get(self.ipaddress)
            if response.status_code == 200 and len(response.json()) == 2:
                return str(response.json()[0]), str(response.json()[1])
            else:
                return "UnknownError", "UnknownError"
        except ConnectionError:
            return "ConError", "ConError"

        except ConnectTimeout:
            return "TimeoutError", "TimeoutError"