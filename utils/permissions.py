import discord
import json
from config import PERMISSIONS, ROLE_MANAGERS, ROLE_ADMINS, save_permissions  # Import save_permissions

def user_has_permission(interaction: discord.Interaction, allowed_roles, allowed_users) -> bool:
    member = interaction.user
    return (
        member.guild_permissions.administrator or
        any(role.name in allowed_roles for role in member.roles) or
        member.id in allowed_users
    )

def add_permission(guild_id, user_or_role_id, command, subcommand=None):
    guild_id = int(guild_id)  
    user_or_role_id = int(user_or_role_id)  

    if guild_id not in PERMISSIONS:
        PERMISSIONS[guild_id] = {}
    if user_or_role_id not in PERMISSIONS[guild_id]:
        PERMISSIONS[guild_id][user_or_role_id] = {}
    if command not in PERMISSIONS[guild_id][user_or_role_id]:
        PERMISSIONS[guild_id][user_or_role_id][command] = []
    if subcommand:
        if subcommand not in PERMISSIONS[guild_id][user_or_role_id][command]:
            PERMISSIONS[guild_id][user_or_role_id][command].append(subcommand)

    save_permissions()

    print(f"Updated PERMISSIONS after add_permission: {json.dumps(PERMISSIONS, indent=4)}")

def has_permission(interaction, command, subcommand=None):
    guild_id = interaction.guild.id
    user_id = interaction.user.id
    role_ids = [role.id for role in interaction.user.roles]

    command = command.lower()
    if subcommand and subcommand.startswith("<@&") and subcommand.endswith(">"):
        try:
            subcommand = str(int(subcommand[3:-1]))
        except ValueError:
            subcommand = None
    subcommand = subcommand.lower() if subcommand else None

    if guild_id in PERMISSIONS:
        if user_id in PERMISSIONS[guild_id] and "*" in PERMISSIONS[guild_id][user_id]:
            return True

        for role_id in role_ids:
            if role_id in PERMISSIONS[guild_id] and "*" in PERMISSIONS[guild_id][role_id]:
                return True

        if user_id in PERMISSIONS[guild_id]:
            user_permissions = PERMISSIONS[guild_id][user_id]
            if command in user_permissions:
                if not subcommand or subcommand in [sc.lower() for sc in user_permissions[command]]:
                    return True

        for role_id in role_ids:
            if role_id in PERMISSIONS[guild_id]:
                role_permissions = PERMISSIONS[guild_id][role_id]
                if command in role_permissions:
                    if not subcommand or subcommand in [sc.lower() for sc in role_permissions[command]]:
                        return True

    return False

def add_role_manager(role_id, manager_id):
    if role_id not in ROLE_MANAGERS:
        ROLE_MANAGERS[role_id] = []
    if manager_id not in ROLE_MANAGERS[role_id]:
        ROLE_MANAGERS[role_id].append(manager_id)

    save_permissions()

    print(f"Updated ROLE_MANAGERS: {json.dumps(ROLE_MANAGERS, indent=4)}")

def add_role_admin(role_id, admin_id):
    if role_id not in ROLE_ADMINS:
        ROLE_ADMINS[role_id] = []
    if admin_id not in ROLE_ADMINS[role_id]:
        ROLE_ADMINS[role_id].append(admin_id)

    save_permissions()

    print(f"Updated ROLE_ADMINS: {json.dumps(ROLE_ADMINS, indent=4)}")

def remove_role_manager(role_id, manager_id):
    if role_id in ROLE_MANAGERS and manager_id in ROLE_MANAGERS[role_id]:
        ROLE_MANAGERS[role_id].remove(manager_id)
        if not ROLE_MANAGERS[role_id]:
            del ROLE_MANAGERS[role_id]
        save_permissions()

def remove_role_admin(role_id, admin_id):
    if role_id in ROLE_ADMINS and admin_id in ROLE_ADMINS[role_id]:
        ROLE_ADMINS[role_id].remove(admin_id)
        if not ROLE_ADMINS[role_id]:
            del ROLE_ADMINS[role_id]
        save_permissions()

def is_role_manager(role_id, user_id):
    return role_id in ROLE_MANAGERS and user_id in ROLE_MANAGERS[role_id]

def is_role_admin(role_id, user_id):
    """
    Check if a user is a RoleAdmin for a specific role.
    """
    return role_id in ROLE_ADMINS and user_id in ROLE_ADMINS[role_id]

def can_manage_role(interaction: discord.Interaction, role_id: int, action: str = None) -> bool:
    """
    Check if the user has the necessary permissions to manage a specific role.
    This includes RoleManager (restricted to their role), RoleAdmin, or explicit permissions.
    """
    user_id = interaction.user.id

    if is_role_admin(role_id, user_id):
        return True

    if role_id in ROLE_MANAGERS and user_id in ROLE_MANAGERS[role_id]:
        if action in ["assign", "unassign"]:
            return True
        return False

    if has_permission(interaction, "role", str(role_id)):
        return True

    return False
