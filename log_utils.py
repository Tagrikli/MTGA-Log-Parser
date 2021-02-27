import requests
import json
from os import path, listdir
import time
import re

def getCardInfo(cardID):

    if path.exists(f"cardInfos/{cardID}.json"):
        with open(f"cardInfos/{cardID}.json", "r") as cardFile:
            resp = json.loads(cardFile.read())

    else:
        resp = requests.get(
            f"https://api.scryfall.com/cards/arena/{cardID}").json()
        if resp["object"] == "error":
            resp["name"] = None

        with open(f"cardInfos/{cardID}.json", "w") as cardFile:
            cardFile.write(json.dumps(resp))

        time.sleep(0.1)

    return resp


class GameObject:
    def __init__(self, data):
        self.instanceId = data["instanceId"]
        self.grpId = data["grpId"]
        self.type = data["type"]
        self.zoneId = data["zoneId"]
        self.visibility = data["visibility"]
        self.ownerSeatId = data["ownerSeatId"]
        self.name = getCardInfo(self.grpId)["name"]

    @property
    def asList(self):
        return [self.instanceId, self.grpId, self.type,
                self.zoneId, self.visibility, self.ownerSeatId]

class Zone:
    def __init__(self, data):
        self.zoneId = data["zoneId"]
        self.type = data["type"]
        self.visibility = data["visibility"]
        if "objectInstanceIds" in data:
            self.objectInstanceIds = data["objectInstanceIds"]
            self.objectInstanceIds.sort()
        else:
            self.objectInstanceIds = []

        

    @property
    def asList(self):
        return [self.zoneId, self.type, self.visibility]



class GameStateMessageHelper:
    def __init__(self):
        self.objects = []
        self.zones = []
        self.players = []

    def updGameObject(self, newObjData, log=False):
        newObj = GameObject(newObjData)
        new = True

        for obj in self.objects:
            if obj.instanceId == newObj.instanceId and obj.name and newObj.name:
                objProps = obj.asList
                newObjProps = newObj.asList
                for index in range(len(objProps)):
                    if objProps[index] != newObjProps[index]:

                        if index == 3:
                            pass
                            print("Object Change".ljust(15),f"[{obj.name}:{obj.instanceId}:{obj.ownerSeatId}]: {self.findZoneName(objProps[index])} -> {self.findZoneName(newObjProps[index])}")

                        else:
                            print("Object Change".ljust(15),f"[{obj.name}:{obj.instanceId}:{obj.ownerSeatId}]: {objProps[index]} -> {newObjProps[index]}")

                self.objects.remove(obj)
                self.objects.append(newObj) 
                new = False

        if new:
            self.objects.append(newObj) 
        



    def updZone(self, newZoneData, log=False):

        newZone = Zone(newZoneData)

        temp = []
        for id in newZone.objectInstanceIds:
            objIds = [x.instanceId for x in self.objects]
            if id in objIds:
                temp.append(id)

        newZone.objectInstanceIds = temp

        new = True

        for zone in self.zones:
            if zone.zoneId == newZone.zoneId:
                zoneProps = zone.asList
                newZoneProps = newZone.asList

                #Not needed in for current task
                for index in range(len(zoneProps)):
                    if zoneProps[index] != newZoneProps[index]:
                        print("Zone Change".ljust(15),f"[{zone.type}:{zone.zoneId}]: {zoneProps[index]} -> {newZoneProps[index]}")
                        self.zones.remove(zone)
                        self.zones.append(newZone)
                        new = False


                if zone.objectInstanceIds != newZone.objectInstanceIds:
                    if zone.type == "ZoneType_Battlefield":
                        print("Battlefield Change".ljust(15),f"[{zone.type}:{zone.zoneId}]:")
                        for name in self.cardNamesFromZone(newZone.objectInstanceIds):
                            print("     ",name)
                    
            
                self.zones.remove(zone)
                self.zones.append(newZone)
                new = False

        if new:
            self.zones.append(newZone)
     

    def createPlayer(self,playerData):
        p = {"id":playerData["teamId"],"username":playerData["playerName"], "currentLife": None, "startingLife":None}
        self.players.append(p)


    def cardNamesFromZone(self,instanceIds):
        cardNames = []
        for id in instanceIds:
            added = False
            for obj in self.objects:
                if obj.instanceId == id:
                    cardNames.append(obj.name)
                    added = True
                    break
            if not added:
                cardNames.append(id)

        return cardNames

    def findZoneName(self,zoneId):
        for zone in self.zones:
            if zone.zoneId == zoneId:
                return zone.type

    def printObjValues(self, obj):
        print(
            f'-----> {getCardInfo(obj["grpId"])["name"].ljust(20)} {str(obj["instanceId"]).ljust(10)} {obj["visibility"].ljust(10)} {str(obj["ownerSeatId"]).ljust(10)} {obj["zoneId"]}')





def evalDeck(deckList):
    deckDict = {}
    for index in range(0, len(deckList), 2):
        cardInfo = getCardInfo(deckList[index])
        cardName = cardInfo["name"]
        deckDict[cardName] = deckList[index + 1]

    return deckDict


def get_recursively(search_dict, field):
    """
    Takes a dict with nested lists and dicts,
    and searches all dicts for a key of the field
    provided.
    """
    fields_found = []

    for key, value in search_dict.items():

        if key == field:
            fields_found.append(value)

        elif isinstance(value, dict):
            results = get_recursively(value, field)
            for result in results:
                fields_found.append(result)

        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    more_results = get_recursively(item, field)
                    for another_result in more_results:
                        fields_found.append(another_result)

    return fields_found


class LogFileManager:
    def __init__(self, logFilePath) -> None:
        self.lineCount = 0
        self.logsPath = logFilePath
        self.logFilename = ""

    def checkFile(self, filename=""):
        """
        Return new added lines in the log file.
        Pre-condition: A non-emtpy log folder.
        """
        if not filename:
            filename = self.newestFilename()

        with open(self.logsPath + filename, "r") as logFile:
            lines = logFile.readlines()
            newLineCount = len(lines)

        if newLineCount > self.lineCount:
            result = lines[self.lineCount:]
            self.lineCount = newLineCount
            return result

        return []

    def newestFilename(self):
        """
        Finds the newest file in log files path
        Sample log filename : UTC_Log - 02-24-2021 08.55.18.log
        """
        compareList = {}
        dateRe = re.compile(
            '[0-9]{2}-[0-9]{2}-[0-9]{4} [0-9]{2}\.[0-9]{2}\.[0-9]{2}')
        files = listdir(self.logsPath)
        for logFile in files:
            date = time.strptime(dateRe.search(logFile)[
                                 0], "%m-%d-%Y %H.%M.%S")
            compareList[date] = logFile

        return compareList[max(compareList.keys())]


if __name__ == "__main__":

    filepath = "/home/tugrul/Games/magic-the-gathering-arena/drive_c/Program Files/Wizards of the Coast/MTGA/MTGA_Data/Logs/Logs/"


    tmp = LogFileManager(filepath)

    file = open(filepath + tmp.newestFilename(),"r")


    
    loglines = follow(file)
    for line in loglines:
        print (line)