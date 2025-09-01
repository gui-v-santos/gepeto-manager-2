import discord
from ui.modals import NewOrder

class ProdutoDropdown(discord.ui.Select):
    def __init__(self, bot, button_data, receitas, precos, index, selecionados):
        options = [
            discord.SelectOption(label=produto, value=produto)
            for produto in receitas.keys()
        ]
        super().__init__(
            placeholder=f"Escolha o produto #{index+1}...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"select_produto_{index}"
        )
        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos
        self.index = index
        if selecionados and index in selecionados and selecionados[index] is not None:
            for option in self.options:
                if option.value == selecionados[index]:
                    option.default = True
                    break

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=False)
        self.view.selecoes[self.index] = self.values[0]
        try:
            await interaction.message.edit(view=self.view)
        except discord.errors.NotFound:
            pass

class ProdutoDropdownView(discord.ui.View):
    def __init__(self, bot, button_data, receitas, precos, selecoes=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos
        self.selecoes = selecoes if selecoes is not None else {}
        if not self.selecoes:
            self.selecoes[0] = None
        self.build_view()

    def build_view(self):
        self.clear_items()
        for i in sorted(self.selecoes.keys()):
            self.add_item(ProdutoDropdown(self.bot, self.button_data, self.receitas, self.precos, i, self.selecoes))
        self.add_item(self.AdicionarItem(self))
        self.add_item(self.EnviarEncomenda(self))

    class AdicionarItem(discord.ui.Button):
        def __init__(self, parent_view):
            super().__init__(label="Adicionar Item", style=discord.ButtonStyle.primary)
            self.parent_view = parent_view

        async def callback(self, interaction: discord.Interaction):
            if len(self.parent_view.selecoes) >= 4:
                await interaction.response.send_message(
                    "❌ Você atingiu o limite de 4 produtos por encomenda.",
                    ephemeral=True,
                    delete_after=10
                )
                return
            if not self.parent_view.selecoes:
                new_dropdown_index = 0
            else:
                new_dropdown_index = max(self.parent_view.selecoes.keys()) + 1
            self.parent_view.selecoes[new_dropdown_index] = None
            self.parent_view.build_view()
            await interaction.response.edit_message(view=self.parent_view)

    class EnviarEncomenda(discord.ui.Button):
        def __init__(self, parent_view):
            super().__init__(label="Continuar...", style=discord.ButtonStyle.success)
            self.parent_view = parent_view

        async def callback(self, interaction: discord.Interaction):
            produtos_selecionados = sorted(list(set(
                self.parent_view.selecoes[key]
                for key in self.parent_view.selecoes
                if self.parent_view.selecoes[key] is not None
            )))
            if not produtos_selecionados:
                await interaction.response.send_message(
                    "⚠️ Nenhum produto selecionado!",
                    ephemeral=True,
                    delete_after=5
                )
                return
            modal = NewOrder(
                bot=self.parent_view.bot,
                button_data=self.parent_view.button_data,
                receitas=self.parent_view.receitas,
                precos=self.parent_view.precos,
                produtos_selecionados=produtos_selecionados
            )
            await interaction.response.send_modal(modal)
