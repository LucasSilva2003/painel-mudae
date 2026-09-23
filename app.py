from flask import Flask, render_template_string, request, jsonify
import requests
import time
import threading

app = Flask(__name__)

# ============================================================
# ESTADO GLOBAL E STATUS DO FARM
# ============================================================

status = {
    "rodando": False,
    "quantidade": 0,
    "enviados": 0,
    "comando": "-",
    "mensagem": "Aguardando início...",
    "erro": ""
}

status_lock = threading.Lock()


def atualizar_status(**dados):
    with status_lock:
        status.update(dados)


# ============================================================
# HTML COM LAYOUT DA IMAGEM E PROGRESSO EM TEMPO REAL
# ============================================================

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mudae Farm Central</title>

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
            margin: 30px auto;
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
            font-size: 14px;
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
            font-size: 15px;
        }

        input,
        select {
            background: #4f545c;
            color: white;
        }

        input::placeholder {
            color: #8e9297;
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

        button:disabled {
            background: #747f8d;
            cursor: not-allowed;
        }

        .footer {
            font-size: 12px;
            color: #faa61a;
            margin-top: 20px;
        }

        /* STATUS E BARRA DE PROGRESSO */
        .status-box {
            margin-top: 25px;
            padding: 15px;
            background: #202225;
            border-radius: 8px;
            text-align: center;
        }

        .contador {
            font-size: 28px;
            font-weight: bold;
            color: #ff69b4;
            margin: 10px 0;
        }

        .barra {
            width: 100%;
            height: 16px;
            background: #4f545c;
            border-radius: 8px;
            overflow: hidden;
            margin: 10px 0;
        }

        .progresso {
            height: 100%;
            width: 0%;
            background: #43b581;
            transition: width 0.3s;
        }

        .info-txt {
            font-size: 14px;
            color: #b9bbbe;
            margin: 4px 0;
        }

        .erro {
            color: #f04747;
            font-size: 13px;
        }
    </style>
</head>

<body>

    <div class="container">

        <h2>🌸 Mudae Farm Central</h2>

        <form id="farmForm" onsubmit="iniciarFarm(event)">

            <label>Insira seu Token do Discord (Usuário):</label>
            <input
                type="password"
                id="token"
                name="token"
                placeholder="Cole seu token pessoal aqui"
                required
            >

            <label>ID do Canal do Discord (Onde vai rolar):</label>
            <input
                type="text"
                id="channel_id"
                name="channel_id"
                placeholder="Ex: 123456789012345"
                required
            >

            <label>Quantidade de Rolagens:</label>
            <input
                type="number"
                id="quantidade"
                name="quantidade"
                value="15"
                min="1"
                required
            >

            <label>Categoria:</label>
            <select id="categoria" name="categoria">
                <option value="wa">$wa (Anime Mulheres)</option>
                <option value="wg">$wg (Games Mulheres)</option>

                <option value="m">$m (Misto)</option>

                <option value="all">$all (Tudo)</option>

                <option value="ma">$ma (Anime Homens)</option>

                <option value="mg">$mg (Games Homens)</option>

                <option value="w">$w (Mulheres Geral)</option>

                <option value="h">$h (Homens Geral)</option>
            </select>

            <button type="submit" id="btnIniciar">
                🚀 INICIAR FARM AUTOMÁTICO
            </button>

        </form>

        <div class="status-box">
            <div id="contador" class="contador">0/0</div>

            <div class="barra">
                <div id="progresso" class="progresso"></div>
            </div>

            <p id="mensagem" class="info-txt">Aguardando início...</p>
            <p id="comando" class="info-txt">Comando: -</p>
            <p id="erro" class="erro"></p>
        </div>

        <div class="footer">
            ⚠️ Risco de ban por conta do usuário. Use com moderação.
        </div>

    </div>

    <script>
        async function iniciarFarm(event) {
            event.preventDefault();

            const btn = document.getElementById("btnIniciar");
            btn.disabled = true;

            const formData = new FormData(document.getElementById("farmForm"));

            try {
                const res = await fetch("/iniciar", {
                    method: "POST",
                    body: formData
                });
                const dados = await res.json();

                if (dados.erro) {
                    alert(dados.erro);
                    btn.disabled = false;
                }
            } catch (err) {
                alert("Erro ao conectar ao servidor.");
                btn.disabled = false;
            }
        }

        async function atualizarStatus() {
            try {
                const res = await fetch("/status");
                const dados = await res.json();

                document.getElementById("contador").innerText = dados.enviados + "/" + dados.quantidade;
                document.getElementById("mensagem").innerText = dados.mensagem;
                document.getElementById("comando").innerText = "Comando: " + dados.comando;
                document.getElementById("erro").innerText = dados.erro;

                let porcentagem = 0;
                if (dados.quantidade > 0) {
                    porcentagem = (dados.enviados / dados.quantidade) * 100;
                }
                document.getElementById("progresso").style.width = porcentagem + "%";

                document.getElementById("btnIniciar").disabled = dados.rodando;

            } catch (err) {
                console.error("Erro ao obter status:", err);
            }
        }

        setInterval(atualizarStatus, 1000);
    </script>

</body>

</html>
"""


# ============================================================
# LÓGICA DO SELF-BOT (HTTP REST VIA REQUESTS)
# ============================================================

def enviar_mensagem_http(token, channel_id, conteudo):
    """Realiza a requisição direta de envio à API HTTP do Discord."""
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
            return dados.get("id")

        elif res.status_code == 429:
            # Rate limit do Discord
            dados = res.json()
            espera = dados.get("retry_after", 4.0)
            atualizar_status(mensagem=f"⚠️ Rate limit. Aguardando {espera}s...")
            print(f"⚠️ Rate limit detectado. Aguardando {espera}s...", flush=True)
            time.sleep(float(espera) + 0.5)
        else:
            raise Exception(f"HTTP {res.status_code}: {res.text}")


def executar_farm_thread(token, channel_id, quantidade, categoria):
    comando = categoria if categoria.startswith("$") else f"${categoria}"

    atualizar_status(
        rodando=True,
        quantidade=quantidade,
        enviados=0,
        comando=comando,
        mensagem="Iniciando farm...",
        erro=""
    )

    print()
    print("=" * 50, flush=True)
    print(f"🚀 Iniciando farm de {quantidade} rolls...", flush=True)
    print(f"🎲 Comando: {comando}", flush=True)
    print("=" * 50, flush=True)

    try:
        enviar_mensagem_http(token, channel_id, f"🤖 *Iniciando farm de {quantidade} rolls...*")
    except Exception:
        pass

    time.sleep(3.0)

    for numero in range(1, quantidade + 1):
        print(f"▶️ Tentando enviar {numero}/{quantidade}", flush=True)
        atualizar_status(mensagem=f"Enviando roll {numero}/{quantidade}...")

        try:
            msg_id = enviar_mensagem_http(token, channel_id, comando)

            atualizar_status(enviados=numero, mensagem=f"Roll {numero}/{quantidade} enviado com sucesso!")
            print(f"✅ Enviado {numero}/{quantidade} | ID: {msg_id}", flush=True)

        except Exception as e:
            erro_msg = f"{type(e).__name__}: {e}"
            atualizar_status(erro=f"Erro no roll {numero}: {erro_msg}")
            print(f"❌ ERRO no envio {numero}: {erro_msg}", flush=True)

        if numero < quantidade:
            print("⏳ Aguardando 4 segundos...", flush=True)
            time.sleep(4)

    print("🏁 LOOP TERMINADO", flush=True)

    try:
        enviar_mensagem_http(token, channel_id, f"✅ *Farm concluído! {quantidade} rolls foram enviados.*")
    except Exception:
        pass

    atualizar_status(rodando=False, mensagem="✅ Farm Concluído!")


# ============================================================
# ROTAS DA APLICAÇÃO FLASK
# ============================================================

@app.route("/")
def index():
    return render_template_string(HTML_PAGINA)


@app.route("/status")
def obter_status():
    with status_lock:
        return jsonify(status)


@app.route("/iniciar", methods=["POST"])
def iniciar_farm():
    with status_lock:
        if status["rodando"]:
            return jsonify({"erro": "O farm já está em execução!"})

    token = request.form.get("token", "").strip()
    channel_id = request.form.get("channel_id", "").strip()
    categoria = request.form.get("categoria", "wa").strip()

    try:
        quantidade = int(request.form.get("quantidade", "15"))
    except (ValueError, TypeError):
        return jsonify({"erro": "Quantidade inválida."})

    if quantidade < 1:
        return jsonify({"erro": "A quantidade precisa ser maior que 0."})

    if not token or not channel_id:
        return jsonify({"erro": "Token e ID do Canal são obrigatórios."})

    threading.Thread(
        target=executar_farm_thread,
        args=(token, channel_id, quantidade, categoria),
        daemon=True
    ).start()

    return jsonify({"sucesso": True})


# ============================================================
# EXECUÇÃO DO FLASK
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
    
