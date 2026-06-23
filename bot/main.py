import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime, timezone

# ─── CONFIG ───────────────────────────────────────────────────────────────────
PERM_ROLE_ID    = 1502876234705535088
OWNERS          = {282494845753491456, 145759040956399616}
STAY_VC_ID      = 1502876369468657674
DATA_FILE       = "data.json"
BOT_STATUS      = "discord.gg/dilbar"
PREFIX          = "-"

# ─── DATA HELPERS ─────────────────────────────────────────────────────────────
def load_data() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"afk": {}, "owners": list(OWNERS), "perms": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save_data(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ─── PERMISSION HELPERS ───────────────────────────────────────────────────────
def has_bot_permission(member: discord.Member, data: dict) -> bool:
    if member.id in data.get("owners", list(OWNERS)):
        return True
    return any(r.id == PERM_ROLE_ID for r in member.roles)

def is_owner(member: discord.Member, data: dict) -> bool:
    return member.id in data.get("owners", list(OWNERS))

# ─── COMPONENT V2 BUILDERS ────────────────────────────────────────────────────
# MessageFlags for Component V2 (requires discord.py >= 2.5)
V2          = discord.MessageFlags(is_components_v2=True)
V2_EPH      = discord.MessageFlags(is_components_v2=True, ephemeral=True)

def v2(text: str) -> list:
    """Fully transparent Component V2 container — no accent color strip."""
    return [discord.ui.Container(discord.ui.TextDisplay(text))]

def v2_title(title: str, text: str) -> list:
    """Transparent Component V2 with a bold title + separator + body."""
    return [
        discord.ui.Container(
            discord.ui.TextDisplay(f"## {title}"),
            discord.ui.Separator(),
            discord.ui.TextDisplay(text),
        )
    ]

def v2_err(text: str) -> list:
    """Component V2 with red accent strip for errors."""
    return [discord.ui.Container(discord.ui.TextDisplay(text), accent_color=discord.Color(0xff4444))]

# ─── INTENTS & BOT ────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(
    command_prefix=PREFIX,
    intents=intents,
    help_command=None,
)

# ─── STARTUP ──────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} ({bot.user.id})")
    await bot.change_presence(
        activity=discord.CustomActivity(name=BOT_STATUS),
        status=discord.Status.idle
    )

    # Clear old guild-specific slash commands
    for guild in bot.guilds:
        try:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
        except Exception as e:
            print(f"⚠️  Could not clear guild commands for {guild.name}: {e}")
    print(f"🗑️  Cleared old guild-specific slash commands in {len(bot.guilds)} guild(s)")

    # Sync new global slash commands (replaces all old ones on Discord's side)
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands: {[c.name for c in synced]}")
    except Exception as e:
        print(f"❌ Slash sync error: {e}")

    keep_in_vc.start()

# ─── KEEP BOT IN VOICE CHANNEL ───────────────────────────────────────────────
@tasks.loop(seconds=30)
async def keep_in_vc():
    vc_channel = bot.get_channel(STAY_VC_ID)
    if vc_channel is None:
        return
    guild = vc_channel.guild
    voice_client = guild.voice_client
    if voice_client is None or not voice_client.is_connected():
        try:
            await vc_channel.connect(self_deaf=True)
            print(f"🔊 Joined VC: {vc_channel.name}")
        except Exception as e:
            print(f"❌ VC join error: {e}")
    elif voice_client.channel.id != STAY_VC_ID:
        try:
            await voice_client.move_to(vc_channel)
        except Exception as e:
            print(f"❌ VC move error: {e}")

@keep_in_vc.before_loop
async def before_keep_in_vc():
    await bot.wait_until_ready()

# ─── AFK SYSTEM ───────────────────────────────────────────────────────────────
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    data = load_data()
    uid = str(message.author.id)

    # Clear AFK when they send a message
    if uid in data["afk"]:
        info = data["afk"].pop(uid)
        save_data(data)
        try:
            await message.channel.send(
                components=v2(f"✅ Welcome back, {message.author.mention}! You were AFK: **{info['reason']}**"),
                flags=V2,
                delete_after=8
            )
        except Exception:
            pass

    # Notify when mentioning an AFK user
    if message.mentions:
        notified = []
        for mentioned in message.mentions:
            mid = str(mentioned.id)
            if mid in data["afk"] and mentioned.id not in notified:
                notified.append(mentioned.id)
                info = data["afk"][mid]
                try:
                    await message.channel.send(
                        components=v2(
                            f"💤 **{mentioned.display_name}** is AFK\n"
                            f"Reason: **{info['reason']}**\n"
                            f"Since: <t:{info['since']}:R>"
                        ),
                        flags=V2,
                        delete_after=10
                    )
                except Exception:
                    pass

    await bot.process_commands(message)

# ═══════════════════════════════════════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

# ─── HELP ─────────────────────────────────────────────────────────────────────
@bot.command(name="help")
async def help_cmd(ctx: commands.Context):
    data = load_data()
    everyone_section = (
        "**For Everyone**\n"
        "`-afk [reason]` — Set yourself as AFK\n"
        "`-help` — Show this command list\n"
    )
    if has_bot_permission(ctx.author, data):
        body = (
            "**Permission Commands**\n"
            "`-perms give @user` — Give a user bot permissions\n"
            "`-perms remove @user` — Remove a user's bot permissions\n"
            "`-perms list` — List users with bot permissions\n\n"
            "**Embed Command**\n"
            "`-embed #channel message` — Send a transparent V2 message to a channel\n\n"
            "**Owner Commands**\n"
            "`-addowner @user` — Add a new bot owner\n"
            "`-removeowner @user` — Remove a bot owner\n"
            "`-owners` — List all bot owners\n\n"
            + everyone_section +
            f"\n-# {BOT_STATUS}"
        )
    else:
        body = everyone_section + f"\n-# {BOT_STATUS}"
    try:
        await ctx.send(components=v2_title("Bot Commands", body), flags=V2)
    except Exception as e:
        print(f"[V2 ERROR] help command: {e}")
        await ctx.send(body)

@bot.tree.command(name="help", description="Show all bot commands")
async def help_slash(interaction: discord.Interaction):
    data = load_data()
    everyone_section = (
        "**For Everyone**\n"
        "`/afk [reason]` — Set yourself as AFK\n"
        "`/help` — Show this command list\n"
    )
    if has_bot_permission(interaction.user, data):
        body = (
            "**Permission Commands**\n"
            "`/perms give @user` — Give a user bot permissions\n"
            "`/perms remove @user` — Remove a user's bot permissions\n"
            "`/perms list` — List users with bot permissions\n\n"
            "**Embed Command**\n"
            "`/embed #channel message` — Send a transparent V2 message to a channel\n\n"
            "**Owner Commands**\n"
            "`/addowner @user` — Add a new bot owner\n"
            "`/removeowner @user` — Remove a bot owner\n"
            "`/owners` — List all bot owners\n\n"
            + everyone_section +
            f"\n-# {BOT_STATUS}"
        )
    else:
        body = everyone_section + f"\n-# {BOT_STATUS}"
    await interaction.response.send_message(components=v2_title("Bot Commands", body), flags=V2_EPH)

# ─── AFK ──────────────────────────────────────────────────────────────────────
@bot.command(name="afk")
async def afk_cmd(ctx: commands.Context, *, reason: str = "No reason provided"):
    data = load_data()
    uid = str(ctx.author.id)
    data["afk"][uid] = {
        "reason": reason,
        "since": int(datetime.now(timezone.utc).timestamp())
    }
    save_data(data)
    await ctx.send(
        components=v2(f"💤 **{ctx.author.display_name}** is now AFK\nReason: **{reason}**"),
        flags=V2
    )

@bot.tree.command(name="afk", description="Set yourself as AFK")
@discord.app_commands.describe(reason="Your AFK reason")
@discord.app_commands.default_permissions(send_messages=True)
async def afk_slash(interaction: discord.Interaction, reason: str = "No reason provided"):
    data = load_data()
    uid = str(interaction.user.id)
    data["afk"][uid] = {
        "reason": reason,
        "since": int(datetime.now(timezone.utc).timestamp())
    }
    save_data(data)
    await interaction.response.send_message(
        components=v2(f"💤 **{interaction.user.display_name}** is now AFK\nReason: **{reason}**"),
        flags=V2
    )

# ─── PERMS ────────────────────────────────────────────────────────────────────
@bot.command(name="perms")
async def perms_cmd(ctx: commands.Context, action: str = None, member: discord.Member = None):
    data = load_data()
    if not is_owner(ctx.author, data):
        return await ctx.send(components=v2_err("❌ Only bot owners can manage permissions."), flags=V2, delete_after=5)

    if action is None:
        return await ctx.send(
            components=v2_err("Usage: `-perms give @user` | `-perms remove @user` | `-perms list`"),
            flags=V2, delete_after=8
        )

    action = action.lower()

    if action == "list":
        perm_ids = data.get("perms", [])
        if not perm_ids:
            return await ctx.send(components=v2("No users have been given bot permissions yet."), flags=V2)
        lines = [f"• <@{uid}>" for uid in perm_ids]
        return await ctx.send(
            components=v2("**Users with bot permissions:**\n" + "\n".join(lines)),
            flags=V2
        )

    if member is None:
        return await ctx.send(
            components=v2_err("Please mention a user. Example: `-perms give @user`"),
            flags=V2, delete_after=8
        )

    if action == "give":
        role = ctx.guild.get_role(PERM_ROLE_ID)
        if role is None:
            return await ctx.send(
                components=v2_err(f"❌ Permission role not found (ID: `{PERM_ROLE_ID}`).\nMake sure the role exists in this server."),
                flags=V2, delete_after=10
            )
        try:
            await member.add_roles(role, reason=f"Bot permission granted by {ctx.author}")
        except discord.Forbidden:
            return await ctx.send(components=v2_err("❌ I don't have permission to assign that role."), flags=V2, delete_after=8)
        if member.id not in data.get("perms", []):
            data.setdefault("perms", []).append(member.id)
            save_data(data)
        await ctx.send(components=v2(f"✅ **{member.display_name}** has been given bot permissions."), flags=V2)

    elif action == "remove":
        role = ctx.guild.get_role(PERM_ROLE_ID)
        if role:
            try:
                await member.remove_roles(role, reason=f"Bot permission removed by {ctx.author}")
            except discord.Forbidden:
                return await ctx.send(components=v2_err("❌ I don't have permission to remove that role."), flags=V2, delete_after=8)
        perms = data.get("perms", [])
        if member.id in perms:
            perms.remove(member.id)
            data["perms"] = perms
            save_data(data)
        await ctx.send(components=v2(f"✅ **{member.display_name}**'s bot permissions have been removed."), flags=V2)

    else:
        await ctx.send(components=v2_err("Unknown action. Use: `give`, `remove`, or `list`"), flags=V2, delete_after=8)

@bot.tree.command(name="perms", description="Manage bot permissions (owners only)")
@discord.app_commands.describe(action="give / remove / list", member="The user to give/remove permissions from")
@discord.app_commands.default_permissions(administrator=True)
async def perms_slash(interaction: discord.Interaction, action: str, member: discord.Member = None):
    data = load_data()
    if not is_owner(interaction.user, data):
        return await interaction.response.send_message(components=v2_err("❌ Only bot owners can manage permissions."), flags=V2_EPH)

    action = action.lower()

    if action == "list":
        perm_ids = data.get("perms", [])
        if not perm_ids:
            return await interaction.response.send_message(components=v2("No users have been given bot permissions yet."), flags=V2_EPH)
        lines = [f"• <@{uid}>" for uid in perm_ids]
        return await interaction.response.send_message(
            components=v2("**Users with bot permissions:**\n" + "\n".join(lines)),
            flags=V2_EPH
        )

    if member is None:
        return await interaction.response.send_message(components=v2_err("Please provide a user for give/remove."), flags=V2_EPH)

    if action == "give":
        role = interaction.guild.get_role(PERM_ROLE_ID)
        if role is None:
            return await interaction.response.send_message(
                components=v2_err(f"❌ Permission role not found (ID: `{PERM_ROLE_ID}`)."),
                flags=V2_EPH
            )
        try:
            await member.add_roles(role, reason=f"Bot permission granted by {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message(components=v2_err("❌ Missing permission to assign role."), flags=V2_EPH)
        if member.id not in data.get("perms", []):
            data.setdefault("perms", []).append(member.id)
            save_data(data)
        await interaction.response.send_message(components=v2(f"✅ **{member.display_name}** has been given bot permissions."), flags=V2)

    elif action == "remove":
        role = interaction.guild.get_role(PERM_ROLE_ID)
        if role:
            try:
                await member.remove_roles(role, reason=f"Bot permission removed by {interaction.user}")
            except discord.Forbidden:
                return await interaction.response.send_message(components=v2_err("❌ Missing permission to remove role."), flags=V2_EPH)
        perms = data.get("perms", [])
        if member.id in perms:
            perms.remove(member.id)
            data["perms"] = perms
            save_data(data)
        await interaction.response.send_message(components=v2(f"✅ **{member.display_name}**'s bot permissions have been removed."), flags=V2)
    else:
        await interaction.response.send_message(components=v2_err("Unknown action. Use: `give`, `remove`, or `list`"), flags=V2_EPH)

# ─── EMBED ────────────────────────────────────────────────────────────────────
@bot.command(name="embed")
async def embed_cmd(ctx: commands.Context, channel: discord.TextChannel = None, *, message: str = None):
    data = load_data()
    if not has_bot_permission(ctx.author, data):
        return await ctx.send(components=v2_err("❌ You don't have permission to use this command."), flags=V2, delete_after=5)
    if channel is None or message is None:
        return await ctx.send(components=v2_err("Usage: `-embed #channel your message here`"), flags=V2, delete_after=8)
    try:
        await channel.send(components=v2(message), flags=V2)
        await ctx.send(components=v2(f"✅ Sent to {channel.mention}."), flags=V2, delete_after=5)
    except discord.Forbidden:
        await ctx.send(components=v2_err(f"❌ I don't have permission to send in {channel.mention}."), flags=V2, delete_after=8)

@bot.tree.command(name="embed", description="Send a transparent Component V2 message to a channel")
@discord.app_commands.describe(channel="Channel to send to", message="The message content")
@discord.app_commands.default_permissions(manage_guild=True)
async def embed_slash(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    data = load_data()
    if not has_bot_permission(interaction.user, data):
        return await interaction.response.send_message(components=v2_err("❌ You don't have permission to use this command."), flags=V2_EPH)
    try:
        await channel.send(components=v2(message), flags=V2)
        await interaction.response.send_message(components=v2(f"✅ Sent to {channel.mention}."), flags=V2_EPH)
    except discord.Forbidden:
        await interaction.response.send_message(components=v2_err(f"❌ Missing permission to send in {channel.mention}."), flags=V2_EPH)

# ─── OWNER MANAGEMENT ─────────────────────────────────────────────────────────
@bot.command(name="addowner")
async def addowner_cmd(ctx: commands.Context, member: discord.Member = None):
    data = load_data()
    if not is_owner(ctx.author, data):
        return await ctx.send(components=v2_err("❌ Only bot owners can add new owners."), flags=V2, delete_after=5)
    if member is None:
        return await ctx.send(components=v2_err("Usage: `-addowner @user`"), flags=V2, delete_after=8)
    owners = data.get("owners", list(OWNERS))
    if member.id in owners:
        return await ctx.send(components=v2(f"**{member.display_name}** is already a bot owner."), flags=V2)
    owners.append(member.id)
    data["owners"] = owners
    save_data(data)
    await ctx.send(components=v2(f"✅ **{member.display_name}** has been added as a bot owner."), flags=V2)

@bot.command(name="removeowner")
async def removeowner_cmd(ctx: commands.Context, member: discord.Member = None):
    data = load_data()
    if not is_owner(ctx.author, data):
        return await ctx.send(components=v2_err("❌ Only bot owners can remove owners."), flags=V2, delete_after=5)
    if member is None:
        return await ctx.send(components=v2_err("Usage: `-removeowner @user`"), flags=V2, delete_after=8)
    owners = data.get("owners", list(OWNERS))
    if member.id not in owners:
        return await ctx.send(components=v2(f"**{member.display_name}** is not a bot owner."), flags=V2)
    if len(owners) <= 1:
        return await ctx.send(components=v2_err("❌ Cannot remove the last owner."), flags=V2, delete_after=8)
    owners.remove(member.id)
    data["owners"] = owners
    save_data(data)
    await ctx.send(components=v2(f"✅ **{member.display_name}** has been removed as a bot owner."), flags=V2)

@bot.command(name="owners")
async def owners_cmd(ctx: commands.Context):
    data = load_data()
    if not has_bot_permission(ctx.author, data):
        return await ctx.send(components=v2_err("❌ You don't have permission to use this command."), flags=V2, delete_after=5)
    owners = data.get("owners", list(OWNERS))
    lines = [f"• <@{uid}>" for uid in owners]
    await ctx.send(components=v2("**Bot Owners:**\n" + "\n".join(lines)), flags=V2)

@bot.tree.command(name="addowner", description="Add a new bot owner (owners only)")
@discord.app_commands.describe(member="User to make a bot owner")
@discord.app_commands.default_permissions(administrator=True)
async def addowner_slash(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    if not is_owner(interaction.user, data):
        return await interaction.response.send_message(components=v2_err("❌ Only bot owners can add new owners."), flags=V2_EPH)
    owners = data.get("owners", list(OWNERS))
    if member.id in owners:
        return await interaction.response.send_message(components=v2(f"**{member.display_name}** is already a bot owner."), flags=V2_EPH)
    owners.append(member.id)
    data["owners"] = owners
    save_data(data)
    await interaction.response.send_message(components=v2(f"✅ **{member.display_name}** has been added as a bot owner."), flags=V2)

@bot.tree.command(name="removeowner", description="Remove a bot owner (owners only)")
@discord.app_commands.describe(member="Owner to remove")
@discord.app_commands.default_permissions(administrator=True)
async def removeowner_slash(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    if not is_owner(interaction.user, data):
        return await interaction.response.send_message(components=v2_err("❌ Only bot owners can remove owners."), flags=V2_EPH)
    owners = data.get("owners", list(OWNERS))
    if member.id not in owners:
        return await interaction.response.send_message(components=v2(f"**{member.display_name}** is not a bot owner."), flags=V2_EPH)
    if len(owners) <= 1:
        return await interaction.response.send_message(components=v2_err("❌ Cannot remove the last owner."), flags=V2_EPH)
    owners.remove(member.id)
    data["owners"] = owners
    save_data(data)
    await interaction.response.send_message(components=v2(f"✅ **{member.display_name}** has been removed as a bot owner."), flags=V2)

@bot.tree.command(name="owners", description="List all bot owners")
@discord.app_commands.default_permissions(manage_guild=True)
async def owners_slash(interaction: discord.Interaction):
    data = load_data()
    if not has_bot_permission(interaction.user, data):
        return await interaction.response.send_message(components=v2_err("❌ You don't have permission to use this command."), flags=V2_EPH)
    owners = data.get("owners", list(OWNERS))
    lines = [f"• <@{uid}>" for uid in owners]
    await interaction.response.send_message(components=v2("**Bot Owners:**\n" + "\n".join(lines)), flags=V2_EPH)

# ─── ERROR HANDLER ────────────────────────────────────────────────────────────
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return
    print(f"[CMD ERROR] {ctx.command} — {type(error).__name__}: {error}")
    msg = None
    if isinstance(error, commands.MissingRequiredArgument):
        msg = f"❌ Missing argument: `{error.param.name}`"
    elif isinstance(error, commands.MemberNotFound):
        msg = "❌ User not found. Please mention a valid server member."
    elif isinstance(error, commands.BadArgument):
        msg = "❌ Invalid argument. Please check your command usage."
    else:
        msg = f"❌ An error occurred: `{type(error).__name__}: {error}`"
    try:
        await ctx.send(components=v2_err(msg), flags=V2, delete_after=10)
    except Exception as e:
        print(f"[SEND ERROR] Could not send error message: {e}")
        try:
            await ctx.send(msg, delete_after=10)
        except Exception:
            pass

# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set!")
    bot.run(token)
