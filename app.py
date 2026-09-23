async def rodar_selfbot_task(token, channel_id, quantidade, categoria):
    try:
        quantidade = int(quantidade)
    except (TypeError, ValueError):
        print(f"Quantidade inválida: {quantidade!r}")
        return

    if quantidade <= 0:
        print("A quantidade deve ser maior que zero.")
        return

    print(f"Executando {quantidade} rolls")

    bot = commands.Bot(
        command_prefix="!",
        self_bot=True,
        heartbeat_timeout=60.0
    )

    @bot.event
    async def on_ready():
        channel = bot.get_channel(int(channel_id))

        if channel is None:
            print("Canal não encontrado.")
            await bot.close()
            return

        comando = categoria if categoria.startswith("$") else f"${categoria}"

        for numero in range(1, quantidade + 1):
            try:
                await channel.send(comando)
                print(f"Roll {numero}/{quantidade} enviado")
                await asyncio.sleep(3)

            except Exception as erro:
                print(f"Erro no roll {numero}: {erro}")
                break

        await bot.close()

    await bot.start(token)
