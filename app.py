from flask import Flask, render_template_string, request, jsonify
import requests
import time
import json
import redis
import threading
import os

app = Flask(__name__)

# Conexão ao Redis interno do Render
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    db = redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception as e:
    db = None

def atualizar_status(rodando, enviados, quantidade, mensagem, pausado=False):
    dados = {
        "rodando": rodando,
        "enviados": enviados,
        "quantidade": quantidade,
        "mensagem": mensagem,
        "pausado": pausado
    }
    if db:
        try:
            db.set("farm_status", json.dumps(dados))
        except Exception:
            pass

def enviar_mensagem(token, channel_id, conteudo):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    
    while True:
        res = requests.post(url, headers=headers, json={"content": conteudo}, timeout=10)
        if res.status_code in [200, 201]:
            return res.json().get("id")
        elif res.status_code == 429:
            espera = res.json().get("retry_after", 4.0)
            time.sleep(float(espera) + 0.5)
        else:
            raise Exception(f"HTTP {res.status_code}: {res.text}")

def executar_farm_thread(token, channel_id, quantidade, categoria, inicio_roll=1):
    if db:
        db.set("parar_farm", "0")

    comando = categoria if categoria.startswith("$") else f"${categoria}"
    
    if inicio_roll > 1:
        atualizar_status(True, inicio_roll - 1, quantidade, f"Retomando do roll {inicio_roll}...")
    else:
        atualizar_status(True, 0, quantidade, "Iniciando rolagens...")

    try:
        if inicio_roll == 1:
            enviar_mensagem(token, channel_id, f"🤖 *Iniciando farm de {quantidade} rolls...*")
        else:
            enviar_mensagem(token, channel_id, f"🔄 *Retomando farm a partir do roll {inicio_roll}/{quantidade}...*")
    except Exception:
        pass

    time.sleep(3)

    for numero in range(inicio_roll, quantidade + 1):
        if db and db.get("parar_farm") == "1":
            try:
                enviar_mensagem(token, channel_id, f"🛑 *Farm pausado no roll {numero-1}/{quantidade}.*")
            except Exception:
                pass
            atualizar_status(False, numero - 1, quantidade, "⏸️ Farm Pausado!", pausado=True)
            return

        try:
            msg_id = enviar_mensagem(token, channel_id, comando)
            atualizar_status(True, numero, quantidade, f"Roll {numero}/{quantidade} enviado.")
        except Exception as e:
            atualizar_status(True, numero, quantidade, f"Erro no roll {numero}.")

        if numero < quantidade:
            time.sleep(4)

    try:
        enviar_mensagem(token, channel_id, f"✅ *Farm concluído! {quantidade} rolls enviados.*")
    except Exception:
        pass

    atualizar_status(False, quantidade, quantidade, "✅ Farm Concluído!", pausado=False)

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Federação Mudae Tempest</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            background: linear-gradient(135deg, #0d1b2a, #1b263b, #415a77);
            color: #e0e1dd; 
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 15px;
        }
        .container { 
            width: 100%;
            max-width: 480px; 
            background: rgba(13, 27, 42, 0.85); 
            backdrop-filter: blur(10px);
            padding: 25px; 
            border-radius: 16px; 
            border: 1px solid #00b4d8;
            box-shadow: 0 0 20px rgba(0, 180, 216, 0.3);
        }
        .header-title {
            text-align: center;
            margin-bottom: 20px;
        }
        .header-title h2 { 
            color: #90e0ef; 
            font-size: 22px;
            letter-spacing: 1px;
            text-transform: uppercase;
            text-shadow: 0 0 10px rgba(144, 224, 239, 0.5);
        }
        .header-title p {
            color: #778da9;
            font-size: 12px;
            margin-top: 4px;
        }
        label { display: block; text-align: left; margin-top: 12px; margin-bottom: 5px; font-size: 13px; color: #90e0ef; }
        input, select, button { 
            width: 100%; 
            padding: 12px; 
            margin: 4px 0; 
            border-radius: 8px; 
            border: 1px solid #415a77; 
            font-size: 14px; 
        }
        input, select { background: #1b263b; color: #ffffff; outline: none; }
        input:focus, select:focus { border-color: #00b4d8; box-shadow: 0 0 8px rgba(0, 180, 216, 0.5); }
        .btn-group { display: flex; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
        .btn-start { background: #00b4d8; color: #0d1b2a; font-weight: bold; cursor: pointer; border: none; flex: 1; min-width: 140px; }
        .btn-resume { background: #52b788; color: #0d1b2a; font-weight: bold; cursor: pointer; border: none; flex: 1; min-width: 140px; display: none; }
        .btn-stop { background: #e63946; color: white; font-weight: bold; cursor: pointer; border: none; flex: 1; min-width: 140px; }
        button:disabled { background: #415a77 !important; cursor: not-allowed; opacity: 0.5; }
        .status-box { margin-top: 20px; padding: 15px; background: #1b263b; border-radius: 10px; border: 1px solid #415a77; text-align: center; }
        .contador { font-size: 26px; font-weight: bold; color: #90e0ef; margin: 8px 0; }
        .barra { width: 100%; height: 12px; background: #0d1b2a; border-radius: 6px; overflow: hidden; margin: 8px 0; }
        .progresso { height: 100%; width: 0%; background: #00b4d8; transition: width 0.3s; }
        .info-txt { font-size: 13px; color: #e0e1dd; margin: 4px 0; }
        .footer { font-size: 11px; color: #778da9; text-align: center; margin-top: 15px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header-title">
            <h2>💧 FEDERAÇÃO MUDAE TEMPEST</h2>
            <p>Painel de Controle de Rolagens</p>
        </div>
        
        <form id="farmForm" onsubmit="iniciarFarm(event, false)">
            <label>Token do Discord:</label>
            <input type="password" id="token" name="token" required placeholder="Seu token de usuário">
            
            <label>ID do Canal:</label>
            <input type="text" id="channel_id" name="channel_id" required placeholder="Ex: 123456789012345">
            
            <label>Quantidade de Rolagens:</label>
            <input type="number" id="quantidade" name="quantidade" value="15" min="1" required>
            
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
            
            <div class="btn-group">
                <button type="submit" id="btnIniciar" class="btn-start">🚀 INICIAR</button>
                <button type="button" id="btnRetomar" class="btn-resume" onclick="retomarFarm()">🔄 RETOMAR</button>
                <button type="button" id="btnParar" onclick="pararFarm()" class="btn-stop" disabled>⏸️ PAUSAR</button>
            </div>
        </form>

        <div class="status-box">
            <div id="contador" class="contador">0/0</div>
            <div class="barra"><div id="progresso" class="progresso"></div></div>
            <p id="mensagem" class="info-txt">Aguardando início...</p>
        </div>
        <div class="footer">Federação Mudae Tempest • Sistema de Automação</div>
    </div>

    <script>
        let ultimoEstado = {};

        async function iniciarFarm(e, retomar = false) {
            if (e) e.preventDefault();
            const formData = new FormData(document.getElementById("farmForm"));
            if (retomar) formData.append("retomar", "true");
            
            const res = await fetch("/iniciar", { method: "POST", body: formData });
            const data = await res.json();
            if (data.erro) alert(data.erro);
        }

        function retomarFarm() {
            iniciarFarm(null, true);
        }

        async function pararFarm() {
            const res = await fetch("/parar", { method: "POST" });
            const data = await res.json();
            if (data.sucesso) {
                document.getElementById("mensagem").innerText = "Pausando...";
            }
        }

        async function atualizarStatus() {
            try {
                const res = await fetch("/status");
                const d = await res.json();
                ultimoEstado = d;

                document.getElementById("contador").innerText = `${d.enviados || 0}/${d.quantidade || 0}`;
                document.getElementById("mensagem").innerText = d.mensagem || "Aguardando...";
                let pct = d.quantidade > 0 ? (d.enviados / d.quantidade) * 100 : 0;
                document.getElementById("progresso").style.width = pct + "%";
                
                document.getElementById("btnIniciar").disabled = d.rodando;
                document.getElementById("btnParar").disabled = !d.rodando;

                // Exibe botão de retomar apenas quando pausado e com rolagens pendentes
                const podeRetomar = d.pausado && d.enviados < d.quantidade;
                document.getElementById("btnRetomar").style.display = podeRetomar ? "block" : "none";
            } catch(e) {}
        }
        setInterval(atualizarStatus, 2000);
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_PAGINA)

@app.route("/iniciar", methods=["POST"])
def iniciar():
    status_raw = db.get("farm_status") if db else None
    status = json.loads(status_raw) if status_raw else {}
    
    if status.get("rodando"):
        return jsonify({"erro": "Um farm já está em execução!"})

    retomar = request.form.get("retomar") == "true"
    token = request.form.get("token", "").strip()
    channel_id = request.form.get("channel_id", "").strip()
    categoria = request.form.get("categoria", "wa").strip()
    
    try:
        quantidade = int(request.form.get("quantidade", 15))
    except ValueError:
        quantidade = 15

    inicio_roll = 1
    if retomar and status.get("enviados"):
        inicio_roll = status.get("enviados") + 1

    threading.Thread(
        target=executar_farm_thread,
        args=(token, channel_id, quantidade, categoria, inicio_roll),
        daemon=True
    ).start()

    return jsonify({"sucesso": True})

@app.route("/parar", methods=["POST"])
def parar():
    if db:
        db.set("parar_farm", "1")
    return jsonify({"sucesso": True})

@app.route("/status")
def get_status():
    status_raw = db.get("farm_status") if db else None
    return jsonify(json.loads(status_raw) if status_raw else {"rodando": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
