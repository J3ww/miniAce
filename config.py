import os
import json
from dotenv import load_dotenv
import pathlib

# Debug .env loading with more verbose output
current_dir = pathlib.Path(__file__).parent.absolute()
env_path = current_dir / '.env'
print(f"[DEBUG] Looking for .env at: {env_path}")
print(f"[DEBUG] .env exists: {env_path.exists()}")

# Force reload environment
if env_path.exists():
    with open(env_path, 'r') as f:
        env_content = f.read().strip()
        os.environ['DISCORD_TOKEN'] = env_content.split('=', 1)[1].strip()
        print("[DEBUG] Directly loaded token from .env file")

# Get token with fallback
TOKEN = os.environ.get('DISCORD_TOKEN')
if not TOKEN:
    raise ValueError("[ERROR] Could not load DISCORD_TOKEN")

print(f"[DEBUG] Full Token: {TOKEN}")
print(f"[DEBUG] Token length: {len(TOKEN)}")
print(f"[DEBUG] Token first/last 5 chars: {TOKEN[:5]}...{TOKEN[-5:]}")

ALLOWED_ROLE_NAMES = ["Admin", "Mod"]
ALLOWED_USER_IDS = []

PERMISSIONS_FILE = "permissions.json"
PERMISSIONS = {}
ROLE_MANAGERS = {}
ROLE_ADMINS = {}


if os.path.exists(PERMISSIONS_FILE):
    with open(PERMISSIONS_FILE, "r") as f:
        loaded_permissions = json.load(f)
        PERMISSIONS = {
            int(guild_id): {
                int(user_or_role_id): commands
                for user_or_role_id, commands in users_or_roles.items()
            }
            for guild_id, users_or_roles in loaded_permissions.get("permissions", {}).items()
        }
        ROLE_MANAGERS = {
            int(role_id): [int(manager_id) for manager_id in managers]
            for role_id, managers in loaded_permissions.get("role_managers", {}).items()
        }
        ROLE_ADMINS = {
            int(role_id): [int(admin_id) for admin_id in admins]
            for role_id, admins in loaded_permissions.get("role_admins", {}).items()
        }

    print(f"Loaded PERMISSIONS: {json.dumps(PERMISSIONS, indent=4)}")
    print(f"Loaded ROLE_MANAGERS: {json.dumps(ROLE_MANAGERS, indent=4)}")
    print(f"Loaded ROLE_ADMINS: {json.dumps(ROLE_ADMINS, indent=4)}")

def save_permissions():
    cleaned_permissions = {
        "permissions": {
            str(guild_id): {
                str(user_or_role_id): {
                    command: subcommands
                    for command, subcommands in commands.items() if subcommands
                }
                for user_or_role_id, commands in users_or_roles.items() if commands
            }
            for guild_id, users_or_roles in PERMISSIONS.items() if users_or_roles
        },
        "role_managers": {
            str(role_id): [str(manager_id) for manager_id in managers]
            for role_id, managers in ROLE_MANAGERS.items() if managers
        },
        "role_admins": {
            str(role_id): [str(admin_id) for admin_id in admins]
            for role_id, admins in ROLE_ADMINS.items() if admins
        }
    }

    print(f"Saving cleaned PERMISSIONS: {json.dumps(cleaned_permissions, indent=4)}")

    with open(PERMISSIONS_FILE, "w") as f:
        json.dump(cleaned_permissions, f, indent=4)
