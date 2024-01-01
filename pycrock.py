import logging
import os

import discord

from dotenv import load_dotenv
from discord.ext import commands

# Load the environment variables
load_dotenv()

# Setup the logger
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")

# Initialize the intents the bot has access to
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

# Initialize the bot
bot = commands.Bot(
    command_prefix="?", description="PyCrock Discord Bot", intents=intents
)


# Load cogs into the bot
@bot.event
async def setup_hook():
    for file in os.listdir("./cogs"):
        if file.endswith(".py"):
            await bot.load_extension(f"cogs.{file[:-3]}")
            print(f"Loaded Cog: {file[:-3]}")


# Initialization event
@bot.event
async def on_ready():
    print(f"We have logged in as {bot.user}.")
    print("-----")
    await bot.change_presence(activity=discord.Game(os.getenv("ACTIVITY")))


# When a member joins the server
@bot.event
async def on_member_join(member):
    user_role = member.guild.get_role(int(os.getenv("USER_ROLE")))
    await member.add_roles(user_role)


# Run the bot
bot.run(token=os.getenv("BOT_TOKEN"), log_handler=handler, log_level=logging.DEBUG)
