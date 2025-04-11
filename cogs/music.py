import discord
from discord.ext import commands
import yt_dlp

from datetime import timedelta

import asyncio

# Set up ytdl format
format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "verbose": True,
    "no_warnings": False,
    "default_search": "auto",
}

# Set up ffmpeg options
ffmpeg_options = {
    "options": "-vn",
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}

# Initialize the player
ytdl = yt_dlp.YoutubeDL(format_options)


# Set up the music source for YTDL
# In this case, the data will usually be from a youtube url
class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)

        self.data = data

        self.title = data.get("title")
        self.url = data.get("url")
        self.duration = timedelta(seconds=data.get("duration"))

    @classmethod
    async def from_url(cls, url, *, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)
        )

        if "entries" in data:
            data = data["entries"][0]

        song = data["url"]
        return cls(discord.FFmpegPCMAudio(song, **ffmpeg_options), data=data)


# Set up the music commands
class Music(commands.Cog):
    # Initialize the important variables
    def __init__(self, bot):
        self.bot = bot

        self.queue = []

        self.vc = None
        self.bot_channel = None

    # Pops a song from the queue and plays it. If there are no songs left
    # in the queue, the bot will disconnect.
    async def play_next(self):
        if len(self.queue) > 0:
            current_song = self.queue[0]

            self.queue.pop(0)

            await self.bot_channel.send(
                f"Now playing: **{current_song.title}** [{current_song.duration}]."
            )
            self.vc.play(
                current_song,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(), self.bot.loop
                ),
            )
        else:
            await self.bot_channel.send(
                "No more songs in the queue. Disconnecting now."
            )
            await self.vc.disconnect()
            self.vc = None

    # Finds a youtube source from the inputted information and adds it to the
    # music queue. If the bot is not playing music, start playing music.
    @commands.command(
        name="play", aliases=["p"], help="Plays a song from Youtube via search query or link."
    )
    async def play(self, ctx, *, url):
        if ctx.author.voice.channel == self.vc.channel:
            async with ctx.typing():
                song = await YTDLSource.from_url(url, loop=self.bot.loop)
                await ctx.send(
                    f"Song **{song.title}** [{song.duration}] has been added to the queue."
                )
                self.queue.append(song)
                if self.vc.is_playing() == False:
                    await self.play_next()
        else:
            await ctx.send(
                "You cannot use the bot if it is in a different voice channel."
            )

    # Stop the voice client and play the next song.
    @commands.command(name="skip", help="Skips the song currently being played.")
    async def skip(self, ctx):
        if self.vc:
            if ctx.author.voice.channel == self.vc.channel:
                self.vc.stop()
            else:
                await ctx.send(
                    "You cannot use the bot if it is in a different voice channel."
                )
        else:
            await ctx.send("The bot is not currently playing music.")

    # Loop through the music queue and create an embed of all the songs
    # in the music queue.
    @commands.command(name="queue", help="Displays the current music queue.")
    async def queue(self, ctx):
        queue_text = ""
        for i in range(0, len(self.queue)):
            if i > 9:
                break
            queue_text += (
                f"{i + 1} - **{self.queue[i].title}** [{self.queue[i].duration}]" + "\n"
            )

        if queue_text == "":
            queue_text = "There are no songs in the queue."
        queue_embed = discord.Embed(
            title=f"There are {len(self.queue)} songs in queue.", description=queue_text
        )
        await ctx.send(embed=queue_embed)

    # Pop the song at the specified index from the queue
    @commands.command(
        name="remove", help="Removes the song at the specified index from the queue."
    )
    async def remove(self, ctx, ind: int):
        arr_ind = ind - 1

        if arr_ind < 0 or arr_ind > len(self.queue) - 1:
            await ctx.send("Your inputted number is out of bounds")
        else:
            removed_song = self.queue[arr_ind]

            self.queue.pop(arr_ind)

            await ctx.send(
                f"Removed **{removed_song.title}** [{removed_song.duration}] from the queue."
            )

    # Clears the queue and disconnects the bot from the channel
    @commands.command(
        name="stop", help="Clears the music queue and disconnects the bot."
    )
    async def stop(self, ctx):
        if self.vc:
            if ctx.author.voice.channel == self.vc.channel:
                self.queue = []
                await self.vc.disconnect()
                self.vc = None
            else:
                await ctx.send(
                    "You cannot use the bot if it is in a different voice channel."
                )
        else:
            await ctx.send("The bot is not currently playing music.")

    # Ensures the bot is connected to a voice channel before attempting
    # to play music
    @play.before_invoke
    async def ensure_connection(self, ctx):
        if self.vc is None:
            if ctx.author.voice:
                self.vc = await ctx.author.voice.channel.connect()
                self.bot_channel = ctx.channel
            else:
                await ctx.send("You are not connected to a voice channel.")


# Setup the cog
async def setup(bot):
    await bot.add_cog(Music(bot))
