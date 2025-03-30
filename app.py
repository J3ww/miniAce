import discord
from discord.ext import commands
from discord import app_commands
from config import TOKEN, PERMISSIONS, save_permissions, ROLE_MANAGERS, ROLE_ADMINS
from commands.role_commands import role_group, logger as role_logger
from utils.logger import Logger
from utils.permissions import add_permission, has_permission
import json

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="~", intents=intents)
logger = Logger()

@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        bot.synced = True
        print(f"Commands synced successfully. Registered commands: {[cmd.name for cmd in bot.tree.get_commands()]}")
        
        # Automatically grant the guild owner the * permission
        for guild in bot.guilds:
            owner_id = guild.owner_id
            guild_id = guild.id
            if guild_id not in PERMISSIONS:
                PERMISSIONS[guild_id] = {}
            if owner_id not in PERMISSIONS[guild_id]:
                PERMISSIONS[guild_id][owner_id] = {}
            if "*" not in PERMISSIONS[guild_id][owner_id]:
                PERMISSIONS[guild_id][owner_id]["*"] = ["*"]
                save_permissions()
                print(f"Granted * permission to the owner of guild {guild.name} ({guild.id}).")
    except Exception as e:
        print(f"Error syncing commands or granting owner permissions: {e}")

@bot.event
async def on_guild_join(guild: discord.Guild):
    # Automatically grant the guild owner the * permission when the bot joins a new guild
    try:
        owner_id = guild.owner_id
        guild_id = guild.id
        if guild_id not in PERMISSIONS:
            PERMISSIONS[guild_id] = {}
        if owner_id not in PERMISSIONS[guild_id]:
            PERMISSIONS[guild_id][owner_id] = {}
        if "*" not in PERMISSIONS[guild_id][owner_id]:
            PERMISSIONS[guild_id][owner_id]["*"] = ["*"]
            save_permissions()
            print(f"Granted * permission to the owner of new guild {guild.name} ({guild.id}).")
    except Exception as e:
        print(f"Error granting owner permissions for new guild {guild.name} ({guild.id}): {e}")

@bot.tree.command(name="setlogchannel", description="Set the logging output channel.")
async def set_log_channel(interaction: discord.Interaction):
    if not has_permission(interaction, "setlogchannel"):
        await interaction.response.send_message("Yo, you ain't got the juice to set the log channel, homie.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    logger.set_channel(interaction.channel)
    role_logger.set_channel(interaction.channel)

    await interaction.followup.send(f"Aight, logging channel is now {interaction.channel.mention}. Keep it real.", ephemeral=True)

@bot.tree.command(name="testlog", description="Test the logging system.")
async def test_log(interaction: discord.Interaction):
    if not has_permission(interaction, "testlog"):
        await interaction.response.send_message("Nah, you ain't got the clearance to test the logs, boss.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    await logger.log(
        bot,
        interaction,
        Action="Test Log",
        Message="This is a test log message."
    )
    await interaction.followup.send("Logs tested, all good in the hood.", ephemeral=True)

async def command_autocomplete(interaction: discord.Interaction, current: str):
    bot_commands = [
        app_commands.Choice(name=cmd.name, value=cmd.name)
        for cmd in bot.tree.get_commands() if current.lower() in cmd.name.lower()
    ]

    discord_permissions = [
        app_commands.Choice(name=perm, value=perm)
        for perm in discord.Permissions.VALID_FLAGS if current.lower() in perm.lower()
    ]


    wildcard_option = [app_commands.Choice(name="*", value="*")]

    combined_choices = bot_commands + discord_permissions + wildcard_option
    return combined_choices[:25]

@bot.tree.command(name="perms", description="Manage permissions.")
@app_commands.describe(
    action="Action to perform (add/remove)",
    target="User or Role mention or ID",
    command="Command or Discord permission to modify (use '*' for Master Access)",
    subcommand="Subcommand to modify permissions for (optional)"
)
@app_commands.autocomplete(command=command_autocomplete)
async def manage_permissions(interaction: discord.Interaction, action: str, target: str, command: str, subcommand: str = None):
    if not has_permission(interaction, "perms"):
        await interaction.response.send_message("Yo, you ain't got the authority to mess with permissions, dawg.", ephemeral=True)
        return

    await logger.log_perms_command(bot, interaction, action, target, command, subcommand)

    available_commands = [cmd.name for cmd in bot.tree.get_commands()]
    available_permissions = list(discord.Permissions.VALID_FLAGS)
    if command != "*" and command not in available_commands and command not in available_permissions and not command.startswith("role "):
        await interaction.response.send_message(
            f"Yo, I don't know what '{command}' is. Check your list, playa.", 
            ephemeral=True
        )
        return

    try:
        if target.startswith("<@&") and target.endswith(">"):
            target_id = int(target[3:-1])
            target_type = "role"
        elif target.startswith("<@") and target.endswith(">"):
            target_id = int(target[2:-1])
            target_type = "user"
        else:
            target_id = int(target)
            target_type = "user" if interaction.guild.get_member(target_id) else "role"
    except ValueError:
        await interaction.response.send_message("Invalid target format. Use a mention or ID.", ephemeral=True)
        return

    guild_id = interaction.guild.id
    if action == "add":
        if command == "*":
            if guild_id not in PERMISSIONS:
                PERMISSIONS[guild_id] = {}
            if target_id not in PERMISSIONS[guild_id]:
                PERMISSIONS[guild_id][target_id] = {}
            PERMISSIONS[guild_id][target_id]["*"] = ["*"]
            save_permissions()

            try:
                if target_type == "role":
                    role = interaction.guild.get_role(target_id)
                    if role:
                        await role.edit(permissions=discord.Permissions(administrator=True))
                elif target_type == "user":
                    member = interaction.guild.get_member(target_id)
                    if member:
                        admin_role = discord.utils.get(interaction.guild.roles, name="Administrator")
                        if not admin_role:
                            admin_role = await interaction.guild.create_role(name="Administrator", permissions=discord.Permissions(administrator=True))
                        await member.add_roles(admin_role)
            except discord.Forbidden:
                await interaction.response.send_message(
                    "I do not have sufficient permissions to grant Administrator access. Please ensure my role is higher in the role hierarchy and has the necessary permissions.",
                    ephemeral=True
                )
                return

            await interaction.response.send_message(f"Master Access granted to {target}.", ephemeral=True)
        else:
            add_permission(guild_id, target_id, command, subcommand)
            save_permissions()
            await interaction.response.send_message(f"Aight, {target} now got access to {command} {subcommand or ''}.", ephemeral=True)
    elif action == "remove":
        if command == "*":
            if guild_id in PERMISSIONS and target_id in PERMISSIONS[guild_id]:
                if "*" in PERMISSIONS[guild_id][target_id]:
                    del PERMISSIONS[guild_id][target_id]["*"]
                    if not PERMISSIONS[guild_id][target_id]:
                        del PERMISSIONS[guild_id][target_id]
                    save_permissions()

                    try:
                        if target_type == "role":
                            role = interaction.guild.get_role(target_id)
                            if role:
                                await role.edit(permissions=discord.Permissions.none())
                        elif target_type == "user":
                            member = interaction.guild.get_member(target_id)
                            if member:
                                admin_role = discord.utils.get(interaction.guild.roles, name="Administrator")
                                if admin_role:
                                    await member.remove_roles(admin_role)
                    except discord.Forbidden:
                        await interaction.response.send_message(
                            "I do not have sufficient permissions to revoke Administrator access. Please ensure my role is higher in the role hierarchy and has the necessary permissions.",
                            ephemeral=True
                        )
                        return

                    await interaction.response.send_message(f"Master Access revoked from {target}.", ephemeral=True)
                    return
            await interaction.response.send_message("Master Access not found for the target.", ephemeral=True)
        else:
            if guild_id in PERMISSIONS and target_id in PERMISSIONS[guild_id]:
                if command in PERMISSIONS[guild_id][target_id]:
                    if subcommand:
                        if subcommand in PERMISSIONS[guild_id][target_id][command]:
                            PERMISSIONS[guild_id][target_id][command].remove(subcommand)
                            if not PERMISSIONS[guild_id][target_id][command]:
                                del PERMISSIONS[guild_id][target_id][command]
                            save_permissions()
                            await interaction.response.send_message(
                                f"Permission removed for {target} on {command} {subcommand}.", ephemeral=True
                            )
                            return
                        else:
                            await interaction.response.send_message(
                                f"Subcommand '{subcommand}' not found for {command}.", ephemeral=True
                            )
                            return
                    else:
                        del PERMISSIONS[guild_id][target_id][command]
                        if not PERMISSIONS[guild_id][target_id]:
                            del PERMISSIONS[guild_id][target_id]
                        save_permissions()
                        await interaction.response.send_message(
                            f"Permission removed for {target} on {command}.", ephemeral=True
                        )
                        return
            await interaction.response.send_message("Permission not found.", ephemeral=True)
    else:
        await interaction.response.send_message("Yo, pick 'add' or 'remove', don't be special.", ephemeral=True)

@bot.tree.command(name="showperms", description="Output the current permissions to the console.")
async def show_permissions(interaction: discord.Interaction):
    if not has_permission(interaction, "showperms"):
        await interaction.response.send_message("You ain't got the clearance to see the permissions, homie.", ephemeral=True)
        return
    await interaction.response.send_message("Permissions have been dropped in the console. Check it out, boss.", ephemeral=True)

@bot.tree.command(name="checkperms", description="Check your set of permissions.")
async def check_permissions(interaction: discord.Interaction):
    if not has_permission(interaction, "checkperms"):
        await interaction.response.send_message("Nah, you ain't allowed to check your permissions, playa.", ephemeral=True)
        return
    user_id = interaction.user.id
    role_ids = [role.id for role in interaction.user.roles]
    guild_id = interaction.guild.id

    user_perms = {}
    role_manager_roles = []
    role_admin_roles = []

    if guild_id in PERMISSIONS:
        if user_id in PERMISSIONS[guild_id]:
            user_perms["User"] = PERMISSIONS[guild_id][user_id]
        for role_id in role_ids:
            if role_id in PERMISSIONS[guild_id]:
                user_perms[f"Role {role_id}"] = PERMISSIONS[guild_id][role_id]

    for role_id, managers in ROLE_MANAGERS.items():
        if user_id in managers:
            role_manager_roles.append(role_id)

    for role_id, admins in ROLE_ADMINS.items():
        if user_id in admins:
            role_admin_roles.append(role_id)

    if not user_perms and not role_manager_roles and not role_admin_roles:
        await interaction.response.send_message("Yo, you ain't got no special permissions. Step it up.", ephemeral=True)
        return

    response = "**Your Permissions**\n"
    if user_perms:
        response += "**General Permissions:**\n"
        for key, perms in user_perms.items():
            response += f"- **{key}:**\n"
            for command, subcommands in perms.items():
                subcommands_list = ", ".join(subcommands) if subcommands else "None"
                response += f"  - `{command}`: {subcommands_list}\n"

    if role_manager_roles:
        response += "\n**Role Manager For:**\n"
        for role_id in role_manager_roles:
            role = interaction.guild.get_role(role_id)
            response += f"- {role.mention if role else f'Role ID: {role_id}'}\n"

    if role_admin_roles:
        response += "\n**Role Admin For:**\n"
        for role_id in role_admin_roles:
            role = interaction.guild.get_role(role_id)
            response += f"- {role.mention if role else f'Role ID: {role_id}'}\n"

    await interaction.response.send_message(response, ephemeral=False)

bot.tree.add_command(role_group)

@bot.event
async def on_connect():
    if not hasattr(bot, "synced"):
        await bot.tree.sync()
        bot.synced = True

bot.run(TOKEN)
