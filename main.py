import os
import asyncio
import yt_dlp
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = '8583335986:AAHZc6b_KPmMMXDgCwMLKLTeCKqgAsRaBfA'
FFMPEG_PATH = r'C:\ffmpeg\bin' # <--- VERIFICA QUE ESTA SEA TU RUTA

async def procesar_descarga(url, update: Update):
    """Maneja la lógica de descarga y envío con reintentos y pausas"""
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'ffmpeg_location': FFMPEG_PATH,
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'ignoreerrors': True, # No se detiene si un video de la lista da error
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }, {
            'key': 'FFmpegMetadata',
        }],
        # Optimización para conexiones rápidas
        'nocheckcertificate': True,
        'concurrent_fragment_downloads': 5, 
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 1. Obtener información
            info = ydl.extract_info(url, download=False)
            
            if 'entries' in info:
                # Filtrar entradas nulas y crear lista
                canciones = [e for e in info['entries'] if e is not None]
                total = len(canciones)
                await update.message.reply_text(f"📂 Playlist detectada: {total} canciones.\n🚀 Iniciando descarga a máxima velocidad...")
            else:
                canciones = [info]
                total = 1

            # 2. Bucle de procesamiento
            for i, cancion in enumerate(canciones, 1):
                try:
                    # Usamos el link directo del video
                    video_url = cancion.get('webpage_url') or cancion.get('url')
                    
                    # Descarga real
                    data = ydl.extract_info(video_url, download=True)
                    # Construir nombre del archivo (yt-dlp cambia la extensión a mp3 al final)
                    temp_name = ydl.prepare_filename(data)
                    archivo_mp3 = os.path.splitext(temp_name)[0] + ".mp3"

                    # 3. Enviar a Telegram
                    if os.path.exists(archivo_mp3):
                        with open(archivo_mp3, 'rb') as audio:
                            await update.message.reply_audio(
                                audio, 
                                title=cancion.get('title'),
                                caption=f"🎵 {i}/{total}"
                            )
                        os.remove(archivo_mp3) # Limpiar inmediatamente
                    
                    # 4. PAUSA DE SEGURIDAD (Evita el baneo de Telegram)
                    # Con tu internet, esto permite que los servidores de Telegram respiren.
                    await asyncio.sleep(1.5)

                except Exception as e:
                    await update.message.reply_text(f"⚠️ Error en canción {i}: {cancion.get('title', 'Desconocida')}")
                    continue

            await update.message.reply_text("✅ ¡Todo listo! Todas las canciones procesadas.")

    except Exception as e:
        await update.message.reply_text(f"❌ Error crítico en la lista: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text
    
    # Detectar si es link o búsqueda
    if "youtube.com" in user_input or "youtu.be" in user_input:
        await procesar_descarga(user_input, update)
    else:
        # Si envían texto, busca el primer resultado en YouTube
        await update.message.reply_text(f"🔍 Buscando '{user_input}'...")
        await procesar_descarga(f"ytsearch1:{user_input}", update)

def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    print("Bot activo y esperando música...")
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()