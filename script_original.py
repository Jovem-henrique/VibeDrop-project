import yt_dlp

print("Escolha o formato de saída:")
print("1 - MP3 (Alta qualidade - 320 kbps)")
print("2 - M4A (Perfeito para WhatsApp e celular)")

escolha = input("Digite 1 ou 2: ")

# Configurações baseadas na sua escolha
if escolha == '1':
    opcoes = {
        'format': 'bestaudio',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '320', # MP3 no talo da qualidade!
        }],
        'outtmpl': '%(title)s.%(ext)s',
    }
    print("\nBaixando e convertendo para MP3 320kbps...")
else:
    opcoes = {
        'format': '140',
        'outtmpl': '%(title)s.m4a',
    }
    print("\nBaixando em M4A puro...")

url = input('Cole aqui sua URL: ')

try:
    with yt_dlp.YoutubeDL(opcoes) as ydl:
        ydl.download([url])
    print("\nSucesso! Download concluído na pasta do projeto.")
except Exception as e:
    print(f"\nOcorreu um erro: {e}")