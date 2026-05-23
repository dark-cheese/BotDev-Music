# bot.py
import discord
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import re

# Configurações do yt-dlp
ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'cookiefile': 'cookies.txt',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'ignoreerrors': True,
}

# Classe da fila
class MusicQueue:
    def __init__(self):
        self.queue = []
        self.current = None

    def add(self, item):
        self.queue.append(item)

    def next(self):
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        self.current = None
        return None

    def clear(self):
        self.queue = []
        self.current = None

# Configuração do bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

queues = {}

def get_queue(guild_id):
    if guild_id not in queues:
        queues[guild_id] = MusicQueue()
    return queues[guild_id]

async def play_next(ctx, guild_id):
    queue = get_queue(guild_id)
    next_song = queue.next()
    if next_song:
        queue.current = next_song
        
        def after_callback(error):
            if error:
                print(f'Erro após tocar: {error}')
            asyncio.run_coroutine_threadsafe(play_next(ctx, guild_id), bot.loop)
        
        try:
            # Usa opções mais simples
            source = discord.FFmpegPCMAudio(
                next_song['url'],
                before_options='-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
                options='-vn',
                executable='C:/ffmpeg/bin/ffmpeg.exe'
            )
            ctx.voice_client.play(source, after=after_callback)
            await ctx.send(f"🎵 Tocando agora: **{next_song['title']}**")
        except Exception as e:
            await ctx.send(f"❌ Erro: {str(e)[:100]}")
            await play_next(ctx, guild_id)
    else:
        await asyncio.sleep(300)
        if ctx.voice_client and not ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()
            if guild_id in queues:
                del queues[guild_id]

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} conectado!')

@bot.command()
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send("⚠️ Entre em um canal de voz primeiro!")
        return

    voice_channel = ctx.author.voice.channel
    if not ctx.voice_client:
        await voice_channel.connect()
    elif ctx.voice_client.channel != voice_channel:
        await ctx.voice_client.move_to(voice_channel)

    async with ctx.typing():
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                # Remove parâmetros de playlist do link
                if '&list=' in query:
                    query = query.split('&list=')[0]
                
                info = ydl.extract_info(query, download=False)
                
                # Se for playlist
                if 'entries' in info:
                    playlist_title = info.get('title', 'Playlist')
                    entries = [e for e in info['entries'] if e]
                    
                    if len(entries) > 20:
                        await ctx.send(f"⚠️ Playlist grande! Pegando só 20 músicas.")
                        entries = entries[:20]
                    
                    await ctx.send(f"📋 Adicionando {len(entries)} músicas de **{playlist_title}**...")
                    
                    for entry in entries:
                        # Extrai a URL real do áudio
                        with youtube_dl.YoutubeDL(ydl_opts) as ydl2:
                            song_info = ydl2.extract_info(
                                f"https://www.youtube.com/watch?v={entry['id']}", 
                                download=False
                            )
                            song = {
                                'title': song_info.get('title', 'Desconhecido'),
                                'url': song_info.get('url')
                            }
                            get_queue(ctx.guild.id).add(song)
                    
                    await ctx.send(f"✅ {len(entries)} músicas na fila!")
                    
                    if not ctx.voice_client.is_playing():
                        await play_next(ctx, ctx.guild.id)
                else:
                    # Vídeo único
                    song = {
                        'title': info.get('title', 'Desconhecido'),
                        'url': info.get('url')
                    }
                    get_queue(ctx.guild.id).add(song)
                    
                    if not ctx.voice_client.is_playing():
                        await play_next(ctx, ctx.guild.id)
                    else:
                        queue = get_queue(ctx.guild.id)
                        await ctx.send(f"✅ **{song['title']}** na fila (posição {len(queue.queue)})")
                        
        except Exception as e:
            await ctx.send(f"❌ Erro: {str(e)[:200]}")

@bot.command()
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Pulado!")
    else:
        await ctx.send("❌ Nada tocando.")

@bot.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("⏸️ Pausado.")
    else:
        await ctx.send("❌ Nada tocando.")

@bot.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("▶️ Retomado.")
    else:
        await ctx.send("❌ Nada pausado.")

@bot.command()
async def stop(ctx):
    if ctx.voice_client:
        get_queue(ctx.guild.id).clear()
        ctx.voice_client.stop()
        await ctx.voice_client.disconnect()
        if ctx.guild.id in queues:
            del queues[ctx.guild.id]
        await ctx.send("⏹️ Desconectado.")
    else:
        await ctx.send("❌ Não estou em um canal.")

@bot.command()
async def queue(ctx):
    queue = get_queue(ctx.guild.id)
    if not queue.queue:
        await ctx.send("📭 Fila vazia.")
        return

    msg = "🎶 **Fila:**\n"
    for i, song in enumerate(queue.queue[:10]):
        msg += f"`{i+1}.` {song['title'][:50]}\n"
    
    if len(queue.queue) > 10:
        msg += f"\n*... e mais {len(queue.queue) - 10}*"
    
    await ctx.send(msg)

@bot.command()
async def clear(ctx):
    get_queue(ctx.guild.id).clear()
    await ctx.send("🗑️ Fila limpa!")

# Coloque seu token AQUI
bot.run("MTUwNjgyNDYyOTI5NjE3MzIwNg.Gt-PYr.eXoGyxWCVbp-ZxD5IQJo1PlYtTuvAbFDPKb280")