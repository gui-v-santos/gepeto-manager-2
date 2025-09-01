import discord
from ui.modals import NewOrder

class ProdutoDropdown(discord.ui.Select):
    def __init__(self, bot, button_data, receitas, precos, index, selecionados):
        # Cria opções de acordo com receitas
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

        # Preenche a seleção anterior se ela existir.
        if selecionados and index in selecionados and selecionados[index] is not None:
            for option in self.options:
                if option.value == selecionados[index]:
                    option.default = True
                    break

    async def callback(self, interaction: discord.Interaction):
        # Defer the interaction to avoid "interaction failed"
        await interaction.response.defer(ephemeral=True, thinking=False)

        # Update the selection in the view's state
        self.view.selecoes[self.index] = self.values[0]

        # Rebuild the entire view to reflect the new state
        self.view.build_view()

        # Edit the original message with the updated view
        try:
            await interaction.message.edit(view=self.view)
        except discord.errors.NotFound:
            # This can happen if the original message was deleted
            pass


class ProdutoDropdownView(discord.ui.View):
    def __init__(self, bot, button_data, receitas, precos, selecoes=None):
        super().__init__(timeout=300)
        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos
        self.selecoes = selecoes if selecoes is not None else {}

        # Garante que sempre haja pelo menos um dropdown no início.
        if not self.selecoes:
            self.selecoes[0] = None

        # Constrói a view no início.
        self.build_view()

    def build_view(self):
        # Limpa todos os itens existentes para reconstruir a view corretamente.
        self.clear_items()

        # Adiciona todos os dropdowns com base no dicionário 'selecoes'.
        for i in sorted(self.selecoes.keys()):
            self.add_item(ProdutoDropdown(self.bot, self.button_data, self.receitas, self.precos, i, self.selecoes))

        # Adiciona os botões no final, criando novas instâncias para evitar o erro de duplicação.
        self.add_item(self.AdicionarItem(self))
        self.add_item(self.EnviarEncomenda(self))

    class AdicionarItem(discord.ui.Button):
        def __init__(self, parent_view):
            super().__init__(label="➕ Adicionar Item", style=discord.ButtonStyle.primary)
            self.parent_view = parent_view

        async def callback(self, interaction: discord.Interaction):
            # Limite de 4 dropdowns + 1 linha de botões = 5 linhas (limite do Discord)
            if len(self.parent_view.selecoes) >= 4:
                await interaction.response.send_message(
                    "❌ Você atingiu o limite de 4 produtos por encomenda.",
                    ephemeral=True,
                    delete_after=10
                )
                return

            await interaction.response.defer(ephemeral=True, thinking=False)

            # Define o novo índice para o próximo dropdown
            if not self.parent_view.selecoes:
                new_dropdown_index = 0
            else:
                new_dropdown_index = max(self.parent_view.selecoes.keys()) + 1

            # Adiciona um marcador no dicionário de seleções para o novo dropdown
            self.parent_view.selecoes[new_dropdown_index] = None

            # Chama o método que reconstrói a view
            self.parent_view.build_view()

            # Tenta editar a mensagem com a view reconstruída
            try:
                await interaction.message.edit(view=self.parent_view)
            except discord.errors.NotFound:
                pass


    class EnviarEncomenda(discord.ui.Button):
        def __init__(self, parent_view):
            super().__init__(label="Enviar Encomenda", style=discord.ButtonStyle.success)
            self.parent_view = parent_view

        async def callback(self, interaction: discord.Interaction):
            # Filtra para obter uma lista de nomes de produtos únicos.
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

            # Abre o modal NewOrder, passando a lista de produtos.
            modal = NewOrder(
                bot=self.parent_view.bot,
                button_data=self.parent_view.button_data,
                receitas=self.parent_view.receitas,
                precos=self.parent_view.precos,
                produtos_selecionados=produtos_selecionados
            )
            await interaction.response.send_modal(modal)
