import discord
from ui.embeds import ConfirmView

from cogs.calculator import calcular_custo_craft

class NewOrder(discord.ui.Modal):
    def __init__(self, bot, button_data, receitas, precos, produto_predefinido: str = None):
        # Define o título dinamicamente com base no produto_predefinido
        title = f"Nova Encomenda: {produto_predefinido}" if produto_predefinido else "Nova Encomenda"
        super().__init__(title=title)
        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos
        self.produto_locked = produto_predefinido.strip() if produto_predefinido else None  # Armazena o produto predefinido

        self.name = discord.ui.TextInput(label='Nome', placeholder='Nome do comprador', required=True)
        self.pombo = discord.ui.TextInput(label='Pombo', placeholder='ID do pombo', required=True)
        self.quantidade = discord.ui.TextInput(label='Quantidade', placeholder='Quantidade do produto', required=True)
        self.prazo = discord.ui.TextInput(label='Prazo', placeholder='Prazo em dias', required=True)

        self.add_item(self.name)
        self.add_item(self.pombo)
        self.add_item(self.quantidade)
        self.add_item(self.prazo)

    async def on_submit(self, interaction: discord.Interaction):
        print(f"[MODAL] [{interaction.user.name}] processando os dados da encomenda...")

        produto_name = self.produto_locked if self.produto_locked else "Produto não especificado"

        try:
            quantidade = int(self.quantidade.value)
        except ValueError:
            quantidade = 1

        # CÁLCULO DE CUSTO DE CRAFT
        preco_min, preco_max = calcular_custo_craft(
            produto_name,
            quantidade,
            self.receitas,
            self.precos
        )

        embed = discord.Embed(title='Confirmar nova encomenda!', color=discord.Colour.random())

        if preco_min == 0 and preco_max == 0 and produto_name in self.receitas:
            preco_min_str = preco_max_str = "❓"
            embed.set_footer(text="Custo zerado. Verifique se todos os materiais base possuem preço.")
        else:
            preco_min_str = f"$ {preco_min}"
            preco_max_str = f"$ {preco_max}"

        embed.add_field(name='🧑 Nome', value=f'```{self.name.value}```', inline=False)
        embed.add_field(name='🕊️ Pombo', value=f'```{self.pombo.value}```', inline=False)
        embed.add_field(name='📦 Produto', value=f'```{produto_name}```', inline=False)
        embed.add_field(name='🔢 Quantidade', value=f'```{self.quantidade.value}```', inline=False)
        embed.add_field(name='⏰ Prazo', value=f'```{self.prazo.value}```', inline=False)
        embed.add_field(name='💰 Custo Mínimo de Fabricação', value=f'```{preco_min_str}```', inline=False)
        embed.add_field(name='💵 Valor de Venda Mínimo', value=f'```{preco_min_str}```', inline=False)

        embed.add_field(name='👤 Criado por', value=f'{interaction.user.mention}', inline=False)

        view = ConfirmView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        message = await interaction.original_response()
        self.button_data[message.id] = {
            'name': self.name.value,
            'pombo': self.pombo.value,
            'produto': produto_name,
            'quantidade': self.quantidade.value,
            'prazo': self.prazo.value,
            'venda': preco_min_str

        }

        print(f"[MODAL] [{interaction.user.name}] Embed enviado para confirmação, message ID: {message.id}")