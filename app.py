from flask import Flask, render_template_string, request
import discord
from discord.ext import commands
import asyncio
import threading

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
    try:
        quantidade = int(quantidade)
    except (TypeError, ValueError):
        print(f"Quantidade inválida: {quantidade!r}")
        return

    if quantidade <= 0:
        print("A quantidade deve ser maior que zero.")
        return

    print(f"Executando {quantidade} rolls")

    bot = commands.Bot(
        command_prefix="!",
        self_bot=True,
        heartbeat_timeout=60.0
    )

    @bot.event
    async def on_ready():
        print(f"📡 Conectado como {bot.user.name}")
        channel = bot.get_channel(int(channel_id))

        if channel is None:
            try:
                channel = await bot.fetch_channel(int(channel_id))
            except Exception as e:
                print(f"❌ Canal não encontrado: {e}")
                await bot.close()
                return

        comando = categoria if categoria.startswith("$") else f"${categoria}"
        await channel.send(f"🤖 *Conectado ao painel web. Iniciando farm de {quantidade} rolls...*")

        for numero in range(1, quantidade + 1):
            try:
                await channel.send(comando)
                print(f"Roll {numero}/{quantidade} enviado por {bot.user.name}")
                
                # Delay de 4 segundos entre todas as mensagens
                await asyncio.sleep(4)

            except Exception as erro:
                print(f"⚠️ Erro no roll {numero}: {erro}")
                break

        await channel.send("✅ *Farm concluído com sucesso! Desconectando.*")
        await bot.close()

    try:
        await bot.start(token)
    except Exception as e:
        print(f"❌ Erro ao iniciar o bot: {e}")

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
    token = request.form.get('token', '').strip()
    channel_id = request.form.get('channel_id', '').strip()
    
    # Garantia da conversão correta da quantidade recebida pelo formulário
    try:
        quantidade = int(request.form.get('quantidade', 15))
    except (ValueError, TypeError):
        quantidade = 15

    categoria = request.form.get('categoria', 'wa')
    
    threading.Thread(
        target=start_bot_thread, 
        args=(token, channel_id, quantidade, categoria), 
        daemon=True
    ).start()
    
    return "<h3>🚀 Farm Iniciado! Olhe o canal do seu Discord.</h3><br><a href='/'>Voltar</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
