import discord
import io
import socket
import threading
import asyncio
import cv2
import numpy as np
from matplotlib import pyplot as plt
import PVP
from PIL import Image

settings = {}
f = open("settings.txt", "r")
lines = f.readlines()
for line in lines:
    parts = line.split(" ", 1)
    settings[parts[0]] = parts[1]

f.close()

TOKEN = settings["TOKEN"]
GUILD = None
CHANNEL = None
client = discord.Client()

frames = []

oldmsg = []

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    
    for guild in client.guilds:
        global GUILD
        GUILD = guild
        members = '\n - '.join([member.name for member in guild.members])
        print(f'Guild Members:\n - {members}')
        break
    
    for channel in guild.channels:
        if channel.name == "bot-test":
            global CHANNEL
            CHANNEL = channel

    async for message in channel.history(limit=100):
        await message.delete()

    await SendOutputs()

@client.event
async def on_message(message):
    print(message.author.name + ": " + message.content)
    if message.channel == CHANNEL and message.author != client.user:
        for at in message.attachments:
            if at.height<=512 and at.width<=512 and at.size<1000000:
                saveto = io.BytesIO()
                await at.save(saveto)
                PVP.inputs.append(saveto)
                await message.delete()
                await SendOutputs()
                break
    elif message.author == client.user:
        oldmsg.append(message)

async def SendOutputs():
    global oldmsg
    for m in oldmsg:
        await m.delete()
    oldmsg = []
    await CHANNEL.send("Processing, please wait...")
    print("waiting outputs")
    await PVP.WaitForOutput()

    if len(PVP.outputs)<5:
        for o in PVP.outputs:
            im = Image.fromarray(cv2.resize(AddBG(o)[:,:,:3],(820,256),fx=0,fy=0,interpolation=cv2.INTER_NEAREST))      
            im.save("a.png", "PNG") #sending from buffer not working?
            sendfile = discord.File("a.png", "state.png")
            await CHANNEL.send("", file=sendfile)
    else:
        out = cv2.VideoWriter('result.mp4',cv2.VideoWriter_fourcc(*"H264"), 60, (820,256))
        for i in range(len(PVP.outputs)-2):
            o = PVP.outputs[i]
            out.write(cv2.resize(AddBG(o)[:,:,[2, 1, 0]],(820,256),fx=0,fy=0,interpolation=cv2.INTER_NEAREST))
        out.release()
        await CHANNEL.send("", file=discord.File("result.mp4", "result.mp4"))
        
        o = PVP.outputs[-1]
        im = Image.fromarray(cv2.resize(AddBG(o)[:,:,:3],(820,256),fx=0,fy=0,interpolation=cv2.INTER_NEAREST))      
        im.save("a.png", "PNG") #sending from buffer not working?
        sendfile = discord.File("a.png", "state.png")
        await CHANNEL.send("", file=sendfile)
        
    PVP.outputs = []
    print("got outputs")

def AddBG(s_img):
    l_img = PVP.imgs["bg"].copy()
    y1, y2 = 29, 29+s_img.shape[0]
    x1, x2 = 0, s_img.shape[1]

    alpha_s = s_img[:, :, 3] / 255.0
    alpha_l = 1.0 - alpha_s

    for c in range(0, 3):
        l_img[y1:y2, x1:x2, c] = (alpha_s * s_img[:, :, c] +
                                  alpha_l * l_img[y1:y2, x1:x2, c])
    return l_img
        
client.run(TOKEN)
