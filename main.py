import os
import json
import discord
from discord.ext import commands
from dotenv import load_dotenv
from cogs.encomendas import EncomendaCog

button_data = {}

API_DATA = {}

async def load_api_data():
    """Carrega os dados do arquivo local data.json para a variável global API_DATA."""
    global API_DATA
    try:
        with open("data.json", "r", encoding="utf-8") as file:
            API_DATA = json.load(file)
        print("[API] Dados carregados com sucesso do arquivo local.")
    except FileNotFoundError:
        print("[ERRO] Arquivo data.json não encontrado.")
        API_DATA = None
    except json.JSONDecodeError:
        print("[ERRO] Arquivo data.json está corrompido ou inválido.")
        API_DATA = None

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix=commands.when_mentioned_or('.'), intents=discord.Intents.all())

    async def setup_hook(self):
        """Carrega os dados da API, a cog de encomendas e sincroniza os comandos de árvore."""
        await load_api_data()
        await self.add_cog(EncomendaCog(self, button_data, API_DATA))
        print("[SETUP] Cog 'EncomendaCog' carregada.")
        
        # Sincroniza os comandos de árvore
        await self.tree.sync()
        print("[SETUP] Comandos de árvore sincronizados.")

    async def on_ready(self):
        """Executado quando o bot está online e pronto."""
        print(f"[READY] Bot online como {self.user}")

if __name__ == "__main__":
    print("[MAIN] Carregando variáveis de ambiente...")
    load_dotenv()
    token = os.getenv("API_KEY")

    if not token:
        print("[ERRO] Variável de ambiente 'API_KEY' não encontrada.")
    else:
        bot = MyBot()
        print("[MAIN] Iniciando o bot...")
        bot.run(token)