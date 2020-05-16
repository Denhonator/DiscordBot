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
import json

settings = {}
f = open("settings.txt", "r")
lines = f.readlines()
for line in lines:
    parts = line.split(" ", 1)
    settings[parts[0]] = parts[1]

f.close()

TOKEN = settings["TOKEN"]
gl = {}
client = discord.Client()

frames = []

oldmsg = []

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    
    for guild in client.guilds:
        gl["GUILD"] = guild
        members = '\n - '.join([member.name for member in guild.members])
        print(f'Guild Members:\n - {members}')
        break
    
    for channel in guild.channels:
        if channel.name == "bot-test":           
            gl["CHANNEL"] = channel
        if channel.name == "roles-request":            
            gl["ROLECHANNEL"] = channel
        if channel.name == "leaderboards":
            gl["LEADERBOARDS"] = channel

    for r in gl["GUILD"].roles:
        if r.name=="PVPBeta":
            gl["PVPROLE"]=r
            break

    async for message in gl["CHANNEL"].history(limit=100):
        await message.delete()

    await SendOutputs()

@client.event
async def on_raw_reaction_add(payload):
    print("reaction: "+ str(payload.emoji))
    if gl["GUILD"].get_channel(payload.channel_id) == gl["ROLECHANNEL"] and str(payload.emoji) == "🤖":
        member = gl["GUILD"].get_member(payload.user_id)
        curroles = member.roles
        if gl["PVPROLE"] not in curroles:
            curroles.append(gl["PVPROLE"])
            await member.edit(roles=curroles)
            print("Added role")

@client.event
async def on_raw_reaction_remove(payload):
    print("reaction: "+ str(payload.emoji))
    if gl["GUILD"].get_channel(payload.channel_id) == gl["ROLECHANNEL"] and str(payload.emoji) == "🤖":
        member = gl["GUILD"].get_member(payload.user_id)
        curroles = member.roles
        if gl["PVPROLE"] in curroles:
            curroles.remove(gl["PVPROLE"])
            await member.edit(roles=curroles)
            print("Removed role")
    
@client.event
async def on_message(message):
    print(message.author.name + ": " + message.content)
    if message.channel == gl["CHANNEL"] and message.author != client.user:
        for at in message.attachments:
            if at.height<=512 and at.width<=512 and at.size<1000000:
                saveto = io.BytesIO()
                saveto2 = io.BytesIO()
                await message.author.avatar_url_as(format="png", size=256).save(saveto2)
                await at.save(saveto)
                PVP.pnames.append(message.author.name)
                PVP.inputstext.append(message.content+(" hide" if at.is_spoiler() else ""))
                PVP.inputstext.append(message.content+(" hide" if at.is_spoiler() else ""))
                PVP.inputs.append(saveto2)
                PVP.inputs.append(saveto)

                await message.delete()
                async with gl["CHANNEL"].typing():
                    await SendOutputs()
                break
    elif message.author == client.user:
        oldmsg.append(message)

async def SendOutputs():
    await DeleteOld()
    print("waiting outputs")
    await PVP.WaitForOutput()

    if len(PVP.outputs)<5:
        for o in PVP.outputs:
            im = Image.fromarray(cv2.resize(AddBG(o)[:,:,:3],(820,256),fx=0,fy=0,interpolation=cv2.INTER_NEAREST))      
            im.save("a.png", "PNG") #sending from buffer not working?
            sendfile = discord.File("a.png", "state.png")
            await gl["CHANNEL"].send("Attach an image:", file=sendfile)
    else:
        out = cv2.VideoWriter('result.mp4',cv2.VideoWriter_fourcc(*"H264"), 60, (820,256))
        for i in range(len(PVP.outputs)-2):
            o = PVP.outputs[i]
            out.write(cv2.resize(AddBG(o)[:,:,[2, 1, 0]],(820,256),fx=0,fy=0,interpolation=cv2.INTER_NEAREST))
        out.release()
        
        await gl["CHANNEL"].send("Result of the battle:", file=discord.File("result.mp4", "result.mp4"))
        
        o = PVP.outputs[-1]
        im = Image.fromarray(cv2.resize(AddBG(o)[:,:,:3],(820,256),fx=0,fy=0,interpolation=cv2.INTER_NEAREST))      
        im.save("a.png", "PNG") #sending from buffer not working?
        sendfile = discord.File("a.png", "state.png")

        await gl["CHANNEL"].send("Attach an image:", file=sendfile)

        edited = False
        async for message in gl["LEADERBOARDS"].history(limit=1):
            await message.edit(content=json.dumps(PVP.stats,sort_keys=True, indent=4))
            edited = True
        if not edited:
            await gl["LEADERBOARDS"].send(content=json.dumps(PVP.stats,sort_keys=True, indent=4))
        
    PVP.outputs = []
    print("got outputs")

async def DeleteOld():
    global oldmsg
    for m in oldmsg:
        await m.delete()
    oldmsg = []

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
