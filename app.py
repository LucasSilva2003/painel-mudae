from flask import Flask, render_template_string, request, jsonify
import requests
import time
import json
import redis
import threading
import os

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
try:
    db = redis.Redis.from_url(REDIS_URL, decode_responses=True)
except Exception:
    db = None

def atualizar_status(channel_id, rodando, enviados, quantidade, mensagem, pausado=False):
    dados = {
        "rodando": rodando,
        "enviados": enviados,
        "quantidade": quantidade,
        "mensagem": mensagem,
        "pausado": pausado
    }
    if db and channel_id:
        try:
            db.set(f"farm_status:{channel_id}", json.dumps(dados))
        except Exception:
            pass

def enviar_mensagem(token, channel_id, conteudo):
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {"Authorization": token, "Content-Type": "application/json"}
    
    while True:
        res = requests.post(url, headers=headers, json={"content": conteudo}, timeout=10)
        if res.status_code in [200, 201]:
            return res.json()
        elif res.status_code == 429:
            espera = res.json().get("retry_after", 4.0)
            time.sleep(float(espera) + 0.5)
        else:
            raise Exception(f"HTTP {res.status_code}: {res.text}")

def executar_farm_thread(token, channel_id, quantidade, categoria, usar_us, inicio_roll=1):
    if db:
        db.set(f"parar_farm:{channel_id}", "0")

    comando = categoria if categoria.startswith("$") else f"${categoria}"
    
    if inicio_roll > 1:
        atualizar_status(channel_id, True, inicio_roll - 1, quantidade, f"Retomando do roll {inicio_roll}...", pausado=False)
    else:
        atualizar_status(channel_id, True, 0, quantidade, "Iniciando rolagens...", pausado=False)

    try:
        if inicio_roll == 1:
            enviar_mensagem(token, channel_id, f"🤖 *Federação Tempest: Iniciando farm de {quantidade} rolls...*")
        else:
            enviar_mensagem(token, channel_id, f"🔄 *Federação Tempest: Retomando farm a partir do roll {inicio_roll}/{quantidade}...*")
    except Exception:
        pass

    time.sleep(2)
    us_usado = False

    for numero in range(inicio_roll, quantidade + 1):
        if db and db.get(f"parar_farm:{channel_id}") == "1":
            atualizar_status(channel_id, False, numero - 1, quantidade, f"⏸️ Pausado no roll {numero-1}/{quantidade}", pausado=True)
            return

        try:
            resposta = enviar_mensagem(token, channel_id, comando)
            
            # Lê o conteúdo e também possíveis embeds retornados pelo Discord/Mudae
            conteudo_resposta = ""
            if isinstance(resposta, dict):
                conteudo_resposta = resposta.get("content", "") or ""
                for embed in resposta.get("embeds", []):
                    conteudo_resposta += " " + embed.get("description", "") + " " + embed.get("title", "")
            
            conteudo_lower = conteudo_resposta.lower()
            
            # Verificação aprimorada para detetar o limite de rolls independentemente da variação exata
            if "limitado" in conteudo_lower or "min restante" in conteudo_lower or "upvote" in conteudo_lower:
                if usar_us and not us_usado:
                    atualizar_status(channel_id, True, numero - 1, quantidade, "⚠️ Rolls esgotados! Usando $us 20...", pausado=False)
                    enviar_mensagem(token, channel_id, "$us 20")
                    us_usado = True
                    time.sleep(3)  # Aguarda a Mudae processar o reset
                    
                    # Tenta novamente o comando após o uso do $us
                    enviar_mensagem(token, channel_id, comando)
                    atualizar_status(channel_id, True, numero, quantidade, f"Roll {numero}/{quantidade} enviado ($us ativado).", pausado=False)
                else:
                    atualizar_status(channel_id, False, numero - 1, quantidade, "🛑 Rolls esgotados!", pausado=True)
                    enviar_mensagem(token, channel_id, f"🛑 *Farm pausado: limite de rolls atingido no roll {numero-1}/{quantidade}.*")
                    return
            else:
                atualizar_status(channel_id, True, numero, quantidade, f"Roll {numero}/{quantidade} enviado.", pausado=False)

        except Exception:
            atualizar_status(channel_id, True, numero, quantidade, f"Erro no roll {numero}.", pausado=False)

        if numero < quantidade:
            time.sleep(4)

    atualizar_status(channel_id, False, quantidade, quantidade, "✅ Farm Concluído!", pausado=False)

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
        .checkbox-group { 
            grid-column: span 2; 
            display: flex; 
            align-items: center; 
            gap: 8px; 
            margin-top: 5px; 
            background: #0b132b; 
            padding: 8px 12px; 
            border-radius: 6px; 
            border: 1px solid #0077b6; 
        }
        .checkbox-group input { width: auto; cursor: pointer; }
        .checkbox-group label { margin-bottom: 0; cursor: pointer; color: #48cae4; font-size: 12px; }

        @media (max-width: 480px) { .checkbox-group { grid-column: span 1; } }

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
        <p>PAINEL DE CONTROLADORIA MULTI-SESSÃO</p>
    </div>

    <div class="container">
        <form id="farmForm">
            <div class="form-grid">
                <div class="field-group">
                    <label>Token de Usuário:</label>
                    <input type="password" id="token" name="token" required placeholder="Cole seu token">
                </div>
                <div class="field-group">
                    <label>Channel ID (Seu Canal):</label>
                    <input type="text" id="channel_id" name="channel_id" required placeholder="ID do canal" oninput="atualizarStatus()">
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
                <div class="checkbox-group">
                    <input type="checkbox" id="usar_us" name="usar_us" value="true">
                    <label for="usar_us">Usar <b>$us 20</b> automaticamente se os rolls acabarem</label>
                </div>
            </div>
            
            <div class="btn-group">
                <button type="button" id="btnIniciar" class="btn-start" onclick="iniciarFarm(false)">🚀 INICIAR DO ZERO</button>
                <button type="button" id="btnRetomar" class="btn-resume" onclick="iniciarFarm(true)" disabled>▶️ RETOMAR</button>
                <button type="button" id="btnParar" class="btn-stop" onclick="pararFarm()" disabled>⏸️ PAUSAR</button>
            </div>
        </form>

        <div class="status-box">
            <div id="contador" class="contador">0/15</div>
            <div class="status-details">
                <p id="mensagem" class="info-txt">Insira o Channel ID para carregar...</p>
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
            else atualizarStatus();
        }

        async function pararFarm() {
            const channelId = document.getElementById("channel_id").value.trim();
            if (!channelId) return alert("Insira o Channel ID!");

            const res = await fetch(`/parar?channel_id=${channelId}`, { method: "POST" });
            const data = await res.json();
            if (data.sucesso) {
                document.getElementById("mensagem").innerText = "Solicitando pausa...";
            }
        }

        async function atualizarStatus() {
            const channelId = document.getElementById("channel_id").value.trim();
            if (!channelId) {
                document.getElementById("mensagem").innerText = "Insira o Channel ID para carregar o status.";
                document.getElementById("contador").innerText = "0/0";
                document.getElementById("progresso").style.width = "0%";
                document.getElementById("btnIniciar").disabled = false;
                document.getElementById("btnParar").disabled = true;
                document.getElementById("btnRetomar").disabled = true;
                return;
            }

            try {
                const res = await fetch(`/status?channel_id=${channelId}`);
                if (!res.ok) return;
                const d = await res.json();

                document.getElementById("contador").innerText = `${d.enviados || 0}/${d.quantidade || 15}`;
                document.getElementById("mensagem").innerText = d.mensagem || "Pronto para iniciar.";
                let pct = d.quantidade > 0 ? (d.enviados / d.quantidade) * 100 : 0;
                document.getElementById("progresso").style.width = pct + "%";
                
                document.getElementById("btnIniciar").disabled = d.rodando;
                document.getElementById("btnParar").disabled = !d.rodando;

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
    channel_id = request.form.get("channel_id", "").strip()
    if not channel_id:
        return jsonify({"erro": "Channel ID é obrigatório!"})

    status_raw = db.get(f"farm_status:{channel_id}") if db else None
    status = json.loads(status_raw) if status_raw else {}
    
    if status.get("rodando"):
        return jsonify({"erro": "Já existe um farm rodando neste canal!"})

    retomar = request.form.get("retomar") == "true"
    token = request.form.get("token", "").strip()
    categoria = request.form.get("categoria", "wa").strip()
    usar_us = request.form.get("usar_us") == "true"
    
    try:
        quantidade = int(request.form.get("quantidade", 15))
    except ValueError:
        quantidade = 15

    inicio_roll = 1
    if retomar and status.get("enviados"):
        inicio_roll = status.get("enviados") + 1

    threading.Thread(
        target=executar_farm_thread,
        args=(token, channel_id, quantidade, categoria, usar_us, inicio_roll),
        daemon=True
    ).start()

    return jsonify({"sucesso": True})

@app.route("/parar", methods=["POST"])
def parar():
    channel_id = request.args.get("channel_id", "").strip()
    if db and channel_id:
        db.set(f"parar_farm:{channel_id}", "1")
    return jsonify({"sucesso": True})

@app.route("/status")
def get_status():
    channel_id = request.args.get("channel_id", "").strip()
    if not channel_id or not db:
        return jsonify({"rodando": False, "enviados": 0, "quantidade": 0, "mensagem": "Aguardando canal..."})

    status_raw = db.get(f"farm_status:{channel_id}")
    return jsonify(json.loads(status_raw) if status_raw else {"rodando": False, "enviados": 0, "quantidade": 0})

@app.errorhandler(404)
def page_not_found(e):
    return render_template_string(HTML_PAGINA), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
