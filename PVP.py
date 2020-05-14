import numpy as np
import cv2
from matplotlib import pyplot as plt
from PIL import Image
import time
import threading
import io
import asyncio

imgs = {"empty":        np.zeros((32,32,4)),
        "selection":    np.zeros((32,32,4)),
        "bg":           np.zeros((32,205,4))}

gl = {"state":      0,
      "lastImg":    np.zeros((32,32,4), dtype=np.uint8),
      "turn":       0}

inputs = []
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

def PlayImage(update=True):
    flip = True if gl["state"]==2 or gl["state"]==4 else False
    img = gl["lastImg"]
    for x in range(32):
        for y in range(32):
            if x<img.shape[0] and y<img.shape[1]:
                if not flip:
                    Pl()[x][y] = img[x][y]
                else:
                    Pl()[x][y] = img[x][img.shape[1]-1-y]
    if update:
        UpdateBattle()

def UpdateBattle():
    global battleimg
    battleimg = np.zeros((32,205,4), dtype=np.uint8)
    for j in range(2):
        i = ((j+gl["turn"])%2) *2
        for x in range(32):
            for y in range(32):
                posp = (int(P[i][0]+x), int(P[i][1]+y))
                posa = (int(A[i][0]+x), int(A[i][1]+y))
                if posa[0]<0:
                    continue
                pp = P[i+1][x][y]
                pa = A[i+1][x][y]
                bip = battleimg[posa[0]][posa[1]]
                if bip[3]>0 and abs(A[0][1]-A[2][1])<32:
                    if pa[0] >= pa[1] and pa[0] >= pa[2] and bip[2] >= bip[0] and bip[2] >= bip[1]:
                        A[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                    elif pa[1] >= pa[0] and pa[1] >= pa[2] and bip[0] >= bip[1] and bip[0] >= bip[2]:
                        A[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                    elif pa[2] >= pa[0] and pa[2] >= pa[1] and bip[1] >= bip[0] and bip[1] >= bip[2]:
                        A[i+1][x][y] = np.zeros(4, dtype=np.uint8)
                if pp[3]>0:
                    battleimg[posp[0]][posp[1]] = pp
                if pa[3]>0:
                    battleimg[posa[0]][posa[1]] = pa
                    
    outputs.append(battleimg)

def Pl():
    if gl["state"] == 1:
        return P[1]
    if gl["state"] == 2:
        return P[3]
    if gl["state"] == 3:
        return A[1]
    if gl["state"] == 4:
        return A[3]

def SwitchState(st):
    if st != gl["state"]:
        gl["state"] = st
        
    elif gl["state"] < 5:
        gl["state"] += 1
    
    elif gl["state"] == 5:
        gl["state"] = 3
        A[3] = np.zeros((32,32,4), dtype=np.uint8)
    
    if gl["state"] != 5:
        gl["lastImg"] = imgs["selection"]
        PlayImage()

def Battle():
    A[gl["turn"]*2][1] += (0.5-gl["turn"])*2
    gl["turn"] = (gl["turn"]+1)%2
    if abs(A[0][1]-A[2][1])>32:
        A[gl["turn"]*2][1] += (0.5-gl["turn"])*2
    if A[0][1]+16 > P[2][1]:
        A[0][1] = 32
        A[2][1] = 205-64
        SwitchState(gl["state"])
    UpdateBattle()

class GameThread(threading.Thread):
    def run(self):
        global inputs

        test = Image.open("bg.png").convert("RGBA")
        testdata = np.asarray(test, dtype=np.uint8)
        imgs["bg"] = testdata
        test = Image.open("selection.png").convert("RGBA")
        testdata = np.asarray(test, dtype=np.uint8)
        imgs["selection"] = testdata
        SwitchState(gl["state"])

        #test = Image.open("ogre32.png").convert("RGBA")
        #inputs.append(test.tobytes())
        
        while True:
            time.sleep(0.1)
            if gl["state"] != 5:
                for i in inputs:
                    gl["lastImg"] = cv2.resize(np.asarray(Image.open(i).convert("RGBA")),(32,32),fx=0,fy=0,interpolation=cv2.INTER_NEAREST)
                    PlayImage(False)
                    SwitchState(gl["state"])
                inputs = []
            else:
                Battle()

gameThread = GameThread(name="PVPThread")
gameThread.start()

