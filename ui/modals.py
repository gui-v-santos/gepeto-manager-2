import discord
from ui.embeds import ConfirmView
from cogs.calculator import find_price, calcular_custo_minimo
import re


class NewOrder(discord.ui.Modal):
    def __init__(self, bot, button_data, receitas, precos):
        title = "Nova Encomenda"
        super().__init__(title=title)
        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos

        self.name = discord.ui.TextInput(
            label='Nome',
            placeholder='Nome do comprador',
            required=True
        )
        self.pombo = discord.ui.TextInput(
            label='Pombo',
            placeholder='ID do pombo',
            required=True
        )
        self.produtos = discord.ui.TextInput(
            label='Produtos e Quantidades',
            style=discord.TextStyle.paragraph,
            placeholder='Coloque cada produto em uma nova linha no formato:\nNome do Produto: Quantidade\n\nExemplo:\nLockpick: 50\nAdaga de Ferro: 10',
            required=True
        )
        self.prazo = discord.ui.TextInput(
            label='Prazo',
            placeholder='Prazo em dias',
            required=True
        )

        self.add_item(self.name)
        self.add_item(self.pombo)
        self.add_item(self.produtos)
        self.add_item(self.prazo)

    async def on_submit(self, interaction: discord.Interaction):
        print(f"[MODAL] [{interaction.user.name}] processando os dados da encomenda...")

        produtos_input = self.produtos.value.strip().split('\n')
        produtos_list = []
        produtos_str = []
        total_custo_min = 0
        total_valor_venda = 0
        has_valid_sale_price = False

        for line in produtos_input:
            match = re.match(r'([^:]+):\s*(\d+)', line)
            if not match:
                continue

            produto_name = match.group(1).strip()
            try:
                quantidade = int(match.group(2).strip())
            except ValueError:
                continue

            if produto_name not in self.receitas:
                # Opcional: notificar sobre produto inválido
                continue

            produtos_list.append({'name': produto_name, 'quantity': quantidade})
            produtos_str.append(f"{produto_name}: {quantidade}")

            # CÁLCULO DE CUSTO DE CRAFT
            custo_min_item = calcular_custo_minimo(
                produto_name,
                quantidade,
                self.receitas,
                self.precos
            )
            total_custo_min += custo_min_item

            # CÁLCULO DE VALOR DE VENDA
            preco_venda_unitario, _ = find_price(produto_name, self.precos)
            if preco_venda_unitario is not None:
                total_valor_venda += round(quantidade * preco_venda_unitario, 2)
                has_valid_sale_price = True

        if not produtos_list:
            await interaction.response.send_message(
                "❌ Nenhum produto válido foi inserido. Por favor, use o formato 'Nome do Produto: Quantidade'.",
                ephemeral=True
            )
            return

        embed = discord.Embed(title='Confirmar nova encomenda!', color=discord.Colour.random())

        preco_min_str = f"$ {total_custo_min:.0f}"
        valor_venda_str = f"$ {total_valor_venda:.0f}" if has_valid_sale_price else "N/A"

        embed.add_field(name='🧑 Nome', value=f'```{self.name.value}```', inline=False)
        embed.add_field(name='🕊️ Pombo', value=f'```{self.pombo.value}```', inline=False)
        embed.add_field(name='📦 Produtos', value=f'```{", ".join(produtos_str)}```', inline=False)
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
            'produtos': produtos_list, # Lista de dicionários
            'prazo': self.prazo.value,
            'venda': valor_venda_str
        }

        print(f"[MODAL] [{interaction.user.name}] Embed enviado para confirmação, message ID: {message.id}")