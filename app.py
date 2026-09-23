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
            enviar_mensagem(token, channel_id, f"🤖 *Federação Tempest: Iniciando farm de {quantidade} rolls...*")
        else:
            enviar_mensagem(token, channel_id, f"🔄 *Federação Tempest: Retomando farm a partir do roll {inicio_roll}/{quantidade}...*")
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
            background: #0a192f linear-gradient(135deg, #0d1b2a 0%, #1b263b 50%, #00b4d8 100%);
            color: #ffffff; 
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 15px;
            overflow-x: hidden;
            position: relative;
        }
        
        /* Efeito de iluminação Mágica ao fundo */
        body::before {
            content: "";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 600px;
            height: 600px;
            background: radial-gradient(circle, rgba(0,180,216,0.2) 0%, rgba(0,0,0,0) 70%);
            z-index: 0;
            pointer-events: none;
        }

        .header-logo {
            text-align: center;
            margin-bottom: 15px;
            z-index: 1;
        }
        
        .header-logo h1 {
            font-size: 24px;
            font-weight: 800;
            letter-spacing: 2px;
            color: #90e0ef;
            text-transform: uppercase;
            text-shadow: 0 0 15px rgba(144, 224, 239, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }

        .header-logo p {
            font-size: 11px;
            color: #48cae4;
            letter-spacing: 1px;
            margin-top: 2px;
        }

        .container { 
            width: 100%;
            max-width: 550px; 
            background: rgba(13, 27, 42, 0.85); 
            backdrop-filter: blur(12px);
            padding: 25px; 
            border-radius: 12px; 
            border: 2px solid #00b4d8;
            box-shadow: 0 0 25px rgba(0, 180, 216, 0.4), inset 0 0 15px rgba(0, 180, 216, 0.2);
            z-index: 1;
        }

        .form-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
        }

        @media (max-width: 500px) {
            .form-grid { grid-template-columns: 1fr; }
        }

        .field-group { display: flex; flex-direction: column; }
        label { text-align: left; margin-bottom: 4px; font-size: 12px; color: #90e0ef; font-weight: 600; }
        
        input, select { 
            width: 100%; 
            padding: 10px 12px; 
            border-radius: 6px; 
            border: 1px solid #0077b6; 
            background: rgba(11, 19, 43, 0.9);
            color: #ffffff; 
            font-size: 13px;
            outline: none;
        }
        
        input:focus, select:focus { border-color: #90e0ef; box-shadow: 0 0 8px rgba(144, 224, 239, 0.5); }

        .btn-group { display: flex; gap: 10px; margin-top: 15px; }
        
        .btn-start { 
            background: #2ec4b6; 
            color: #0d1b2a; 
            font-weight: bold; 
            cursor: pointer; 
            border: none; 
            padding: 12px;
            border-radius: 6px;
            flex: 1;
            font-size: 13px;
            box-shadow: 0 0 10px rgba(46, 196, 182, 0.4);
        }
        
        .btn-resume { 
            background: #00b4d8; 
            color: #ffffff; 
            font-weight: bold; 
            cursor: pointer; 
            border: none; 
            padding: 12px;
            border-radius: 6px;
            flex: 1;
            font-size: 13px;
            display: none;
            box-shadow: 0 0 10px rgba(0, 180, 216, 0.4);
        }

        .btn-stop { 
            background: #e63946; 
            color: white; 
            font-weight: bold; 
            cursor: pointer; 
            border: none; 
            padding: 12px;
            border-radius: 6px;
            flex: 1;
            font-size: 13px;
        }

        button:disabled { background: #415a77 !important; cursor: not-allowed; opacity: 0.5; box-shadow: none; }

        .status-box { 
            margin-top: 20px; 
            padding: 15px; 
            background: rgba(11, 19, 43, 0.8); 
            border-radius: 8px; 
            border: 1px solid #0077b6;
            display: flex;
            align-items: center;
            gap: 15px;
        }

        .contador { font-size: 24px; font-weight: bold; color: #ff9ebb; min-width: 65px; text-align: center; }
        .status-details { flex: 1; }
        .barra { width: 100%; height: 10px; background: #1b263b; border-radius: 5px; overflow: hidden; margin-top: 5px; }
        .progresso { height: 100%; width: 0%; background: #00b4d8; transition: width 0.3s; }
        .info-txt { font-size: 12px; color: #e0e1dd; }

        .footer { font-size: 10px; color: #48cae4; text-align: center; margin-top: 15px; z-index: 1; }
    </style>
</head>
<body>
    <div class="header-logo">
        <h1>💧 FEDERAÇÃO MUDAE TEMPEST</h1>
        <p>SISTEMA CENTRAL DE ROLAGENS AUTOMÁTICAS</p>
    </div>

    <div class="container">
        <form id="farmForm" onsubmit="iniciarFarm(event, false)">
            <div class="form-grid">
                <div class="field-group">
                    <label>Token de Usuário:</label>
                    <input type="password" id="token" name="token" required placeholder="Cole seu token do Discord">
                </div>
                <div class="field-group">
                    <label>Channel ID:</label>
                    <input type="text" id="channel_id" name="channel_id" required placeholder="ID do canal de rolagens">
                </div>
                <div class="field-group">
                    <label>Rolagens:</label>
                    <input type="number" id="quantidade" name="quantidade" value="15" min="1" required>
                </div>
                <div class="field-group">
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
                </div>
            </div>
            
            <div class="btn-group">
                <button type="submit" id="btnIniciar" class="btn-start">📌 INICIAR FARM AUTOMÁTICO</button>
                <button type="button" id="btnRetomar" class="btn-resume" onclick="retomarFarm()">🔄 RETOMAR</button>
                <button type="button" id="btnParar" onclick="pararFarm()" class="btn-stop" disabled>🛑 PARAR ROLAGENS</button>
            </div>
        </form>

        <div class="status-box">
            <div id="contador" class="contador">0/15</div>
            <div class="status-details">
                <p id="mensagem" class="info-txt">Aguardando início...</p>
                <div class="barra"><div id="progresso" class="progresso"></div></div>
            </div>
        </div>
    </div>

    <div class="footer">Inspirado na Federação Mudae Tempest / Tensei Shitara Slime Datta Ken</div>

    <script>
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

                document.getElementById("contador").innerText = `${d.enviados || 0}/${d.quantidade || 15}`;
                document.getElementById("mensagem").innerText = d.mensagem || "Aguardando início...";
                let pct = d.quantidade > 0 ? (d.enviados / d.quantidade) * 100 : 0;
                document.getElementById("progresso").style.width = pct + "%";
                
                document.getElementById("btnIniciar").disabled = d.rodando;
                document.getElementById("btnParar").disabled = !d.rodando;

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
