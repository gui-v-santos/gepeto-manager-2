import discord
from ui.embeds import ConfirmView
from cogs.calculator import find_price, calcular_custo_minimo
import re

class NewOrder(discord.ui.Modal):
    def __init__(self, bot, button_data, receitas, precos, produtos_selecionados: list):
        super().__init__(title="Nova Encomenda")
        self.bot = bot
        self.button_data = button_data
        self.receitas = receitas
        self.precos = precos

        # Preenche o valor padrão para o campo de texto de quantidades
        quantidades_default = "\n".join([f"{nome}: 1" for nome in produtos_selecionados])

        # Componentes fixos do modal
        self.name = discord.ui.TextInput(label='Nome do Comprador', required=True)
        self.pombo = discord.ui.TextInput(label='Pombo (ID)', required=True)
        self.prazo = discord.ui.TextInput(label='Prazo de Entrega', required=True)
        self.quantidades = discord.ui.TextInput(
            label="Produtos e Quantidades",
            style=discord.TextStyle.paragraph,
            default=quantidades_default,
            required=True
        )

        self.add_item(self.name)
        self.add_item(self.pombo)
        self.add_item(self.prazo)
        self.add_item(self.quantidades)


    async def on_submit(self, interaction: discord.Interaction):
        print(f"[MODAL] [{interaction.user.name}] processando os dados da encomenda...")

        produtos_list = []
        total_custo_min = 0
        total_valor_venda = 0
        has_valid_sale_price = False

        # Analisa o campo de texto de quantidades
        linhas = self.quantidades.value.strip().split('\n')
        for linha in linhas:
            match = re.match(r'([^:]+):\s*(\d+)', linha)
            if not match:
                continue

            produto_nome = match.group(1).strip()
            try:
                quantidade = int(match.group(2).strip())
                if quantidade <= 0: continue
            except (ValueError, TypeError):
                continue

            produtos_list.append({'name': produto_nome, 'quantity': quantidade})

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

        produtos_str_list = [f"{p['name']}: {p['quantity']}" for p in produtos_list]
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