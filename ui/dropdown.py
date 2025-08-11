import discord
from ui.modals import NewOrder

class ProdutoDropdown(discord.ui.Select):
    def __init__(self, bot, button_data, receitas, precos):
        options = [
            discord.SelectOption(label=produto, value=produto)
            for produto in receitas.keys()
        ]

        super().__init__(
            placeholder="Escolha um produto...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="select_produto"
        )

        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos

    async def callback(self, interaction: discord.Interaction):
        produto_escolhido = self.values[0]

        await interaction.response.send_modal(NewOrder(
            self.bot,
            self.button_data,
            self.receitas,
            self.precos,
            produto_escolhido
        ))

class ProdutoDropdownView(discord.ui.View):
    def __init__(self, bot, button_data, receitas, precos):
        super().__init__(timeout=60)
        self.add_item(ProdutoDropdown(bot, button_data, receitas, precos))
