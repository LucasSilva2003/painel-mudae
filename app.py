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

# Agora o status é gravado usando o channel_id como CHAVE ÚNICA
def atualizar_status(channel_id, rodando, enviados, quantidade, mensagem, pausado=False):
    dados = {
        "rodando": rodando,
        "enviados": enviados,
        "quantidade": quantidade,
        "mensagem": mensagem,
        "pausado": pausado
    }
    if db:
        try:
            # Salva de forma ISOLADA para este canal
            db.set(f"farm_status:{channel_id}", json.dumps(dados))
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
        db.set(f"parar_farm:{channel_id}", "0")

    comando = categoria if categoria.startswith("$") else f"${categoria}"
    
    if inicio_roll > 1:
        atualizar_status(channel_id, True, inicio_roll - 1, quantidade, f"Retomando do roll {inicio_roll}...", pausado=False)
    else:
        atualizar_status(channel_id, True, 0, quantidade, "Iniciando rolagens...", pausado=False)

    time.sleep(2)

    for numero in range(inicio_roll, quantidade + 1):
        # Checa a flag de pausa ESPECÍFICA deste canal
        if db and db.get(f"parar_farm:{channel_id}") == "1":
            atualizar_status(channel_id, False, numero - 1, quantidade, f"⏸️ Pausado no roll {numero-1}/{quantidade}", pausado=True)
            return

        try:
            enviar_mensagem(token, channel_id, comando)
            atualizar_status(channel_id, True, numero, quantidade, f"Roll {numero}/{quantidade} enviado.", pausado=False)
        except Exception:
            atualizar_status(channel_id, True, numero, quantidade, f"Erro no roll {numero}.", pausado=False)

        if numero < quantidade:
            time.sleep(4)

    atualizar_status(channel_id, False, quantidade, quantidade, "✅ Farm Concluído!", pausado=False)

# ROTA DE STATUS AGORA EXIGE O CHANNEL_ID
@app.route("/status")
def get_status():
    channel_id = request.args.get("channel_id", "").strip()
    if not channel_id or not db:
        return jsonify({"rodando": False, "enviados": 0, "quantidade": 0, "mensagem": "Insira o Channel ID"})

    status_raw = db.get(f"farm_status:{channel_id}")
    return jsonify(json.loads(status_raw) if status_raw else {"rodando": False, "enviados": 0, "quantidade": 0})
