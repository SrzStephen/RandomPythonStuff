from obd import OBD, commands, OBDStatus
import csv
# record throttle, rpm, engine load and speed when my car goes from complete stop to movement.
# Weirdly the OBD port doesn't differentiate forward movement from backward movement
class OBDReading():
    def __init__(self, connection):
            self.throttle = connection.query(commands.THROTTLE_ACTUATOR).value.magnitude
            self.rpm = connection.query(commands.RPM).value.magnitude
            self.engineLoad = connection.query(commands.ENGINE_LOAD).value.magnitude
            self.speed = connection.query(commands.SPEED).value.magnitude
            if self.speed == 0 or self.speed is None:
                self.moving = False
            else:
                print('moving')
                self.moving = True
            self.csvstring = "{},{},{},{},".format(self.throttle,self.rpm,self.engineLoad,self.speed)


conn = OBD(portstr='/dev/ttyUSB0',baudrate=38400,fast=False)
with open('/home/stephen/loggeddata.csv', 'w', newline='') as csvfile:
    if conn.status() == OBDStatus.CAR_CONNECTED:
        print(conn.status())
        try:
            while True:
                reading = []
                print('reading reset')
                reading.append(OBDReading(conn))
                if not reading[0].moving:
                    reading.append(OBDReading(conn))
                    if reading[1].moving:
                        print('{},{}'.format(reading[0].moving, reading[0].speed))
                        print('{},{}'.format(reading[1].moving, reading[1].speed))
                        print('beginlogging')
                        for _ in range(0,10):
                            reading.append(OBDReading(conn))
                            writer = csv.writer(csvfile,delimiter=",")
                            fullstring = ""
                        for dataclass in reading[1:]:
                            fullstring = fullstring + dataclass.csvstring
                        print(fullstring)
                        writer.writerow(fullstring.split(','))

        except(KeyboardInterrupt):

            exit()

    else:
        print("Connection Error")
