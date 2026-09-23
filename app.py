from flask import Flask, render_template_string, request
import requests
import time
import threading

app = Flask(__name__)


# ============================================================
# PÁGINA HTML PRINCIPAL
# ============================================================

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">

    <title>Mudae Auto-Farm Painel</title>

    <style>
        body {
            font-family: Arial, sans-serif;
            background: #23272a;
            color: white;
            text-align: center;
            padding: 20px;
        }

        .container {
            max-width: 400px;
            background: #2c2f33;
            padding: 30px;
            border-radius: 10px;
            margin: 50px auto;
            box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        }

        h2 {
            color: #ff69b4;
            margin-bottom: 20px;
        }

        label {
            display: block;
            text-align: left;
            margin-top: 15px;
            margin-bottom: 5px;
        }

        input,
        select,
        button {
            width: 100%;
            padding: 12px;
            margin: 5px 0;
            border-radius: 5px;
            border: none;
            box-sizing: border-box;
            font-size: 16px;
        }

        input,
        select {
            background: #4f545c;
            color: white;
        }

        button {
            background: #43b581;
            color: white;
            font-weight: bold;
            cursor: pointer;
            transition: 0.3s;
            margin-top: 20px;
        }

        button:hover {
            background: #3ca374;
        }

        .footer {
            font-size: 12px;
            color: #7289da;
            margin-top: 20px;
        }
    </style>
</head>

<body>

    <div class="container">

        <h2>🌸 Mudae Farm Central</h2>

        <form action="/iniciar" method="POST">

            <label>Insira seu Token do Discord (Usuário):</label>

            <input
                type="password"
                name="token"
                placeholder="Cole seu token pessoal aqui"
                required
            >


            <label>ID do Canal do Discord (Onde vai rolar):</label>

            <input
                type="text"
                name="channel_id"
                placeholder="Ex: 123456789012345"
                required
            >


            <label>Quantidade de Rolagens:</label>

            <input
                type="number"
                name="quantidade"
                value="15"
                min="1"
                required
            >


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


            <button type="submit">
                🚀 INICIAR FARM AUTOMÁTICO
            </button>

        </form>


        <div class="footer">
            ⚠️ Risco de ban por conta do usuário. Use com moderação.
        </div>

    </div>

</body>

</html>
"""


# ============================================================
# LÓGICA DE ENVIO VIA API HTTP (SELF-BOT)
# ============================================================

def enviar_mensagem_com_resposta(token, channel_id, conteudo):
    """Realiza o envio direto à API HTTP do Discord e retorna o ID da mensagem se bem-sucedido."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    payload = {"content": conteudo}
    
    while True:
        res = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if res.status_code in [200, 201]:
            dados = res.json()
            return True, dados.get("id")
        
        elif res.status_code == 429:
            # Rate limit atingido
            dados = res.json()
            espera = dados.get("retry_after", 4.0)
            print(f"⚠️ Rate limit detectado. Aguardando {espera}s para tentar novamente...")
            time.sleep(float(espera) + 0.5)
        else:
            raise Exception(f"Erro HTTP {res.status_code}: {res.text}")


def executar_farm_thread(token, channel_id, quantidade, categoria):
    comando = categoria if categoria.startswith("$") else f"${categoria}"
    
    print()
    print("=" * 50)
    print(f"🚀 Iniciando farm de {quantidade} rolls...")
    print(f"🎲 Comando: {comando}")
    print("=" * 50)

    try:
        enviar_mensagem_com_resposta(token, channel_id, f"🤖 *Iniciando farm de {quantidade} rolls...*")
    except Exception:
        pass

    time.sleep(3.0)

    # --------------------------------------------------------
    # LOOP COM OS PRINTS SOLICITADOS
    # --------------------------------------------------------
    for numero in range(1, quantidade + 1):
        print(f"ANTES DO ENVIO: {numero}/{quantidade}")

        try:
            sucesso, msg_id = enviar_mensagem_com_resposta(token, channel_id, comando)
            print(f"ENVIADO: {numero}/{quantidade} - ID {msg_id}")
        except Exception as e:
            print(f"ERRO NO ENVIO {numero}: {e}")

        time.sleep(4)

    print("FOR TERMINOU")

    try:
        enviar_mensagem_com_resposta(token, channel_id, f"✅ *Farm concluído! {quantidade} rolls foram enviados.*")
    except Exception:
        pass


# ============================================================
# ROTAS FLASK
# ============================================================

@app.route("/")
def index():
    return render_template_string(HTML_PAGINA)


@app.route("/iniciar", methods=["POST"])
def iniciar_farm():

    token = request.form.get("token", "").strip()
    channel_id = request.form.get("channel_id", "").strip()
    categoria = request.form.get("categoria", "wa").strip()

    try:
        quantidade = int(request.form.get("quantidade", "15"))
    except (ValueError, TypeError):
        return "<h3>❌ Quantidade inválida.</h3><a href='/'>Voltar</a>"

    if quantidade < 1:
        return "<h3>❌ A quantidade precisa ser maior que 0.</h3><a href='/'>Voltar</a>"

    if not token or not channel_id:
        return "<h3>❌ Token e ID do Canal são obrigatórios.</h3><a href='/'>Voltar</a>"

    threading.Thread(
        target=executar_farm_thread,
        args=(token, channel_id, quantidade, categoria),
        daemon=True
    ).start()

    comando_exibicao = categoria if categoria.startswith("$") else f"${categoria}"

    return f"""
    <!DOCTYPE html>
    <html lang="pt-BR">
    <head>
        <meta charset="UTF-8">
        <title>Farm iniciado</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #23272a;
                color: white;
                text-align: center;
                padding: 50px;
            }}
            .box {{
                background: #2c2f33;
                padding: 30px;
                border-radius: 10px;
                max-width: 450px;
                margin: auto;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            }}
            a {{
                color: #ff69b4;
                text-decoration: none;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="box">
            <h2>🚀 Farm iniciado!</h2>
            <p>Quantidade solicitada: <strong>{quantidade}</strong></p>
            <p>Comando: <strong>{comando_exibicao}</strong></p>
            <br>
            <a href="/">← Voltar</a>
        </div>
    </body>
    </html>
    """


# ============================================================
# INICIAR FLASK
# ============================================================

if __name__ == "__main__":
    print()
    print("=" * 50)
    print("🌸 MUDAE FARM CENTRAL")
    print("=" * 50)
    print("🌐 Painel: http://localhost:5000")
    print("=" * 50)
    print()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )
    
