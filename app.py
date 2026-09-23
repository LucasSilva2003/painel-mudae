from flask import Flask, render_template_string, request
import requests
import time
import threading

app = Flask(__name__)

HTML_PAGINA = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Mudae Auto-Farm Painel</title>
    <style>
        body { font-family: Arial, sans-serif; background: #23272a; color: white; text-align: center; padding: 20px; }
        .container { max-width: 400px; background: #2c2f33; padding: 30px; border-radius: 10px; margin: 50px auto; box-shadow: 0 4px 15px rgba(0,0,0,0.5); }
        h2 { color: #ff69b4; margin-bottom: 20px; }
        input, select, button { width: 100%; padding: 12px; margin: 10px 0; border-radius: 5px; border: none; box-sizing: border-box; font-size: 16px; }
        input, select { background: #4f545c; color: white; }
        button { background: #43b581; color: white; font-weight: bold; cursor: pointer; transition: 0.3s; }
        button:hover { background: #3ca374; }
        .footer { font-size: 12px; color: #7289da; margin-top: 20px; }
    </style>
</head>
<body>
    <div class="container">
        <h2>🌸 Mudae Farm Central</h2>
        <form action="/iniciar" method="POST">
            <label>Insira seu Token do Discord (Usuário):</label>
            <input type="password" name="token" placeholder="Cole seu token pessoal aqui" required>
            
            <label>ID do Canal do Discord (Onde vai rolar):</label>
            <input type="text" name="channel_id" placeholder="Ex: 123456789012345" required>
            
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
            
            <button type="submit">🚀 INICIAR FARM AUTOMÁTICO</button>
        </form>
        <div class="footer">⚠️ Risco de ban por conta do usuário. Use com moderação.</div>
    </div>
</body>
</html>
"""

def enviar_mensagem(token, channel_id, conteudo):
    """Realiza o envio direto à API HTTP do Discord."""
    url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
    headers = {
        "Authorization": token,
        "Content-Type": "application/json"
    }
    payload = {"content": conteudo}
    
    while True:
        try:
            res = requests.post(url, headers=headers, json=payload, timeout=10)
            
            if res.status_code in [200, 201]:
                return True
            
            elif res.status_code == 429:
                # Rate limit atingido: aguarda o tempo exigido pelo Discord
                dados = res.json()
                espera = dados.get("retry_after", 4.0)
                print(f"⚠️ Rate limit detectado. Aguardando {espera}s para tentar novamente...")
                time.sleep(float(espera) + 0.5)
            else:
                print(f"⚠️ Erro HTTP {res.status_code}: {res.text}")
                return False
                
        except Exception as e:
            print(f"⚠️ Falha de conexão na requisição: {e}. Re-tentando em 3s...")
            time.sleep(3.0)

def executar_farm_thread(token, channel_id, quantidade, categoria):
    comando = categoria if categoria.startswith("$") else f"${categoria}"
    
    print(f"🚀 Iniciando ciclo contínuo de {quantidade} rolls...")
    enviar_mensagem(token, channel_id, f"🤖 *Iniciando farm de {quantidade} rolls...*")
    time.sleep(3.0)

    for numero in range(1, quantidade + 1):
        sucesso = enviar_mensagem(token, channel_id, comando)
        
        if sucesso:
            print(f"Roll {numero}/{quantidade} enviado com sucesso")
        else:
            print(f"⚠️ Não foi possível confirmar o envio do roll {numero}/{quantidade}")
            
        # time.sleep alinhado com o 'if/else', executando em TODOS os rolls:
        time.sleep(4.0)

    enviar_mensagem(token, channel_id, "✅ *Farm concluído com sucesso!*")
    print("✅ Execução finalizada com sucesso.")

@app.route('/')
def index():
    return render_template_string(HTML_PAGINA)

@app.route('/iniciar', methods=['POST'])
def iniciar_farm():
    token = request.form.get('token', '').strip()
    channel_id = request.form.get('channel_id', '').strip()
    
    try:
        quantidade = int(request.form.get('quantidade', 15))
    except (ValueError, TypeError):
        quantidade = 15

    categoria = request.form.get('categoria', 'wa')
    
    threading.Thread(
        target=executar_farm_thread, 
        args=(token, channel_id, quantidade, categoria), 
        daemon=True
    ).start()
    
    return "<h3>🚀 Farm Iniciado! Olhe o canal do seu Discord.</h3><br><a href='/'>Voltar</a>"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
