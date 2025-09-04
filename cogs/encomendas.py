import discord
from discord.ext import commands
from ui.modals import NewOrder
from ui.embeds import EncomendaView
import math
from collections import defaultdict
from ui.dropdown import ProdutoDropdownView
from .calculator import calcular_materiais_para_lista, calcular_custo_de_materiais

# ID do canal onde o botão de nova encomenda será enviado
ID_CANAL_ENCOMENDA = 1402582869280292894
# ID do canal onde as encomendas confirmadas serão publicadas
ID_CANAL_PUBLICO = 1160775850334113852
# ID do servidor (guild)
ID_GUILD = 1145126424248848514

def _formatar_bloco_individual(item, quantidade_desejada, receitas, craft_size):
    if item not in receitas:
        return ""
    receita = receitas[item]
    produz_por_craft = receita['produz']
    ingredientes = receita['materiais']
    total_crafts = math.ceil(quantidade_desejada / produz_por_craft)
    soma_materiais_por_craft = sum(mat['quantidade'] for mat in ingredientes)
    max_por_vez = math.floor(craft_size / soma_materiais_por_craft) if soma_materiais_por_craft > 0 else total_crafts
    if max_por_vez == 0: max_por_vez = 1
    repeticoes = total_crafts // max_por_vez
    resto = total_crafts % max_por_vez
    total_produzido = total_crafts * produz_por_craft
    texto = f"Precisa: {quantidade_desejada} | Total a produzir: {total_produzido}\n\n"
    if repeticoes > 0:
        produz_por_lote = max_por_vez * produz_por_craft
        texto += f"📋 Instruções de Lote:\n"
        texto += f"   - Repetir {repeticoes} vezes\n"
        texto += f"   - Produzir {produz_por_lote}\n"
        texto += f"   - Solicita por Vez: {max_por_vez}\n"
        texto += f"   - Materiais (para cada lote):\n"
        for mat in ingredientes:
            qtd_por_lote = mat['quantidade'] * max_por_vez
            texto += f"      - {mat['nome']}: {qtd_por_lote}\n"
        texto += "\n"
    if resto > 0:
        produz_no_final = resto * produz_por_craft
        texto += f"📋 Instruções do Lote Final:\n"
        texto += f"   - Repetir 1 vez\n"
        texto += f"   - Produzir {produz_no_final}\n"
        texto += f"   - Solicita por Vez: {max_por_vez}\n"
        texto += f"   - Materiais (para cada lote):\n"
        for mat in ingredientes:
            qtd_final = mat['quantidade'] * resto
            texto += f"      - {mat['nome']}: {qtd_final}\n"
    return texto.strip()

def dividir_em_blocos(texto, tamanho_max=1018):
    blocos = []
    bloco_atual = ""
    for linha in texto.splitlines(keepends=True):
        if len(bloco_atual) + len(linha) > tamanho_max:
            blocos.append(bloco_atual.rstrip())
            bloco_atual = linha
        else:
            bloco_atual += linha
    if bloco_atual:
        blocos.append(bloco_atual.rstrip())
    return blocos

def calcular_necessidades_intermediarios(produtos_list, receitas):
    necessidades = defaultdict(float)
    a_processar = [(p['name'], p['quantity']) for p in produtos_list]

    while a_processar:
        item, quantidade = a_processar.pop(0)

        if item in receitas:
            receita = receitas[item]
            crafts_necessarios = math.ceil(quantidade / receita['produz'])
            necessidades[item] += quantidade
            for material in receita['materiais']:
                a_processar.append((material['nome'], material['quantidade'] * crafts_necessarios))
    return necessidades

def gerar_blocos_de_rateio_para_lista(produtos_list, receitas, craft_size):
    all_craft_needs = calcular_necessidades_intermediarios(produtos_list, receitas)
    craft_order = []
    visited = set()
    def get_order(item):
        if item in receitas and item not in visited:
            visited.add(item)
            craft_order.append(item)
            for material in receitas[item]['materiais']:
                get_order(material['nome'])
    for produto in produtos_list:
        get_order(produto['name'])

    blocos_finais = []
    for item in craft_order:
        if item in all_craft_needs and all_craft_needs[item] > 0:
            total_a_produzir = math.ceil(all_craft_needs[item])
            bloco_str = _formatar_bloco_individual(item, total_a_produzir, receitas, craft_size)
            if bloco_str:
                blocos_finais.append((f"➡️ {item.upper()}", bloco_str))
    return blocos_finais

class EncomendaCog(commands.Cog):
    def __init__(self, bot: commands.Bot, button_data: dict, api_data: dict):
        self.bot = bot
        self.button_data = button_data
        self.api_data = api_data

    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(ID_GUILD)
        if not guild: return
        channel = guild.get_channel(ID_CANAL_ENCOMENDA)
        if not channel: return

        message_found = None
        async for message in channel.history(limit=20):
            if message.author == self.bot.user and message.embeds and message.embeds[0].title == "Criar nova encomenda":
                break

        self.bot.add_view(EncomendaView())

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get('custom_id', '')

        if custom_id == "botao_encomenda":
            if not self.api_data:
                await interaction.response.send_message("❌ Os dados da API não foram carregados.", ephemeral=True)
                return

            allowed_roles_ids = self.api_data.get('permission', [])
            user_roles_ids = {str(role.id) for role in interaction.user.roles}
            if user_roles_ids.isdisjoint(allowed_roles_ids):
                await interaction.response.send_message("❌ Você não tem permissão.", ephemeral=True, delete_after=5)
                return

            receitas = self.api_data.get("receitas_crafting", {})
            precos = self.api_data.get("precos", {})
            view = ProdutoDropdownView(self.bot, self.button_data, receitas, precos)
            await interaction.response.send_message("🛠️ Selecione os produtos que deseja encomendar:", view=view, ephemeral=True)
            return

        if custom_id in ["confirmar_encomenda", "cancelar_encomenda"]:
            message_id = interaction.message.id
            data = self.button_data.get(message_id)
            if not data: return

            if custom_id == "confirmar_encomenda":
                guild = self.bot.get_guild(ID_GUILD)
                public_channel = guild.get_channel(ID_CANAL_PUBLICO)

                name, pombo, produtos_list, prazo, preco_min_str = data.get('name'), data.get('pombo'), data.get('produtos', []), data.get('prazo'), data.get('venda')

                receitas = self.api_data.get('receitas_crafting', {})
                precos = self.api_data.get('precos', {})

                # 1. Calcular os materiais brutos para o custo
                materiais_brutos_para_custo = calcular_materiais_para_lista(produtos_list, receitas)
                custo_total = calcular_custo_de_materiais(materiais_brutos_para_custo, precos)
                custo_materiais_str = f"$ {custo_total:.0f}".replace(",", "X").replace(".", ",").replace("X", ".")

                # 2. Preparar a lista de materiais para exibição
                materiais_para_exibir = calcular_materiais_para_lista(produtos_list, receitas)
                necessidades_intermediarios = calcular_necessidades_intermediarios(produtos_list, receitas)
                if 'Farelo de Minério' in necessidades_intermediarios:
                    materiais_para_exibir['Farelo de Minério'] = necessidades_intermediarios['Farelo de Minério']

                # 3. Obter o craft_size das configurações
                craft_size = self.api_data.get('settings', {}).get('craft-size', 300)

                # 4. Gerar o embed
                produtos_str = "\n".join([f"🔹 {p['name']}: {p['quantity']}" for p in produtos_list])

                public_embed = discord.Embed(title='Nova Encomenda Confirmada!', color=discord.Color.green())
                public_embed.add_field(name='Nome', value=f'```{name}```', inline=False)
                public_embed.add_field(name='Pombo', value=f'```{pombo}```', inline=False)
                public_embed.add_field(name='Prazo', value=f'```{prazo}```', inline=False)
                public_embed.add_field(name='Valor Mínimo de Venda', value=f'```{preco_min_str}```', inline=True)
                public_embed.add_field(name='Custo dos Materiais', value=f'```{custo_materiais_str}```', inline=True)
                public_embed.add_field(name='\u200B', value='', inline=False)
                public_embed.set_footer(text=f'Encomenda criada por {interaction.user.name}', icon_url=interaction.user.display_avatar.url)

                public_embed.add_field(name='Produtos', value=f'```{produtos_str}```', inline=False)
                materiais_formatados_str = "\n".join([f"🔹 {item}: {math.ceil(quant)}" for item, quant in sorted(materiais_para_exibir.items())])
                if materiais_formatados_str:
                    public_embed.add_field(name='Materiais Necessários (Total)', value=f"```{materiais_formatados_str}```", inline=False)
                    public_embed.add_field(name='\u200B', value='', inline=False)

                blocos_rateio = gerar_blocos_de_rateio_para_lista(produtos_list, receitas, craft_size)
                craft_size = self.api_data.get('settings', {}).get('craft-size', 300)
                print(craft_size, " sizeeeeeeeeeeeeeeeeeeeeeeee")
                blocos_rateio = gerar_blocos_de_rateio_para_lista(produtos_list, receitas)

                for i, (titulo, conteudo) in enumerate(blocos_rateio[:23]):
                    if len(conteudo) > 1024:
                        partes = dividir_em_blocos(conteudo)
                        for j, parte in enumerate(partes):
                            titulo_parte = titulo if j == 0 else f"{titulo} (cont.)"
                            public_embed.add_field(name=titulo_parte, value=f"```{parte}```", inline=False)
                    else:
                        public_embed.add_field(name=titulo, value=f"```{conteudo}```", inline=False)

                if len(blocos_rateio) > 23:
                    print("[WARNING] Rateio truncado por exceder limite de campos do embed.")

                pubic_message = await public_channel.send(embed=public_embed)
                public_message_link = f"https://discord.com/channels/{ID_GUILD}/{ID_CANAL_PUBLICO}/{pubic_message.id}"

                confirm_embed = discord.Embed(title='Encomenda Confirmada!', color=discord.Color.green())
                confirm_embed.add_field(name='', value=f"✅ [Clique aqui para ver os detalhes]({public_message_link})")
                await interaction.response.edit_message(embed=confirm_embed, view=None)

            elif custom_id == "cancelar_encomenda":
                cancel_embed = discord.Embed(title='Encomenda Cancelada', color=discord.Color.red())
                await interaction.response.edit_message(embed=cancel_embed, view=None)
