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
        atualizar_status(True, inicio_roll - 1, quantidade, f"Retomando do roll {inicio_roll}...", pausado=False)
    else:
        atualizar_status(True, 0, quantidade, "Iniciando rolagens...", pausado=False)

    try:
        if inicio_roll == 1:
            enviar_mensagem(token, channel_id, f"🤖 *Federação Tempest: Iniciando farm de {quantidade} rolls...*")
        else:
            enviar_mensagem(token, channel_id, f"🔄 *Federação Tempest: Retomando farm a partir do roll {inicio_roll}/{quantidade}...*")
    except Exception:
        pass

    time.sleep(2)

    for numero in range(inicio_roll, quantidade + 1):
        # Checa se foi solicitado para pausar
        if db and db.get("parar_farm") == "1":
            try:
                enviar_mensagem(token, channel_id, f"⏸️ *Farm pausado no roll {numero-1}/{quantidade}.*")
            except Exception:
                pass
            atualizar_status(False, numero - 1, quantidade, f"⏸️ Pausado no roll {numero-1}/{quantidade}", pausado=True)
            return

        try:
            msg_id = enviar_mensagem(token, channel_id, comando)
            atualizar_status(True, numero, quantidade, f"Roll {numero}/{quantidade} enviado.", pausado=False)
        except Exception as e:
            atualizar_status(True, numero, quantidade, f"Erro no roll {numero}.", pausado=False)

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
        }

        .header-logo { text-align: center; margin-bottom: 15px; }
        .header-logo h1 {
            font-size: 22px;
            font-weight: 800;
            color: #90e0ef;
            text-transform: uppercase;
            text-shadow: 0 0 12px rgba(144, 224, 239, 0.8);
        }
        .header-logo p { font-size: 11px; color: #48cae4; margin-top: 2px; }

        .container { 
            width: 100%;
            max-width: 520px; 
            background: rgba(13, 27, 42, 0.9); 
            backdrop-filter: blur(10px);
            padding: 20px; 
            border-radius: 12px; 
            border: 2px solid #00b4d8;
            box-shadow: 0 0 20px rgba(0, 180, 216, 0.4);
        }

        .form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        @media (max-width: 480px) { .form-grid { grid-template-columns: 1fr; } }

        .field-group { display: flex; flex-direction: column; }
        label { margin-bottom: 4px; font-size: 12px; color: #90e0ef; font-weight: 600; }
        
        input, select { 
            width: 100%; 
            padding: 10px; 
            border-radius: 6px; 
            border: 1px solid #0077b6; 
            background: #0b132b;
            color: #ffffff; 
            font-size: 13px;
        }

        .btn-group { display: flex; gap: 8px; margin-top: 15px; flex-wrap: wrap; }
        
        button {
            padding: 12px;
            border-radius: 6px;
            border: none;
            font-weight: bold;
            font-size: 13px;
            cursor: pointer;
            flex: 1;
            min-width: 120px;
        }

        .btn-start { background: #2ec4b6; color: #0d1b2a; }
        .btn-resume { background: #00b4d8; color: #ffffff; }
        .btn-stop { background: #e63946; color: white; }

        button:disabled { background: #415a77 !important; cursor: not-allowed; opacity: 0.4; }

        .status-box { 
            margin-top: 15px; 
            padding: 12px; 
            background: #0b132b; 
            border-radius: 8px; 
            border: 1px solid #0077b6;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .contador { font-size: 22px; font-weight: bold; color: #ff9ebb; min-width: 60px; text-align: center; }
        .status-details { flex: 1; }
        .barra { width: 100%; height: 10px; background: #1b263b; border-radius: 5px; overflow: hidden; margin-top: 4px; }
        .progresso { height: 100%; width: 0%; background: #00b4d8; transition: width 0.3s; }
        .info-txt { font-size: 12px; color: #e0e1dd; }
    </style>
</head>
<body>
    <div class="header-logo">
        <h1>💧 FEDERAÇÃO MUDAE TEMPEST</h1>
        <p>PAINEL DE CONTROLADORIA DE ROLLS</p>
    </div>

    <div class="container">
        <form id="farmForm">
            <div class="form-grid">
                <div class="field-group">
                    <label>Token de Usuário:</label>
                    <input type="password" id="token" name="token" required placeholder="Cole seu token">
                </div>
                <div class="field-group">
                    <label>Channel ID:</label>
                    <input type="text" id="channel_id" name="channel_id" required placeholder="ID do canal">
                </div>
                <div class="field-group">
                    <label>Rolagens Total:</label>
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
                <button type="button" id="btnIniciar" class="btn-start" onclick="iniciarFarm(false)">🚀 INICIAR DO ZERO</button>
                <button type="button" id="btnRetomar" class="btn-resume" onclick="iniciarFarm(true)">▶️ RETOMAR</button>
                <button type="button" id="btnParar" class="btn-stop" onclick="pararFarm()" disabled>⏸️ PAUSAR</button>
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

    <script>
        async function iniciarFarm(retomar) {
            const formData = new FormData(document.getElementById("farmForm"));
            if (retomar) formData.append("retomar", "true");
            
            const res = await fetch("/iniciar", { method: "POST", body: formData });
            const data = await res.json();
            if (data.erro) alert(data.erro);
        }

        async function pararFarm() {
            const res = await fetch("/parar", { method: "POST" });
            const data = await res.json();
            if (data.sucesso) {
                document.getElementById("mensagem").innerText = "Solicitando pausa...";
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
                
                // Regras dos botões:
                document.getElementById("btnIniciar").disabled = d.rodando;
                document.getElementById("btnParar").disabled = !d.rodando;

                // O botão de RETOMAR só habilita se estiver pausado e ainda sobrarem rolagens
                const podeRetomar = d.pausado && (d.enviados < d.quantidade);
                document.getElementById("btnRetomar").disabled = !podeRetomar;
                
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
