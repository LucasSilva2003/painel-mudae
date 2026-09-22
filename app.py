from flask import Flask, render_template_string, request, jsonify
import discord
from discord.ext import commands
import asyncio
import threading
import random

app = Flask(__name__)

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mudae Auto-Farm Painel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #23272a; color: white; text-align: center; padding: 20px; }
        .container { max-width: 400px; background: #2c2f33; padding: 30px; border-radius: 10px; margin: 50px auto; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { color: #ff69b4; margin-bottom: 20px; }
        input, select, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 5px; border: none; box-sizing: border-box; font-size: 16px; }
        input, select { background: #4f545c; color: white; }
        button { background: #43b581; color: white; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background: #3ca374; }
        .footer { font-size: 12px; color: #7289da; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🌸 Mudae Farm Central</h2>
        <form action="/iniciar" method="POST">
            <label>Insira seu Token do Discord (Usuário):</label>
            <input type="password" name="token" placeholder="Cole seu token pessoal aqui" required>
            
            <label>ID do Canal do Discord (Onde vai rolar):</label>
            <input type="text" name="channel_id" placeholder="Ex: 123456789012345" required>
            
            <label>Quantidade de Rolagens:</label>
            <input type="number" name="quantidade" value="15" min="1" required>
            
            <label>Categoria:</label>
            <select name="categoria">
                <option value="wa">$wa (Anime Mulheres)</option>
                <option value="wg">$wg (Games Mulheres)</option>
                <option value="m">$m (Misto)</option>
                <option value="all">$all (Tudo)</option>
                <option value="ma">$ma (Anime Homens)</option>
                <option value="mg">$mg (Games Homens)</option>
                <option value="w">$w (Mulheres Geral)</option>
                <option value="h">$h (Homens Geral)</option>
            </select>
            
            <button type="submit">🚀 INICIAR FARM AUTOMÁTICO</button>
        </form>
        <div class="footer">⚠️ Risco de ban por conta do usuário. Use com moderação.</div>
    </div>
</body>
</html>
"""

async def rodar_selfbot_task(token, channel_id, quantidade, categoria):
    bot = commands.Bot(command_prefix="!", self_bot=True, heartbeat_timeout=60.0)
    
    @bot.event
    async def on_ready():
        print(f"📡 Conectado ao selfbot de {bot.user.name}")
        channel = bot.get_channel(int(channel_id))
        if not channel:
            print("❌ Canal não encontrado.")
            await bot.close()
            return
            
        # Garante que o comando tenha exatamente uma $ no início
        comando = categoria if categoria.startswith("$") else f"${categoria}"
        
        await channel.send(f"🤖 *Conectado ao painel web. Iniciando farm de {quantidade} rolls...*")
        
        us_utilizado = False
        i = 0
        
        while i < quantidade:
            try:
                await channel.send(comando)
                i += 1
                print(f"Roll {i}/{quantidade} enviado por {bot.user.name}")
                
                # Aguarda a resposta da Mudae
                await asyncio.sleep(random.uniform(2.5, 4.0))
                
                # Verifica se as rolagens acabaram nas últimas mensagens
                rolagens_esgotadas = False
                async for msg in channel.history(limit=5):
                    if msg.author.id == 432610292342587392: # ID da Mudae
                        conteudo = (msg.content or "").lower()
                        if msg.embeds:
                            for embed in msg.embeds:
                                if embed.description:
                                    conteudo += " " + embed.description.lower()
                                if embed.title:
                                    conteudo += " " + embed.title.lower()
                                if embed.footer and embed.footer.text:
                                    conteudo += " " + embed.footer.text.lower()
                        
                        # Termos de limite da Mudae
                        if "são limitadas a" in conteudo or "the roulette is limited to" in conteudo or "0/1" in conteudo:
                            rolagens_esgotadas = True
                            break

                if rolagens_esgotadas:
                    if not us_utilizado:
                        print("⚡ Tentando usar $us...")
                        await channel.send("$us")
                        us_utilizado = True
                        await asyncio.sleep(3.0)
                    else:
                        print("🛑 Rolagens totalmente esgotadas.")
                        await channel.send("🛑 *Meus rolls acabaram definitivamente. Desconectando.*")
                        break
                
                # Pausa estratégica a cada 10 envios
                if i % 10 == 0 and i < quantidade:
                    print("☕ Pausa de descanso de 10 segundos...")
                    await asyncio.sleep(10.0)

            except discord.errors.HTTPException as e:
                if e.status == 429:
                    print("⚠️ Rate limit detectado. Aguardando 15s...")
                    await asyncio.sleep(15.0)
                else:
                    print(f"⚠️ Erro HTTP: {e}")
                    break
            except Exception as e:
                print(f"⚠️ Erro inesperado: {e}")
                break
                
        await channel.send("✅ *Farm concluído com sucesso! Desconectando.*")
        await bot.close()

def start_bot_thread(token, channel_id, quantidade, categoria):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(rodar_selfbot_task(token, channel_id, quantidade, categoria))
    finally:
        loop.close()

@app.route('/')
def index():
    return render_template_string(HTML_PAGINA)

@app.route('/iniciar', methods=['POST'])
def iniciar_farm():
    token = request.form.get('token')
    channel_id = request.form.get('channel_id')
    quantidade = int(request.form.get('quantidade', 15))
    categoria = request.form.get('categoria', 'wa')
    
    threading.Thread(target=start_bot_thread, args=(token, channel_id, quantidade, categoria), daemon=True).start()
    return "<h3>🚀 Farm Iniciado! Olhe o canal do seu Discord, a conta já deve estar rolando. Pode fechar esta página se quiser!</h3><br><a href='/'>Voltar</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
