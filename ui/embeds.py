import discord

class EncomendaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        
    @discord.ui.button(label="Nova Encomenda", style=discord.ButtonStyle.green, custom_id="botao_encomenda")
    async def novo_encomenda_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # A lógica para o clique neste botão é tratada na cog[encomendas.py] (on_interaction)
        pass

class ConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=300) # Timeout de 5 minutos
        
    @discord.ui.button(label="Cancelar", style=discord.ButtonStyle.red, custom_id="cancelar_encomenda")
    async def cancelar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # A lógica para o clique neste botão é tratada na cog[encomendas.py] (on_interaction)
        pass

    @discord.ui.button(label="Confirmar", style=discord.ButtonStyle.green, custom_id="confirmar_encomenda")
    async def confirmar_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # A lógica para o clique neste botão é tratada na cog[encomendas.py] (on_interaction)
        pass