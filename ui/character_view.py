# ui/character_view.py
import discord
from discord.ui import View, Button

class CharacterActivationView(View):
    def __init__(self, commands_list: list):
        super().__init__(timeout=None)
        self.commands_list = commands_list

    @discord.ui.button(label="Karakter aktiválása az Avrae-ben", style=discord.ButtonStyle.green, emoji="⚔️")
    async def activate_character(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True)
        if not self.commands_list:
            await interaction.followup.send("Nincsenek parancsok.", ephemeral=True)
            return

        for cmd in self.commands_list:
            await interaction.channel.send(cmd)

        button.disabled = True
        button.label = "Karakter Aktiválva!"
        button.style = discord.ButtonStyle.grey
        await interaction.message.edit(view=self)
