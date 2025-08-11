import discord
from discord.ext import commands
from ui.modals import NewOrder
from ui.embeds import EncomendaView
import math
from collections import defaultdict
from ui.dropdown import ProdutoDropdownView

# ID do canal onde o botão de nova encomenda será enviado
ID_CANAL_ENCOMENDA = 1402582869280292894
# ID do canal onde as encomendas confirmadas serão publicadas
ID_CANAL_PUBLICO = 1160775850334113852
# ID do servidor (guild)
ID_GUILD = 1145126424248848514

def calcular_materiais(item_nome, quantidade_desejada, receitas, acumulador=None):
    if acumulador is None:
        acumulador = defaultdict(int)

    if item_nome not in receitas:
        acumulador[item_nome] += quantidade_desejada
        return acumulador

    receita = receitas[item_nome]
    produz_por_craft = receita['produz']
    quantidade_de_crafts = math.ceil(quantidade_desejada / produz_por_craft)

    for material in receita['materiais']:
        nome_material = material['nome']
        quantidade_por_craft = material['quantidade']
        total_para_item = quantidade_por_craft * quantidade_de_crafts
        calcular_materiais(nome_material, total_para_item, receitas, acumulador)

    return acumulador

def _formatar_bloco_individual(item, quantidade_desejada, receitas):
    """
    Formata a string de rateio para um único item, usando a lógica de lotes
    cheios e um lote final menor para otimizar a produção.
    """
    if item not in receitas:
        return ""

    receita = receitas[item]
    produz_por_craft = receita['produz']
    ingredientes = receita['materiais']

    total_crafts = math.ceil(quantidade_desejada / produz_por_craft)

    soma_materiais_por_craft = sum(mat['quantidade'] for mat in ingredientes)
    max_por_vez = math.floor(300 / soma_materiais_por_craft) if soma_materiais_por_craft > 0 else total_crafts
    if max_por_vez == 0: max_por_vez = 1

    # Lógica de Lotes Otimizada
    repeticoes = total_crafts // max_por_vez
    resto = total_crafts % max_por_vez

    total_produzido = total_crafts * produz_por_craft
    texto = f"Precisa: {quantidade_desejada} | Total a produzir: {total_produzido}\n\n"

    if repeticoes > 0:
        produz_por_lote = max_por_vez * produz_por_craft
        texto += f"📋 Instruções de Lote (Repetir {repeticoes} vezes):\n"
        texto += f"   - Fabricar: {produz_por_lote} (de {max_por_vez} fabricações)\n"
        texto += f"   - Materiais (para cada lote):\n"
        for mat in ingredientes:
            qtd_por_lote = mat['quantidade'] * max_por_vez
            texto += f"      - {mat['nome']}: {qtd_por_lote}\n"
        texto += "\n"

    if resto > 0:
        produz_no_final = resto * produz_por_craft
        texto += f"📋 Instruções do Lote Final (1 vez):\n"
        texto += f"   - Fabricar: {produz_no_final} (de {resto} fabricações)\n"
        texto += f"   - Materiais:\n"
        for mat in ingredientes:
            qtd_final = mat['quantidade'] * resto
            texto += f"      - {mat['nome']}: {qtd_final}\n"

    return texto.strip()

def gerar_blocos_de_rateio(item_raiz, quantidade_desejada, receitas):
    """
    Gera uma lista de blocos de texto de rateio, um para cada item craftável,
    de forma consolidada e na ordem correta.
    """

    # 1. Calcular a necessidade total de TODOS os itens (intermediários e crus)
    def calcular_necessidades_totais(item, qtd):
        necessidades = defaultdict(int)
        # Fila para processamento (item, quantidade)
        fila = [(item, qtd)]

        while fila:
            item_atual, qtd_atual = fila.pop(0)
            necessidades[item_atual] += qtd_atual

            if item_atual in receitas:
                receita = receitas[item_atual]
                # Quantidade de crafts necessários para a quantidade ACUMULADA do item
                crafts_necessarios = math.ceil(necessidades[item_atual] / receita['produz'])

                # Zera a necessidade do item que já foi processado para não entrar em loop
                necessidades[item_atual] = 0

                for mat in receita['materiais']:
                    fila.append((mat['nome'], mat['quantidade'] * crafts_necessarios))
        return necessidades

    # Na verdade, uma abordagem recursiva para calcular as necessidades de craft
    # é mais simples e menos propensa a erros de estado.
    def calcular_necessidades_craft(item, qtd, receitas):
        necessidades = defaultdict(int)

        # Adiciona a necessidade do item atual
        if item in receitas:
            necessidades[item] += qtd

        # Se não for craftável, não tem sub-materiais para adicionar
        if item not in receitas:
            return necessidades

        receita = receitas[item]
        crafts_necessarios = math.ceil(qtd / receita['produz'])

        for mat in receita['materiais']:
            sub_necessidades = calcular_necessidades_craft(mat['nome'], mat['quantidade'] * crafts_necessarios, receitas)
            for sub_item, sub_qtd in sub_necessidades.items():
                necessidades[sub_item] += sub_qtd

        return necessidades

    necessidades = calcular_necessidades_craft(item_raiz, quantidade_desejada, receitas)

    # 2. Obter a ordem de craft correta (top-down)
    ordem_de_craft = []
    visitados = set()
    def obter_ordem(item):
        if item in receitas and item not in visitados:
            visitados.add(item)
            ordem_de_craft.append(item)
            for mat in receitas[item]['materiais']:
                obter_ordem(mat['nome'])

    obter_ordem(item_raiz)

    # 3. Gerar os blocos de texto na ordem correta
    blocos = []
    for item in ordem_de_craft:
        if item in necessidades and necessidades[item] > 0:
            qtd = math.ceil(necessidades[item])
            bloco_str = _formatar_bloco_individual(item, qtd, receitas)
            if bloco_str:
                blocos.append((f"➡️ {item.upper()}", bloco_str))

    return blocos


def calcular_custo_minimo(item_final, quantidade, receitas, precos):
    materiais_necessarios = calcular_materiais(item_final, quantidade, receitas)
    custo_total = 0.0

    precos_min = {}
    if precos:
        for categoria in precos.values():
            if isinstance(categoria, dict) and 'min' in categoria and isinstance(categoria['min'], dict):
                precos_min.update(categoria['min'])

    for material, qtd in materiais_necessarios.items():
        preco_unitario = 0.0
        # 1. Tenta encontrar o preço exato do material na lista de preços achatada
        if material in precos_min:
            preco_unitario = precos_min[material]
        # 2. Se não encontrou um preço específico e o item é um minério (ou carvão),
        #    usa o preço genérico para "Qualquer Minério" como fallback.
        elif "Minério" in material or material == "Carvão":
            # Garante que a estrutura de preços da mineradora e o fallback existam
            if "mineradora" in precos and "min" in precos["mineradora"] and "Qualquer Minério" in precos["mineradora"]["min"]:
                preco_unitario = precos["mineradora"]["min"]["Qualquer Minério"]

        custo_total += float(qtd) * preco_unitario

    return custo_total

def dividir_em_blocos(texto, tamanho_max=1018):
    blocos = []
    bloco_atual = ""

    for linha in texto.splitlines(keepends=True):
        if len(bloco_atual) + len(linha) > tamanho_max:
            blocos.append(bloco_atual.rstrip())  # remove \n final se tiver
            bloco_atual = linha
        else:
            bloco_atual += linha

    if bloco_atual:
        blocos.append(bloco_atual.rstrip())

    return blocos

class EncomendaCog(commands.Cog):
    def __init__(self, bot: commands.Bot, button_data: dict, api_data: dict):
        self.bot = bot
        self.button_data = button_data
        self.api_data = api_data

    @commands.Cog.listener()
    async def on_ready(self):
        print("[COG] 'EncomendaCog' pronta.")
        
        guild = self.bot.get_guild(ID_GUILD)
        if not guild: return
        
        channel = guild.get_channel(ID_CANAL_ENCOMENDA)
        if not channel:
            print("[READY] Canal de encomenda não encontrado!")
            return

        message_found = None
        async for message in channel.history(limit=20):
            if message.author == self.bot.user and message.embeds and message.embeds[0].title == "Criar nova encomenda":
                message_found = message
                break

        if message_found:
            print(f"[READY] Mensagem de encomenda existente encontrada com ID: {message_found.id}")
            self.bot.add_view(EncomendaView())
        else:
            print("[READY] Nenhuma mensagem de encomenda encontrada, enviando nova...")
            embed = discord.Embed(
                title="Criar nova encomenda",
                description="Clique no botão abaixo para criar uma nova encomenda.",
                color=discord.Color.blue()
            )
            view = EncomendaView()
            await channel.send(embed=embed, view=view)
            print(f"[READY] Nova mensagem de encomenda enviada.")
            self.bot.add_view(view)

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return

        custom_id = interaction.data.get('custom_id')

        if custom_id == "botao_encomenda":
            if not self.api_data:
                await interaction.response.send_message(
                    "❌ Os dados da API não foram carregados. Tente novamente mais tarde.",
                    ephemeral=True
                )
                return

            allowed_roles_ids = self.api_data['permission']
            user_roles_ids = {str(role.id) for role in interaction.user.roles}
            if user_roles_ids.isdisjoint(allowed_roles_ids):
                await interaction.response.send_message(
                    "❌ Você não tem permissão para criar uma nova encomenda.",
                    ephemeral=True,
                    delete_after=5
                )
                return
            
            print(f"[INTERACTION] [{interaction.user.name}] Botão 'Nova Encomenda' clicado, abrindo modal...")
            receitas = self.api_data.get("receitas_crafting", {})
            precos = self.api_data.get("precos", {})
            view = ProdutoDropdownView(self.bot, self.button_data, receitas, precos)
            await interaction.response.send_message(
                "🛠️ Selecione um produto antes de criar a encomenda:",
                view=view,
                ephemeral=True
            )
            print(f"[INTERACTION] [{interaction.user.name}] Modal aberto com sucesso.")
            return

        if custom_id in ["confirmar_encomenda", "cancelar_encomenda"]:

            message_id = interaction.message.id
            data = self.button_data.get(message_id)

            if not data:
                return

            if custom_id == "confirmar_encomenda":
                print(f"[INTERACTION] [{interaction.user.name}] Botão 'Confirmar' clicado...")

                guild = self.bot.get_guild(ID_GUILD)
                public_channel = guild.get_channel(ID_CANAL_PUBLICO)

                name = data.get('name')
                pombo = data.get('pombo')
                produto = data.get('produto')
                quantidade = int(data.get('quantidade'))
                prazo = data.get('prazo')
                preco_min_str = data.get('venda')

                # CÁLCULOS
                receitas = self.api_data.get('receitas_crafting', {})
                precos = self.api_data.get('precos', {})
                custo_materiais = calcular_custo_minimo(produto, quantidade, receitas, precos)
                custo_materiais_str = f"R$ {custo_materiais:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

                public_embed = discord.Embed(title='Nova Encomenda Confirmada!', color=discord.Color.green())
                public_embed.add_field(name='Nome', value=f'```{name}```', inline=False)
                public_embed.add_field(name='Pombo', value=f'```{pombo}```', inline=False)
                public_embed.add_field(name='Produto', value=f'```{produto}```', inline=False)
                public_embed.add_field(name='Quantidade', value=f'```{quantidade}```', inline=False)
                public_embed.add_field(name='Prazo', value=f'```{prazo if str(prazo).lower().endswith(("dia","dias")) else str(prazo) + (" Dia" if str(prazo).strip() == "1" else " Dias")}```', inline=False)
                public_embed.add_field(name='Valor mínimo de venda', value=f'```{preco_min_str}```', inline=True)
                public_embed.add_field(name='Custo Mínimo dos Materiais', value=f'```{custo_materiais_str}```', inline=True)
                public_embed.add_field(name='\u200B', value= '', inline=False)
                public_embed.set_footer(text=f'Encomenda criada por {interaction.user.name}', icon_url=interaction.user.display_avatar.url)

                # CÁLCULO DE MATERIAIS
                materiais_necessarios = calcular_materiais(produto, quantidade, receitas)

                materiais_str = "\n".join(
                    [f"🔹 {item}: {int(float(quant))}" for item, quant in materiais_necessarios.items()]
                )
                public_embed.add_field(name='Materiais Necessários', value=materiais_str, inline=False)
                public_embed.add_field(name='\u200B', value= '', inline=False)
                
                blocos_rateio = gerar_blocos_de_rateio(produto, quantidade, receitas)

                for i, (titulo, conteudo) in enumerate(blocos_rateio[:25]):
                    # Verifica se o conteúdo não excede o limite de caracteres do Discord
                    if len(conteudo) > 1024:
                        # Se exceder, divide o conteúdo e adiciona como campos continuados
                        partes = dividir_em_blocos(conteudo)
                        for j, parte in enumerate(partes):
                            titulo_parte = titulo if j == 0 else f"{titulo} (cont.)"
                            public_embed.add_field(name=titulo_parte, value=f"```{parte}```", inline=False)
                    else:
                        public_embed.add_field(name=titulo, value=f"```{conteudo}```", inline=False)

                if len(blocos_rateio) > 25:
                    print("[WARNING] Rateio truncado por exceder 25 campos de embed.")


                pubic_message = await public_channel.send(embed=public_embed)
                public_message_link = f"https://discord.com/channels/{ID_GUILD}/{ID_CANAL_PUBLICO}/{pubic_message.id}"

                confirm_embed = discord.Embed(title='Encomenda Confirmada!', color=discord.Color.green())
                confirm_embed.add_field(name='', value=f"[Clique aqui para ver os\n Detalhes da encomenda]({public_message_link})", inline=False)
                await interaction.response.edit_message(embed=confirm_embed, view=None)
                print(f"[INTERACTION] [{interaction.user.name}] Encomenda confirmada e publicada.")

            elif custom_id == "cancelar_encomenda":
                print(f"[INTERACTION] [{interaction.user.name}] Botão 'Cancelar' clicado...")
                cancel_embed = discord.Embed(title='Encomenda Cancelada', color=discord.Color.red())
                await interaction.response.edit_message(embed=cancel_embed, view=None)
                print(f"[INTERACTION] [{interaction.user.name}] Encomenda cancelada.")
