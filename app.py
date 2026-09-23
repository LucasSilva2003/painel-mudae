async def rodar_selfbot_task(token, channel_id, quantidade, categoria):
    bot = commands.Bot(command_prefix="!", self_bot=True, heartbeat_timeout=60.0)
    
    @bot.event
    async def on_ready():
        print(f"📡 Conectado ao selfbot de {bot.user.name}")
        channel = bot.get_channel(int(channel_id))
        if not channel:
            print("❌ Canal não encontrado.")
            await bot.close()
            return
            
        # Garante que o comando tenha exatamente uma $ no início
        comando = categoria if categoria.startswith("$") else f"${categoria}"
        
        await channel.send(f"🤖 *Conectado ao painel web. Iniciando farm de {quantidade} rolls...*")
        
        # Intervalo entre envios (segundos)
        delay = 3.0
        
        for i in range(1, quantidade + 1):
            try:
                await channel.send(comando)
                print(f"Roll {i}/{quantidade} enviado por {bot.user.name}")
                
                # Pausa para evitar rate limit do Discord
                await asyncio.sleep(delay)
                
                # Pausa preventiva a cada 10 envios
                if i % 10 == 0 and i < quantidade:
                    print("☕ Pausa de descanso de 8 segundos...")
                    await asyncio.sleep(8.0)

            except discord.errors.HTTPException as e:
                if e.status == 429:
                    print("⚠️ Rate limit detectado. Aguardando 15s...")
                    await asyncio.sleep(15.0)
                else:
                    print(f"⚠️ Erro HTTP: {e}")
                    break
            except Exception as e:
                print(f"⚠️ Erro inesperado: {e}")
                break
                
        await channel.send("✅ *Farm concluído com sucesso! Desconectando.*")
        await bot.close()
