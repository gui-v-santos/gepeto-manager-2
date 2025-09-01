import discord
from ui.embeds import ConfirmView
from cogs.calculator import find_price, calcular_custo_minimo

class NewOrder(discord.ui.Modal):
    def __init__(self, bot, button_data, receitas, precos, produtos_selecionados: list):
        super().__init__(title="Nova Encomenda")
        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos
        self.produtos_selecionados = produtos_selecionados

        self.campos_quantidade = {}

        # Campos fixos
        self.name = discord.ui.TextInput(label='Nome do Comprador', placeholder='Nome do comprador', required=True)
        self.pombo = discord.ui.TextInput(label='Pombo (ID)', placeholder='ID do pombo', required=True)
        self.prazo = discord.ui.TextInput(label='Prazo de Entrega', placeholder='Prazo em dias (ex: 3 dias)', required=True)
        self.add_item(self.name)
        self.add_item(self.pombo)

        # Campos dinâmicos para quantidade
        for produto_nome in self.produtos_selecionados:
            campo = discord.ui.TextInput(
                label=f"Quantidade de {produto_nome}",
                placeholder=f"Digite a quantidade para {produto_nome}",
                required=True,
                custom_id=f"quantidade_{produto_nome}"
            )
            self.add_item(campo)
            self.campos_quantidade[produto_nome] = campo

        # Adiciona prazo por último se houver espaço
        if len(self.children) < 5:
            self.add_item(self.prazo)

    async def on_submit(self, interaction: discord.Interaction):
        print(f"[MODAL] [{interaction.user.name}] processando os dados da encomenda...")

        produtos_list = []
        produtos_str_list = []
        total_custo_min = 0
        total_valor_venda = 0
        has_valid_sale_price = False

        for produto_nome, campo_input in self.campos_quantidade.items():
            try:
                quantidade = int(campo_input.value)
                if quantidade <= 0: continue
            except (ValueError, TypeError):
                continue

            produtos_list.append({'name': produto_nome, 'quantity': quantidade})
            produtos_str_list.append(f"{produto_nome}: {quantidade}")

            # Cálculo de custo de craft
            custo_min_item = calcular_custo_minimo(produto_nome, quantidade, self.receitas, self.precos)
            total_custo_min += custo_min_item

            # Cálculo de valor de venda
            preco_venda_unitario, _ = find_price(produto_nome, self.precos)
            if preco_venda_unitario is not None:
                total_valor_venda += round(quantidade * preco_venda_unitario, 2)
                has_valid_sale_price = True

        if not produtos_list:
            await interaction.response.send_message("❌ Nenhum produto com quantidade válida foi fornecido.", ephemeral=True)
            return

        # Monta o embed de confirmação
        embed = discord.Embed(title='Confirmar Nova Encomenda!', color=discord.Colour.random())

        preco_min_str = f"$ {total_custo_min:.0f}"
        valor_venda_str = f"$ {total_valor_venda:.0f}" if has_valid_sale_price else "N/A"

        embed.add_field(name='🧑 Nome', value=f'```{self.name.value}```', inline=False)
        embed.add_field(name='🕊️ Pombo', value=f'```{self.pombo.value}```', inline=False)
        embed.add_field(name='📦 Produtos e Quantidades', value=f'```{", ".join(produtos_str_list)}```', inline=False)
        embed.add_field(name='⏰ Prazo', value=f'```{self.prazo.value}```', inline=False)
        embed.add_field(name='💰 Custo Mínimo de Fabricação', value=f'```{preco_min_str}```', inline=False)
        embed.add_field(name='💵 Valor de Venda Mínimo', value=f'```{valor_venda_str}```', inline=False)
        embed.add_field(name='👤 Criado por', value=f'{interaction.user.mention}', inline=False)

        if total_custo_min == 0:
            embed.set_footer(text="Custo zerado. Verifique se todos os materiais base possuem preço.")

        view = ConfirmView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

        message = await interaction.original_response()
        self.button_data[message.id] = {
            'name': self.name.value,
            'pombo': self.pombo.value,
            'produtos': produtos_list,
            'prazo': self.prazo.value,
            'venda': valor_venda_str
        }

        print(f"[MODAL] [{interaction.user.name}] Embed enviado para confirmação, message ID: {message.id}")