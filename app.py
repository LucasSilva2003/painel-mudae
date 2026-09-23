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

def atualizar_status(rodando, enviados, quantidade, mensagem):
    dados = {
        "rodando": rodando,
        "enviados": enviados,
        "quantidade": quantidade,
        "mensagem": mensagem
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

def executar_farm_thread(token, channel_id, quantidade, categoria):
    if db:
        db.set("parar_farm", "0") # Reset no sinal de parada

    comando = categoria if categoria.startswith("$") else f"${categoria}"
    atualizar_status(True, 0, quantidade, "Iniciando rolagens...")

    try:
        enviar_mensagem(token, channel_id, f"🤖 *Iniciando farm de {quantidade} rolls...*")
    except Exception:
        pass

    time.sleep(3)

    for numero in range(1, quantidade + 1):
        # Verifica se o botão de parar foi clicado
        if db and db.get("parar_farm") == "1":
            try:
                enviar_mensagem(token, channel_id, f"🛑 *Farm interrompido pelo usuário no roll {numero-1}/{quantidade}.*")
            except Exception:
                pass
            atualizar_status(False, numero - 1, quantidade, "🛑 Farm Interrompido!")
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

    atualizar_status(False, quantidade, quantidade, "✅ Farm Concluído!")

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mudae Farm Central</title>
    <style>
        body { font-family: Arial, sans-serif; background: #23272a; color: white; text-align: center; padding: 20px; }
        .container { max-width: 400px; background: #2c2f33; padding: 30px; border-radius: 10px; margin: 30px auto; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { color: #ff69b4; margin-bottom: 20px; }
        label { display: block; text-align: left; margin-top: 15px; margin-bottom: 5px; font-size: 14px; }
        input, select, button { width: 100%; padding: 12px; margin: 5px 0; border-radius: 5px; border: none; box-sizing: border-box; font-size: 15px; }
        input, select { background: #4f545c; color: white; }
        .btn-start { background: #43b581; color: white; font-weight: bold; cursor: pointer; margin-top: 20px; }
        .btn-stop { background: #f04747; color: white; font-weight: bold; cursor: pointer; margin-top: 10px; }
        button:disabled { background: #747f8d; cursor: not-allowed; opacity: 0.6; }
        .footer { font-size: 12px; color: #faa61a; margin-top: 20px; }
        .status-box { margin-top: 25px; padding: 15px; background: #202225; border-radius: 8px; }
        .contador { font-size: 28px; font-weight: bold; color: #ff69b4; margin: 10px 0; }
        .barra { width: 100%; height: 16px; background: #4f545c; border-radius: 8px; overflow: hidden; margin: 10px 0; }
        .progresso { height: 100%; width: 0%; background: #43b581; transition: width 0.3s; }
        .info-txt { font-size: 14px; color: #b9bbbe; margin: 4px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🌸 Mudae Farm Central</h2>
        <form id="farmForm" onsubmit="iniciarFarm(event)">
            <label>Insira seu Token do Discord (Usuário):</label>
            <input type="password" name="token" required placeholder="Cole seu token pessoal aqui">
            
            <label>ID do Canal do Discord (Onde vai rolar):</label>
            <input type="text" name="channel_id" required placeholder="Ex: 123456789012345">
            
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
            <button type="submit" id="btnIniciar" class="btn-start">🚀 INICIAR FARM AUTOMÁTICO</button>
        </form>
        
        <button id="btnParar" onclick="pararFarm()" class="btn-stop" disabled>🛑 PARAR ROLAGENS</button>

        <div class="status-box">
            <div id="contador" class="contador">0/0</div>
            <div class="barra"><div id="progresso" class="progresso"></div></div>
            <p id="mensagem" class="info-txt">Aguardando início...</p>
        </div>
        <div class="footer">⚠️ Risco de ban por conta do usuário. Use com moderação.</div>
    </div>

    <script>
        async function iniciarFarm(e) {
            e.preventDefault();
            const formData = new FormData(document.getElementById("farmForm"));
            const res = await fetch("/iniciar", { method: "POST", body: formData });
            const data = await res.json();
            if (data.erro) alert(data.erro);
        }

        async function pararFarm() {
            const res = await fetch("/parar", { method: "POST" });
            const data = await res.json();
            if (data.sucesso) {
                document.getElementById("mensagem").innerText = "Solicitando parada...";
            }
        }

        async function atualizarStatus() {
            try {
                const res = await fetch("/status");
                const d = await res.json();
                document.getElementById("contador").innerText = `${d.enviados || 0}/${d.quantidade || 0}`;
                document.getElementById("mensagem").innerText = d.mensagem || "Aguardando...";
                let pct = d.quantidade > 0 ? (d.enviados / d.quantidade) * 100 : 0;
                document.getElementById("progresso").style.width = pct + "%";
                
                // Controle dos botões
                document.getElementById("btnIniciar").disabled = d.rodando;
                document.getElementById("btnParar").disabled = !d.rodando;
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

    token = request.form.get("token", "").strip()
    channel_id = request.form.get("channel_id", "").strip()
    categoria = request.form.get("categoria", "wa").strip()
    try:
        quantidade = int(request.form.get("quantidade", 15))
    except ValueError:
        quantidade = 15

    threading.Thread(
        target=executar_farm_thread,
        args=(token, channel_id, quantidade, categoria),
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
