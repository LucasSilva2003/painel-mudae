from flask import Flask, render_template_string, request
import discord
from discord.ext import commands
import asyncio
import threading
import traceback

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

def executar_farm_thread(token, channel_id, quantidade, categoria):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = commands.Bot(
        command_prefix="!",
        self_bot=True,
        heartbeat_timeout=120.0
    )

    async def iniciar_loop_envio():
        await bot.wait_until_ready()
        print(f"📡 Conectado como {bot.user.name}. Iniciando envio contínuo...")

        try:
            channel = bot.get_channel(int(channel_id))
            if channel is None:
                channel = await bot.fetch_channel(int(channel_id))

            comando = categoria if categoria.startswith("$") else f"${categoria}"
            await channel.send(f"🤖 *Painel ativo. Processando {quantidade} rolls...*")

            for numero in range(1, quantidade + 1):
                enviado = False
                while not enviado:
                    try:
                        await channel.send(comando)
                        print(f"Roll {numero}/{quantidade} enviado com sucesso")
                        enviado = True
                        # Pausa de 4 segundos
                        await asyncio.sleep(4.0)

                    except discord.errors.HTTPException as e:
                        if e.status == 429:
                            print(f"⚠️ Rate limit no roll {numero}. Aguardando 8s...")
                            await asyncio.sleep(8.0)
                        else:
                            print(f"⚠️ Erro HTTP ({e.status}) no roll {numero}: {e}")
                            await asyncio.sleep(4.0)

                    except Exception as err:
                        print(f"⚠️ Instabilidade de conexão no roll {numero}. Reagendando envio...")
                        await asyncio.sleep(5.0)

            await channel.send("✅ *Farm concluído com sucesso! Desconectando.*")

        except Exception as fatal_err:
            print(f"❌ Erro na tarefa de envio: {fatal_err}")
            traceback.print_exc()
        finally:
            await bot.close()

    @bot.event
    async def on_ready():
        # Dispara o loop de envio em background assim que o bot conecta
        bot.loop.create_task(iniciar_loop_envio())

    try:
        loop.run_until_complete(bot.start(token))
    except Exception as e:
        print(f"❌ Sessão encerrada: {e}")
    finally:
        loop.close()

@app.route('/')
def index():
    return render_template_string(HTML_PAGINA)

@app.route('/iniciar', methods=['POST'])
def iniciar_farm():
    token = request.form.get('token', '').strip()
    channel_id = request.form.get('channel_id', '').strip()
    
    try:
        quantidade = int(request.form.get('quantidade', 15))
    except (ValueError, TypeError):
        quantidade = 15

    categoria = request.form.get('categoria', 'wa')
    
    threading.Thread(
        target=executar_farm_thread, 
        args=(token, channel_id, quantidade, categoria), 
        daemon=True
    ).start()
    
    return "<h3>🚀 Farm Iniciado! Olhe o canal do seu Discord.</h3><br><a href='/'>Voltar</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
