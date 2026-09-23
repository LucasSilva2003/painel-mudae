import requests
import time
import json
import redis
import os

# Conexão ao Redis configurado no Render
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
db = redis.Redis.from_url(REDIS_URL, decode_responses=True)

def atualizar_status(rodando, enviados, quantidade, mensagem):
    db.set("farm_status", json.dumps({
        "rodando": rodando,
        "enviados": enviados,
        "quantidade": quantidade,
        "mensagem": mensagem
    }))

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

def processar_farm():
    print("🤖 Worker a rodar e a aguardar tarefas...", flush=True)
    while True:
        item = db.blpop("fila_farm", timeout=5)
        if not item:
            continue

        dados = json.loads(item[1])
        token = dados["token"]
        channel_id = dados["channel_id"]
        quantidade = dados["quantidade"]
        comando = dados["categoria"] if dados["categoria"].startswith("$") else f"${dados['categoria']}"

        print(f"🚀 A iniciar Farm de {quantidade} rolls no canal {channel_id}", flush=True)
        atualizar_status(True, 0, quantidade, "Iniciando rolagens...")

        try:
            enviar_mensagem(token, channel_id, f"🤖 *Iniciando farm de {quantidade} rolls...*")
        except Exception as e:
            print(f"Erro inicial: {e}", flush=True)

        time.sleep(3)

        for numero in range(1, quantidade + 1):
            try:
                msg_id = enviar_mensagem(token, channel_id, comando)
                print(f"✅ [{numero}/{quantidade}] Enviado ID: {msg_id}", flush=True)
                atualizar_status(True, numero, quantidade, f"Roll {numero}/{quantidade} enviado.")
            except Exception as e:
                print(f"❌ [{numero}/{quantidade}] Erro: {e}", flush=True)

            if numero < quantidade:
                time.sleep(4)

        try:
            enviar_mensagem(token, channel_id, f"✅ *Farm concluído! {quantidade} rolls enviados.*")
        except Exception:
            pass

        atualizar_status(False, quantidade, quantidade, "✅ Farm Concluído!")
        print("🏁 Farm concluído com sucesso!", flush=True)

if __name__ == "__main__":
    processar_farm()
