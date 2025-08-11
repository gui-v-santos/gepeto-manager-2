import os
import aiohttp
import discord
from discord.ext import commands
from dotenv import load_dotenv
from cogs.encomendas import EncomendaCog

button_data = {}

API_DATA = {}

async def load_api_data():
    """Faz uma requisição à API e carrega os dados na variável global API_DATA."""
    print("[API] Iniciando a requisição à API...")
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(os.getenv("API_URL")) as response:
                response.raise_for_status() # Lança um erro se a resposta for 4xx ou 5xx
                global API_DATA
                API_DATA = await response.json()
                print("[API] Dados da API carregados com sucesso.")
        except aiohttp.ClientError as e:
            print(f"[ERRO] Falha ao carregar dados da API: {e}")
            API_DATA = None # Deixa a variável como None em caso de erro

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