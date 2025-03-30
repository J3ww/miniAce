import discord
import json
import os

class Logger:
    def __init__(self, storage_file="log_channel.json"):
        self.log_channel = None
        self.storage_file = storage_file
        self._load_channel()

    def _load_channel(self):
        if os.path.exists(self.storage_file):
            with open(self.storage_file, "r") as f:
                data = json.load(f)
                self.log_channel = data.get("channel_id")

    def _save_channel(self, channel_id):
        with open(self.storage_file, "w") as f:
            json.dump({"channel_id": channel_id}, f)

    def set_channel(self, channel: discord.TextChannel):
        self.log_channel = channel.id
        self._save_channel(channel.id)

    async def log(self, bot: discord.Client, interaction: discord.Interaction, **kwargs):
        if not self.log_channel:
            print("Log channel is not set. Please configure it using /setlogchannel.")
            return

        channel = bot.get_channel(self.log_channel)
        if not channel:
            print(f"Log channel with ID {self.log_channel} not found. Please verify the channel ID in log_channel.json.")
            return

        embed = discord.Embed(title="Role Command Log", color=discord.Color.blue())
        embed.add_field(name="Command User", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        for key, value in kwargs.items():
            embed.add_field(name=key, value=value, inline=False)
        await channel.send(embed=embed)

    async def log_perms_command(self, bot: discord.Client, interaction: discord.Interaction, action: str, target: str, command: str, subcommand: str = None):
        if not self.log_channel:
            print("Log channel is not set. Please configure it using /setlogchannel.")
            return

        channel = bot.get_channel(self.log_channel)
        if not channel:
            print(f"Log channel with ID {self.log_channel} not found. Please verify the channel ID in log_channel.json.")
            return

        embed = discord.Embed(title="Permissions Command Log", color=discord.Color.green())
        embed.add_field(name="Action", value=action, inline=False)
        embed.add_field(name="Target", value=target, inline=False)
        embed.add_field(name="Command", value=command, inline=False)
        if subcommand:
            embed.add_field(name="Subcommand", value=subcommand, inline=False)
        embed.add_field(name="Executed By", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        await channel.send(embed=embed)
