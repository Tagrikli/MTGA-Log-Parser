import time
import re
import json
from log_utils import *


logFilePath = "/home/tugrul/Games/magic-the-gathering-arena/drive_c/Program Files/Wizards of the Coast/MTGA/MTGA_Data/Logs/Logs/"

comID = re.compile('\[[0-9]+\]')

unityCrossLogger = "[UnityCrossThreadLogger]"
request = "==>"
response = "<=="

greToClient = "GreToClientEvent"
clientToGRE = "ClientToGREMessage"
matchGameRoomChanged = "MatchGameRoomStateChangedEvent"

eventJoin = "Event.Join"
updateDeck = "Deck.UpdateDeckV3"
deckSubmit = "Event.DeckSubmitV3"
matchCreated = "Event.MatchCreated"
postMatchUpdate = "PostMatch.Update"


fileManager = LogFileManager(logFilePath)
helper = GameStateMessageHelper()

gamePlayers = {}

def follow(thefile):
    thefile.seek(0,2)
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line


while True:
    
    
    lines = fileManager.checkFile()

    for lineNum, line in enumerate(lines):
        line = line[:-1]

        infoLine = comID.match(line)
        if infoLine:
            info = infoLine.string

            if unityCrossLogger in info:
                if response in info:
                    logEvent = info.split(" ")[2]
                    data = json.loads("".join(info.split(" ")[3:]))
                    if logEvent == eventJoin:
                        print("Joining Match")
                    elif logEvent == deckSubmit:
                        print("Deck info:")
                        dectDict = evalDeck(
                            data["payload"]["CourseDeck"]["mainDeck"])
                        for key in dectDict:
                            print(f"    {key}: {dectDict[key]}")

                    elif logEvent == matchCreated:
                        print("Match Created!\nOpponent:",data["payload"]["opponentScreenName"])
                    elif logEvent == postMatchUpdate:
                        print("Match Finished!")
                        helper.players = []

                elif clientToGRE in info:
                    inc = 1
                    data = ""

                    while lineNum + inc < len(lines) and comID.match(lines[lineNum + inc]) is None:
                        data += lines[lineNum + inc][:-1]
                        inc += 1

                    diki = json.loads(data)
                    payloadType = diki["payload"]["type"]

                    if "PerformActionResp" in payloadType:
                        """
                        action = diki["payload"]["performActionResp"]["actions"][0]
                        if action["actionType"] == "ActionType_Play":
                            cardID = action["grpId"]
                            print(">>", getCardInfo(
                                cardID)["name"], action["instanceId"])
                        elif action["actionType"] == "ActionType_Pass":
                            print("Passed")
                        """


                    elif "MulliganResp" in payloadType:
                        desicion = diki["payload"]["mulliganResp"]["decision"]
                        if desicion == "MulliganOption_Mulligan":
                            print("Mulligan Result: Mulligan")
                        elif desicion == "MulliganOption_AcceptHand":
                            print("Mulligan Result: Hand Accepted")

                    elif "SubmitAttackersReq" in payloadType:
                        print("Request: Attack submitted")


                    elif "ConcedeReq" in payloadType:
                        print("Concede Request")

                    else:
                        pass


                elif greToClient in info:
                    
                    data = lines[lineNum + 1]
                    diki = json.loads(data)

                
                    for di in diki["greToClientEvent"]["greToClientMessages"]:
                        if "gameStateMessage" in di:
                            stateMessages = di["gameStateMessage"]

                            if "zones" in stateMessages:
                                for zone in stateMessages["zones"]:

                                    helper.updZone(zone)

                                    """
                                    if "objectInstanceIds" in zone:
                                        print(zone["type"].ljust(10), zone["zoneId"])
                                    else:
                                        print(zone["type"])
                                    """

                            if "gameObjects" in stateMessages:
                                for obj in stateMessages["gameObjects"]:
                                    helper.updGameObject(obj)
                                    #helper.printObjValues(obj) 

                            if "actions" in stateMessages:
                                for act in stateMessages["actions"]:
                                    if "instanceId" in act["action"]:
                                        pass
                            
                            if "gameInfo" in stateMessages:
                                if "stage" in  stateMessages["gameInfo"]:
                                    print("Stage:".ljust(15),stateMessages["gameInfo"]["stage"])
                                
                                if "results" in stateMessages["gameInfo"]:

                                    for res in stateMessages["gameInfo"]["results"]:

                                        if res["result"] == "ResultType_Draw":
                                            print("Game result: Draw")

                                        elif res["result"] == "ResultType_WinLoss":

                                            winningId = res["winningTeamId"]
                                            for player in helper.players:
                                                if player["id"] == winningId:
                                                    print("Gamer Result: Winner->".ljust(15), player["username"])

                            if "players" in stateMessages:
                                for player in stateMessages["players"]:
                                    for ind, p in enumerate(helper.players):
                                        if p["id"] == player["teamId"]:

                                            if helper.players[ind]["currentLife"] != player["lifeTotal"]:
                                                print("Player:".ljust(15),f"{p['username']}, Life: {p['currentLife']}, Total Life: {p['startingLife']}")

                                            helper.players[ind]["currentLife"] = player["lifeTotal"]
                                            helper.players[ind]["startingLife"] = player["startingLifeTotal"]



                elif matchGameRoomChanged in info:
                    data = lines[lineNum + 1]
                    diki = json.loads(data)
                    gameRoomConfig = diki["matchGameRoomStateChangedEvent"]["gameRoomInfo"]["gameRoomConfig"] 
                    if "reservedPlayers" in gameRoomConfig:
                        players = gameRoomConfig["reservedPlayers"]
                        for player in players:
                            helper.createPlayer(player)
                            print("Player:".rjust(15),f"[{player['teamId']}:{player['playerName']}]")



    time.sleep(0.3)

