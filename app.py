from flask import Flask, render_template_string, request, jsonify
import redis
import json
import os

app = Flask(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
db = redis.Redis.from_url(REDIS_URL, decode_responses=True)

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
        button { background: #43b581; color: white; font-weight: bold; cursor: pointer; margin-top: 20px; }
        button:disabled { background: #747f8d; cursor: not-allowed; }
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
            <button type="submit" id="btnIniciar">🚀 INICIAR FARM AUTOMÁTICO</button>
        </form>

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

        async function atualizarStatus() {
            try {
                const res = await fetch("/status");
                const d = await res.json();
                document.getElementById("contador").innerText = `${d.enviados || 0}/${d.quantidade || 0}`;
                document.getElementById("mensagem").innerText = d.mensagem || "Aguardando...";
                let pct = d.quantidade > 0 ? (d.enviados / d.quantidade) * 100 : 0;
                document.getElementById("progresso").style.width = pct + "%";
                document.getElementById("btnIniciar").disabled = d.rodando;
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
    status_raw = db.get("farm_status")
    status = json.loads(status_raw) if status_raw else {}
    if status.get("rodando"):
        return jsonify({"erro": "Um farm já está em execução!"})

    dados = {
        "token": request.form.get("token", "").strip(),
        "channel_id": request.form.get("channel_id", "").strip(),
        "quantidade": int(request.form.get("quantidade", 15)),
        "categoria": request.form.get("categoria", "wa").strip()
    }

    db.rpush("fila_farm", json.dumps(dados))
    db.set("farm_status", json.dumps({
        "rodando": True, "enviados": 0, "quantidade": dados["quantidade"], "mensagem": "Na fila do Worker..."
    }))
    return jsonify({"sucesso": True})

@app.route("/status")
def get_status():
    status_raw = db.get("farm_status")
    return jsonify(json.loads(status_raw) if status_raw else {"rodando": False})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
