import numpy as np
import cv2
from matplotlib import pyplot as plt
from PIL import Image
import time
import threading
import io
import asyncio
import json

imgs = {"empty":        np.zeros((32,32,4)),
        "selection":    np.zeros((32,32,4)),
        "bg":           np.zeros((32,205,4))}

gl = {"state":      0,
      "lastImg":    np.zeros((32,32,4), dtype=np.uint8),
      "turn":       0,
      "show":       False}

stats = {}
pnames = []
pixelCounts = [0,0,0,0]
pixelLoss = [0,0]

inputs = []
inputstext = []
outputs = []

battleimg = np.zeros((32,205,4), dtype=np.uint8)
P = [(0,0),
    np.zeros((32,32,4), dtype=np.uint8),
    (0,205-32),
    np.zeros((32,32,4), dtype=np.uint8)]

A = [[0,32],
    np.zeros((32,32,4), dtype=np.uint8),
    [0,205-64],
    np.zeros((32,32,4), dtype=np.uint8)]

async def WaitForOutput():
    while not outputs or gl["state"]==5:
        await asyncio.sleep(0.1)
    return

def PlayImage(update=False, flip=False):
    img = gl["lastImg"]
    pixelCount = 0
    for x in range(32):
        for y in range(32):
            if x<img.shape[0] and y<img.shape[1]:
                if not flip:
                    Pl()[x][y] = img[x][y]
                else:
                    Pl()[x][y] = img[x][img.shape[1]-1-y]
                if Pl()[x][y][3]>0:
                    pixelCount+=1
    pixelCounts[int(gl["state"]-0.1)] = pixelCount
    #stats[pnames[int(gl["state"]/2-0.1)]]["pixelsPlayed"] += pixelCount
    if update:
        UpdateBattle()

def UpdateBattle():
    global battleimg
    battleimg = np.zeros((32,205,4), dtype=np.uint8)
    for j in range(2):
        i = ((j+gl["turn"])%2) * 2
        for x in range(32):
            for y in range(32):
                posp = (int(P[i][0]+x), int(P[i][1]+y))
                posa = (int(A[i][0]+x), int(A[i][1]+y))
                pp = P[i+1][x][y]
                pa = A[i+1][x][y]

                if A[2][1]-P[0][1]<32 and pp[3]>0:                  #Player damage
                    bip = battleimg[posp[0]][posp[1]]
                    if bip[3]>0:
                        if pp[0] >= pp[1] and pp[0] >= pp[2] and bip[2] >= bip[0] and bip[2] >= bip[1]:
                            P[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                        elif pp[1] >= pp[0] and pp[1] >= pp[2] and bip[0] >= bip[1] and bip[0] >= bip[2]:
                            P[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                        elif pp[2] >= pp[0] and pp[2] >= pp[1] and bip[1] >= bip[0] and bip[1] >= bip[2]:
                            P[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                        else:
                            pixelLoss[i//2] -= 1
                        pixelLoss[i//2] += 1
                if pp[3]>0:
                    battleimg[posp[0]][posp[1]] = P[i+1][x][y] if (gl["state"]==5 or gl["show"]) else np.array([0,0,0,255])
                    
                if posa[1]<0 or posa[1]>=205:
                    continue
                
                if abs(A[0][1]-A[2][1])<32 and pa[3]>0:             #Attack clash
                    bip = battleimg[posa[0]][posa[1]]
                    if bip[3]>0:
                        if pa[0] >= pa[1] and pa[0] >= pa[2] and bip[2] >= bip[0] and bip[2] >= bip[1]:
                            A[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                        elif pa[1] >= pa[0] and pa[1] >= pa[2] and bip[0] >= bip[1] and bip[0] >= bip[2]:
                            A[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                        elif pa[2] >= pa[0] and pa[2] >= pa[1] and bip[1] >= bip[0] and bip[1] >= bip[2]:
                            A[i+1][x][y] = np.zeros(4, dtype=np.uint8)                
                if pa[3]>0:
                    battleimg[posa[0]][posa[1]] = A[i+1][x][y] if (gl["state"]==5 or gl["show"]) else np.array([0,0,0,255])
                    
    outputs.append(battleimg)

def Pl():
    if gl["state"] == 1:
        return P[1]
    if gl["state"] == 2:
        return A[1]
    if gl["state"] == 3:
        return P[3]
    if gl["state"] == 4:
        return A[3]

def SwitchState(st):
    if st != gl["state"]:
        gl["state"] = st
        
    elif gl["state"] < 5:
        gl["state"] += 1
    
    elif gl["state"] == 5:
        gl["state"] = 1
        A[0][1] = 32
        A[2][1] = 205-64
        A[1] = np.zeros((32,32,4), dtype=np.uint8)
        A[3] = np.zeros((32,32,4), dtype=np.uint8)
        P[3] = np.zeros((32,32,4), dtype=np.uint8)
        global pixelLoss
        global pnames
        for i in range(2):
            stats[pnames[i]]["pixelDamage"] += pixelLoss[(i+1)%2]
            stats[pnames[i]]["pixelLoss"]   += pixelLoss[i]
            stats[pnames[i]]["propDamage"]  += pixelLoss[(i+1)%2]/pixelCounts[((i+1)%2)*2]/pixelCounts[i*2+1]
            stats[pnames[i]]["propLoss"]    += pixelLoss[i]/pixelCounts[i*2]/pixelCounts[((i+1)%2)*2+1]
            f = open("stats.txt","w+")
            f.write(json.dumps(stats))
            f.close()
        pixelLoss = [0,0]
        pnames = []
    
    if gl["state"] != 5:
        gl["lastImg"] = imgs["selection"]
        PlayImage(gl["state"]%2==1)

def Battle():
    A[gl["turn"]*2][1] += (0.5-gl["turn"])*2
    gl["turn"] = (gl["turn"]+1)%2
    if abs(A[0][1]-A[2][1])>32 and A[2][1]-P[0][1]>32:
        A[gl["turn"]*2][1] += (0.5-gl["turn"])*2
    if A[0][1] >= 205:     
        SwitchState(gl["state"])
    UpdateBattle()

class GameThread(threading.Thread):
    def run(self):
        global inputs
        global inputstext
        global pnames
        global stats

        with open("stats.txt","r") as f:
            stats = json.loads(f.read())

        test = Image.open("bg.png").convert("RGBA")
        testdata = np.asarray(test, dtype=np.uint8)
        imgs["bg"] = testdata
        test = Image.open("selection.png").convert("RGBA")
        testdata = np.asarray(test, dtype=np.uint8)
        imgs["selection"] = testdata
        SwitchState(gl["state"])
        
        while True:
            time.sleep(0.1)
            if gl["state"] != 5:
                for j in range(len(inputs)):
                    if pnames[len(pnames)-1] not in stats.keys():
                        stats[pnames[len(pnames)-1]] = {"pixelDamage":0,
                                                        "pixelLoss":0,
                                                        "propDamage":0,
                                                        "propLoss":0}
                    gl["lastImg"] = cv2.resize(np.asarray(Image.open(inputs[j]).convert("RGBA")),(32,32),fx=0,fy=0,interpolation=cv2.INTER_NEAREST)
                    param = inputstext[j].lower()
                    param = param.replace("flips","flip userflip")
                    gl["show"] = "hide" not in param
                    if gl["state"]%2==0:
                        PlayImage(False, "flip" in param.split())
                    else:
                        PlayImage(False, "userflip" in param.split())
                    SwitchState(gl["state"])
                inputs = []
                inputstext = []
            else:
                Battle()

gameThread = GameThread(name="PVPThread")
gameThread.start()

