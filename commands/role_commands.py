import discord
from discord import app_commands
from utils.permissions import has_permission, user_has_permission, add_permission, add_role_manager, add_role_admin, is_role_admin, can_manage_role, remove_role_manager, remove_role_admin
from utils.autocomplete import role_autocomplete
from config import ALLOWED_ROLE_NAMES, ALLOWED_USER_IDS, save_permissions
from utils.logger import Logger

logger = Logger()

role_group = app_commands.Group(name="role", description="Role management commands")

@role_group.command(name="create")
@app_commands.describe(
    rolename="Role name",
    color="Hex color, e.g., #FF0000",
    placeunder="Place new role under this role"
)
@app_commands.autocomplete(placeunder=role_autocomplete)
async def create(interaction: discord.Interaction, rolename: str, color: str, placeunder: str):
    print(f"Executing 'role create' command by user {interaction.user.id} with rolename={rolename}, color={color}, placeunder={placeunder}")
    
    if not has_permission(interaction, "role", "create"):
        await interaction.response.send_message("You don't have permission to create roles.", ephemeral=True)
        return

    await logger.log(
        interaction.client,
        interaction,
        Action="Create",
        RoleName=rolename,
        Color=color,
        PlaceUnder=placeunder
    )

    guild = interaction.guild
    bot_member = guild.me

    under_role = discord.utils.get(guild.roles, name=placeunder)
    if not under_role:
        await interaction.response.send_message(f"Role '{placeunder}' not found.", ephemeral=True)
        return

    try:
        role_color = discord.Color(int(color.strip("#"), 16))
    except ValueError:
        await interaction.response.send_message("Invalid color format. Use #RRGGBB.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        new_role = await guild.create_role(
            name=rolename,
            color=role_color,
            reason=f"Created by {interaction.user}"
        )

        try:
            roles = sorted(guild.roles, key=lambda r: r.position, reverse=True)
            target_position = under_role.position - 1

            new_roles = []
            inserted = False
            for role in roles:
                if not inserted and role.position <= target_position:
                    new_roles.append(new_role)
                    inserted = True
                if role != new_role:
                    new_roles.append(role)
            if not inserted:
                new_roles.append(new_role)

            new_positions = {
                role: len(new_roles) - index - 1
                for index, role in enumerate(new_roles)
            }

            await guild.edit_role_positions(positions=new_positions)

            await interaction.followup.send(
                f"✅ Role '{rolename}' created successfully under '{placeunder}'.",
                ephemeral=True
            )

        except discord.Forbidden:
            await new_role.delete()
            await interaction.followup.send(
                "I don't have permission to move roles.", ephemeral=True
            )
        except discord.HTTPException as e:
            await new_role.delete()
            await interaction.followup.send(
                f"Failed to position role: {str(e)}",
                ephemeral=True
            )

    except Exception as e:
        await interaction.followup.send(
            f"An unexpected error occurred: {str(e)}",
            ephemeral=True
        )

@role_group.command(name="delete")
@app_commands.describe(rolenames="Comma-separated list of roles to delete")
async def delete(interaction: discord.Interaction, rolenames: str):
    print(f"Executing 'role delete' command by user {interaction.user.id} with rolenames={rolenames}")
    role_names = [r.strip() for r in rolenames.split(",")]
    deleted = []
    failed = []

    for name in role_names:
        role = None
        if name.startswith("<@&") and name.endswith(">"):
            try:
                role_id = int(name[3:-1])
                role = interaction.guild.get_role(role_id)
            except ValueError:
                pass
        if role is None:
            try:
                role = interaction.guild.get_role(int(name))
            except ValueError:
                pass
        if role is None:
            role = discord.utils.get(interaction.guild.roles, name=name)

        if not role:
            failed.append(f"❌ '{name}' (not found)")
            continue

        if not can_manage_role(interaction, role.id):
            failed.append(f"⚠️ '{name}' (no permission)")
            continue

        try:
            await logger.log(
                interaction.client,
                interaction,
                Action="Delete",
                RoleName=role.name,
                RoleID=role.id
            )
            await role.delete(reason=f"Deleted by {interaction.user}")
            deleted.append(f"✅ {role.name}")
        except Exception as e:
            failed.append(f"❌ '{role.name}' ({e})")

    response = "Deleted roles:\n" + "\n".join(deleted + failed)
    await interaction.response.send_message(response, ephemeral=True)

@role_group.command(name="edit")
@app_commands.describe(
    rolename="Existing role name",
    newname="New name (optional)",
    newcolor="New hex color (optional)",
    rolemanager="User or Role mention or ID to manage this role (optional)",
    roleadmin="User or Role mention or ID to grant admin permissions for this role (optional)"
)
@app_commands.autocomplete(rolename=role_autocomplete)
async def edit(interaction: discord.Interaction, rolename: str, newname: str = None, newcolor: str = None, rolemanager: str = None, roleadmin: str = None):
    print(f"Executing 'role edit' command by user {interaction.user.id} with rolename={rolename}, newname={newname}, newcolor={newcolor}, rolemanager={rolemanager}, roleadmin={roleadmin}")
    role = discord.utils.get(interaction.guild.roles, name=rolename)
    if not role:
        await interaction.response.send_message("Role not found.", ephemeral=True)
        return

    if not can_manage_role(interaction, role.id):
        await interaction.response.send_message("You don't have permission to edit this role.", ephemeral=True)
        return

    kwargs = {}
    if newname:
        kwargs["name"] = newname
    if newcolor:
        try:
            kwargs["color"] = discord.Color(int(newcolor.strip("#"), 16))
        except ValueError:
            await interaction.response.send_message("Invalid color format. Use #RRGGBB.", ephemeral=True)
            return

    if rolemanager:
        try:
            if rolemanager.startswith("<@&") and rolemanager.endswith(">"):
                manager_id = int(rolemanager[3:-1])
            elif rolemanager.startswith("<@") and rolemanager.endswith(">"):
                manager_id = int(rolemanager[2:-1])
            else:
                manager_id = int(rolemanager)
        except ValueError:
            await interaction.response.send_message("Invalid manager format. Use a mention or ID.", ephemeral=True)
            return

        add_role_manager(role.id, manager_id)

    if roleadmin:
        try:
            if roleadmin.startswith("<@&") and roleadmin.endswith(">"):
                admin_id = int(roleadmin[3:-1])
            elif roleadmin.startswith("<@") and roleadmin.endswith(">"):
                admin_id = int(roleadmin[2:-1])
            else:
                admin_id = int(roleadmin)
        except ValueError:
            await interaction.response.send_message("Invalid admin format. Use a mention or ID.", ephemeral=True)
            return

        add_role_admin(role.id, admin_id)

    if not kwargs and not rolemanager and not roleadmin:
        await interaction.response.send_message("No updates provided.", ephemeral=True)
        return

    try:
        await role.edit(**kwargs, reason=f"Edited by {interaction.user}")
        await interaction.response.send_message(f"Role '{rolename}' updated.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to update role: {e}", ephemeral=True)

@role_group.command(name="assign")
@app_commands.describe(
    user="User to assign roles to",
    roles="Comma-separated list of role names"
)
async def assign(interaction: discord.Interaction, user: discord.Member, roles: str):
    print(f"Executing 'role assign' command by user {interaction.user.id} with user={user.id}, roles={roles}")
    role_names = [r.strip() for r in roles.split(",")]
    added = []
    failed = []

    for name in role_names:
        role = None
        if name.startswith("<@&") and name.endswith(">"):
            try:
                role_id = int(name[3:-1])
                role = interaction.guild.get_role(role_id)
            except ValueError:
                pass
        if role is None:
            try:
                role = interaction.guild.get_role(int(name))
            except ValueError:
                role = discord.utils.get(interaction.guild.roles, name=name)

        if not role:
            failed.append(f"❌ '{name}' (not found)")
            continue

        if not can_manage_role(interaction, role.id, action="assign"):
            failed.append(f"⚠️ '{name}' (no permission)")
            continue

        try:
            await logger.log(
                interaction.client,
                interaction,
                Action="Assign",
                TargetName=user.name,
                TargetID=user.id,
                RoleName=f"<@&{role.id}>",
                RoleID=role.id
            )
            await user.add_roles(role, reason=f"Assigned by {interaction.user}")
            added.append(f"✅ {role.name}")
        except Exception as e:
            failed.append(f"❌ '{role.name}' ({e})")

    response = f"Added roles to {user.mention}:\n" + "\n".join(added + failed)
    await interaction.response.send_message(response, ephemeral=True)

@role_group.command(name="unassign")
@app_commands.describe(
    user="User to remove roles from",
    roles="Comma-separated list of role names"
)
async def unassign(interaction: discord.Interaction, user: discord.Member, roles: str):
    print(f"Executing 'role unassign' command by user {interaction.user.id} with user={user.id}, roles={roles}")
    role_names = [r.strip() for r in roles.split(",")]
    removed = []
    failed = []

    for name in role_names:
        role = None
        if name.startswith("<@&") and name.endswith(">"):
            try:
                role_id = int(name[3:-1])
                role = interaction.guild.get_role(role_id)
            except ValueError:
                pass
        if role is None:
            try:
                role = interaction.guild.get_role(int(name))
            except ValueError:
                role = discord.utils.get(interaction.guild.roles, name=name)

        if not role:
            failed.append(f"❌ '{name}' (not found)")
            continue

        if not can_manage_role(interaction, role.id, action="unassign"):
            failed.append(f"⚠️ '{name}' (no permission)")
            continue

        try:
            await logger.log(
                interaction.client,
                interaction,
                Action="Unassign",
                TargetName=user.name,
                TargetID=user.id,
                RoleName=f"<@&{role.id}>",
                RoleID=role.id
            )
            await user.remove_roles(role, reason=f"Removed by {interaction.user}")
            removed.append(f"✅ {role.name}")
        except Exception as e:
            failed.append(f"❌ '{role.name}' ({e})")

    response = f"Removed roles from {user.mention}:\n" + "\n".join(removed + failed)
    await interaction.response.send_message(response, ephemeral=True)

@role_group.command(name="remove_manager")
@app_commands.describe(
    rolename="Role name or ID",
    user="User mention or ID to remove as manager"
)
@app_commands.autocomplete(rolename=role_autocomplete)
async def remove_manager(interaction: discord.Interaction, rolename: str, user: str):
    role = None
    if rolename.isdigit():
        role = interaction.guild.get_role(int(rolename))
    else:
        role = discord.utils.get(interaction.guild.roles, name=rolename)

    if not role:
        await interaction.response.send_message("Role not found.", ephemeral=True)
        return

    if not has_permission(interaction, "role", "edit"):
        await interaction.response.send_message("You don't have permission to modify role managers.", ephemeral=True)
        return

    try:
        if user.startswith("<@") and user.endswith(">"):
            user_id = int(user[2:-1])
        else:
            user_id = int(user)
    except ValueError:
        await interaction.response.send_message("Invalid user format. Use a mention or ID.", ephemeral=True)
        return

    remove_role_manager(role.id, user_id)
    await interaction.response.send_message(f"Removed {user} as manager for role '{role.name}'.", ephemeral=True)

@role_group.command(name="remove_admin")
@app_commands.describe(
    rolename="Role name or ID",
    user="User mention or ID to remove as admin"
)
@app_commands.autocomplete(rolename=role_autocomplete)
async def remove_admin(interaction: discord.Interaction, rolename: str, user: str):
    role = None
    if rolename.isdigit():
        role = interaction.guild.get_role(int(rolename))
    else:
        role = discord.utils.get(interaction.guild.roles, name=rolename)

    if not role:
        await interaction.response.send_message("Role not found.", ephemeral=True)
        return

    if not has_permission(interaction, "role", "edit"):
        await interaction.response.send_message("You don't have permission to modify role admins.", ephemeral=True)
        return

    try:
        if user.startswith("<@") and user.endswith(">"):
            user_id = int(user[2:-1])
        else:
            user_id = int(user)
    except ValueError:
        await interaction.response.send_message("Invalid user format. Use a mention or ID.", ephemeral=True)
        return

    remove_role_admin(role.id, user_id)
    await interaction.response.send_message(f"Removed {user} as admin for role '{role.name}'.", ephemeral=True)