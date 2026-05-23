import yt_dlp

ydl_opts = {
    'format': 'bestaudio/best',
    'quiet': False,
    'no_warnings': False,
    'cookiefile': 'cookies.txt',
    'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

try:
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info("https://www.youtube.com/watch?v=r6zIGXun57U&list=RDr6zIGXun57U&start_radio=1", download=False)
        print(f"✅ Música encontrada: {info.get('title')}")
except Exception as e:
    print(f"❌ Erro: {e}")