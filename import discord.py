import discord
from discord.ext import commands
import asyncio
import numpy as np
import wave
import io
import os
import threading
from flask import Flask, request, redirect, render_template_string

# ----------------------------
# CONFIG
# ----------------------------

DISCORD_TOKEN = os.getenv("MTQ2MzU3MTg2NTA0MDcyMDA0NQ.Gvp85i.zN2cB0h_caImDHLzlJx1DD8vsgs3XvCq3mc1m0")
PORT = int(os.getenv("PORT", 10000))

# ----------------------------
# BOT SETUP
# ----------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

MESSAGE_LOGS = []  # stores last messages


# ----------------------------
# AUDIO
# ----------------------------

def generate_tone(frequency=1000, duration=2, sample_rate=44100):
    t = np.linspace(0, duration, int(sample_rate * duration))
    tone = np.sin(2 * np.pi * frequency * t)
    tone = (tone * 32767).astype(np.int16)

    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(tone.tobytes())

    buffer.seek(0)
    return buffer


# ----------------------------
# BOT EVENTS
# ----------------------------

@bot.event
async def on_ready():
    print(f"[BOT] Logged in as {bot.user} ({bot.user.id})")


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    log_entry = f"[{message.guild}] #{message.channel} | {message.author}: {message.content}"
    print(log_entry)

    MESSAGE_LOGS.append(log_entry)
    MESSAGE_LOGS[:] = MESSAGE_LOGS[-100:]  # keep last 100 only

    # -------- VOICE FEATURE --------
    if message.guild and message.author.voice and message.author.voice.channel:
        channel = message.author.voice.channel
        voice_client = discord.utils.get(bot.voice_clients, guild=message.guild)

        if not voice_client:
            voice_client = await channel.connect()

        tone_buffer = generate_tone(1500, 2)
        with open("temp.wav", "wb") as f:
            f.write(tone_buffer.read())

        voice_client.play(discord.FFmpegPCMAudio("temp.wav"))
        while voice_client.is_playing():
            await asyncio.sleep(0.1)

        await voice_client.disconnect()

    await bot.process_commands(message)


# ----------------------------
# WEB PANEL
# ----------------------------

app = Flask(__name__)

HTML = """
<!DOCTYPE html>
<html>
<head>
<title>Discord Bot Panel</title>
<meta http-equiv="refresh" content="3">
<style>
body { background:#0e0e11; color:white; font-family:consolas; padding:20px; }
.box { background:#15151c; padding:15px; border-radius:8px; margin-bottom:15px; }
input, textarea, button { width:100%; padding:10px; margin-top:8px; background:#1e1e26; color:white; border:none; border-radius:6px; }
button { background:#6a4cff; cursor:pointer; }
pre { white-space:pre-wrap; }
</style>
</head>
<body>

<h2>Discord Bot Control Panel</h2>

<div class="box">
<h3>Send message as bot</h3>
<form action="/send" method="post">
<input name="channel_id" placeholder="Channel ID" required>
<textarea name="message" placeholder="Message..." required></textarea>
<button type="submit">Send</button>
</form>
</div>

<div class="box">
<h3>Live logs</h3>
<pre>{{logs}}</pre>
</div>

</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML, logs="\n".join(MESSAGE_LOGS))


@app.route("/send", methods=["POST"])
def send():
    channel_id = int(request.form["channel_id"])
    msg = request.form["message"]

    async def send_msg():
        channel = bot.get_channel(channel_id)
        if channel:
            await channel.send(msg)

    asyncio.run_coroutine_threadsafe(send_msg(), bot.loop)
    return redirect("/")


# ----------------------------
# START BOTH
# ----------------------------

def run_web():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_web).start()

bot.run(DISCORD_TOKEN)