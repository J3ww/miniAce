from discord import app_commands
import discord

async def role_autocomplete(interaction: discord.Interaction, current: str):
    try:
        roles = [r for r in interaction.guild.roles if current.lower() in r.name.lower()]
        return [app_commands.Choice(name=r.name, value=r.name) for r in roles[:25]]
    except discord.errors.NotFound:
        print("Autocomplete interaction was not found (likely expired).")
        return []
