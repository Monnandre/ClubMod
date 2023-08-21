
from keep_alive import keep_alive
import discord
from discord import app_commands
from discord.ext import commands
from brawlstars import bs_cog
from bs_credentials import BrawlStarsSession

import os, json
import asyncio
import requests, datetime

keep_alive()

public_ip = requests.get('https://bst.alexandremonnie.repl.co').text

if public_ip is None:
    print("Error getting Public IP...")
    exit("No IP")
print("Public IP: ", public_ip)



api_key_bot = str(os.environ['bot_api'])

def get_prefix(client, message):
    if message.guild is None:
        return "!"
    with open('guilds.json', 'r') as f:
        guilds = json.load(f)
    return guilds[str(message.guild.id)]["prefix"]

intents = discord.Intents(messages=True, guilds=True, message_content=True)

bot = commands.Bot(command_prefix=(get_prefix), intents=intents)
bot.remove_command('help')

async def setup():
    await bot.add_cog(bs_cog(bot))


asyncio.run(setup())

@bot.event
async def on_ready():
    print('\nLogged in as :', bot.user.name)
    print('Bot ID :', bot.user.id)
    print('------\n')

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

    with open("credentials.json", "r") as f:
        creds = json.load(f)

    if creds["ip"] == str(public_ip):
        key = creds["key"]
        print("Public Ip already knowed !")
    else:
        print("Getting api key...")
        bs = BrawlStarsSession(str(public_ip))
        await bs.login()
        key_info = await bs.get_api_key()

        if key_info is None:
            print("Failed to retrieve API key.")
            exit("No Key")
            return

        await bs.del_api_key(creds["id"])
        await bs.session.close()

        creds["ip"] = str(public_ip)
        creds["id"] = key_info["id"]
        creds["key"] = key_info["key"]

        with open("credentials.json", "w") as f:
            json.dump(creds, f, indent=4)
        print("API key secured !")
        key = key_info['key']

    bot.get_cog('bs_cog').headers = {"Authorization": f"Bearer {key}"}
    await bot.get_cog('bs_cog').init_bot()

@bot.event
async def on_command_error(ctx, exc):
    response = ""
    if isinstance(exc, commands.CommandNotFound):
        response = f"{get_prefix(None, ctx.message)}help ?"
    elif isinstance(exc, commands.MissingRequiredArgument):
        response = "There is a missing argument."
    elif isinstance(exc, commands.MissingPermissions):
        response = "You need to be an Administrotor to run this command."

    if response:
        msg = await ctx.channel.send(response)
        await asyncio.sleep(5)
        await msg.delete()  # Delete bot's message

bot.run(api_key_bot)
