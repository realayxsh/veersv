import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
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

# ─── PERMISSION HELPER ────────────────────────────────────────────────────────
def has_bot_permission(member: discord.Member, data: dict) -> bool:
    """Returns True if user is an owner or has the perm role."""
    if member.id in data.get("owners", list(OWNERS)):
        return True
    return any(r.id == PERM_ROLE_ID for r in member.roles)

def is_owner(member: discord.Member, data: dict) -> bool:
    return member.id in data.get("owners", list(OWNERS))

# ─── TRANSPARENT EMBED BUILDER ───────────────────────────────────────────────
def make_embed(description: str = None, title: str = None, color: int = 0x2b2d31) -> discord.Embed:
    """Creates a transparent-style embed (color matches Discord dark background)."""
    embed = discord.Embed(color=color)
    if title:
        embed.title = title
    if description:
        embed.description = description
    return embed

def err_embed(description: str) -> discord.Embed:
    return make_embed(description, color=0xff4444)

def ok_embed(description: str) -> discord.Embed:
    return make_embed(description, color=0x2b2d31)

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

    # Step 1 — Clear any old guild-specific slash commands from every guild
    # (old bots often register per-guild commands that persist even after bot changes)
    for guild in bot.guilds:
        try:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
        except Exception as e:
            print(f"⚠️  Could not clear guild commands for {guild.name}: {e}")
    print(f"🗑️  Cleared old guild-specific slash commands in {len(bot.guilds)} guild(s)")

    # Step 2 — Sync all new global slash commands to Discord.
    # discord.py's sync() pushes the current local tree (all our @bot.tree.command decorators)
    # globally and automatically removes any old commands that are no longer defined.
    try:
        synced = await bot.tree.sync()
        print(f"✅ Synced {len(synced)} slash commands: {[c.name for c in synced]}")
    except Exception as e:
        print(f"❌ Slash sync error: {e}")

    keep_in_vc.start()

# ─── KEEP BOT IN VOICE CHANNEL ───────────────────────────────────────────────
@tasks.loop(seconds=30)
async def keep_in_vc():
    """Ensures the bot stays in the configured voice channel."""
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

    # If they were AFK, remove AFK status when they type
    if uid in data["afk"]:
        reason, since = data["afk"][uid]["reason"], data["afk"][uid]["since"]
        del data["afk"][uid]
        save_data(data)
        try:
            embed = ok_embed(f"✅ Welcome back, {message.author.mention}! You were AFK: **{reason}**")
            await message.channel.send(embed=embed, delete_after=8)
        except Exception:
            pass

    # If someone mentions an AFK user, notify
    if message.mentions:
        notified = []
        for mentioned in message.mentions:
            mid = str(mentioned.id)
            if mid in data["afk"] and mentioned.id not in notified:
                notified.append(mentioned.id)
                info = data["afk"][mid]
                embed = ok_embed(
                    f"💤 **{mentioned.display_name}** is AFK\n"
                    f"Reason: **{info['reason']}**\n"
                    f"Since: <t:{info['since']}:R>"
                )
                try:
                    await message.channel.send(embed=embed, delete_after=10)
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
    if not has_bot_permission(ctx.author, data):
        return await ctx.send(embed=err_embed("❌ You don't have permission to use this command."), delete_after=5)

    embed = make_embed()
    embed.title = "Bot Commands"
    embed.add_field(name="Permission Commands", value=(
        "`-perms give @user` — Give a user bot permissions\n"
        "`-perms remove @user` — Remove a user's bot permissions\n"
        "`-perms list` — List users with bot permissions"
    ), inline=False)
    embed.add_field(name="Embed Command", value=(
        "`-embed #channel message` — Send a transparent embed to a channel"
    ), inline=False)
    embed.add_field(name="Owner Commands", value=(
        "`-addowner @user` — Add a new bot owner\n"
        "`-removeowner @user` — Remove a bot owner\n"
        "`-owners` — List all bot owners"
    ), inline=False)
    embed.add_field(name="For Everyone", value=(
        "`-afk reason` — Set yourself as AFK"
    ), inline=False)
    embed.set_footer(text=BOT_STATUS)
    await ctx.send(embed=embed)

# ─── AFK (EVERYONE) ───────────────────────────────────────────────────────────
@bot.command(name="afk")
async def afk_cmd(ctx: commands.Context, *, reason: str = "No reason provided"):
    data = load_data()
    uid = str(ctx.author.id)
    data["afk"][uid] = {
        "reason": reason,
        "since": int(datetime.now(timezone.utc).timestamp())
    }
    save_data(data)
    embed = ok_embed(f"💤 **{ctx.author.display_name}** is now AFK\nReason: **{reason}**")
    await ctx.send(embed=embed)

@bot.tree.command(name="afk", description="Set yourself as AFK")
async def afk_slash(interaction: discord.Interaction, reason: str = "No reason provided"):
    data = load_data()
    uid = str(interaction.user.id)
    data["afk"][uid] = {
        "reason": reason,
        "since": int(datetime.now(timezone.utc).timestamp())
    }
    save_data(data)
    embed = ok_embed(f"💤 **{interaction.user.display_name}** is now AFK\nReason: **{reason}**")
    await interaction.response.send_message(embed=embed)

# ─── PERMS ────────────────────────────────────────────────────────────────────
@bot.command(name="perms")
async def perms_cmd(ctx: commands.Context, action: str = None, member: discord.Member = None):
    data = load_data()
    if not is_owner(ctx.author, data):
        return await ctx.send(embed=err_embed("❌ Only bot owners can manage permissions."), delete_after=5)

    if action is None:
        return await ctx.send(embed=err_embed("Usage: `-perms give @user` | `-perms remove @user` | `-perms list`"), delete_after=8)

    action = action.lower()

    if action == "list":
        perm_ids = data.get("perms", [])
        if not perm_ids:
            return await ctx.send(embed=ok_embed("No users have been given bot permissions yet."))
        lines = []
        for uid in perm_ids:
            user = bot.get_user(uid)
            lines.append(f"• <@{uid}> (`{uid}`)" + (f" — {user.name}" if user else ""))
        return await ctx.send(embed=ok_embed("**Users with bot permissions:**\n" + "\n".join(lines)))

    if member is None:
        return await ctx.send(embed=err_embed("Please mention a user. Example: `-perms give @user`"), delete_after=8)

    if action == "give":
        # Give user the perm role
        role = ctx.guild.get_role(PERM_ROLE_ID)
        if role is None:
            return await ctx.send(embed=err_embed(f"❌ Permission role not found (ID: `{PERM_ROLE_ID}`).\nMake sure the role exists in this server."), delete_after=10)
        try:
            await member.add_roles(role, reason=f"Bot permission granted by {ctx.author}")
        except discord.Forbidden:
            return await ctx.send(embed=err_embed("❌ I don't have permission to assign that role."), delete_after=8)
        if member.id not in data.get("perms", []):
            data.setdefault("perms", []).append(member.id)
            save_data(data)
        embed = ok_embed(f"✅ **{member.display_name}** has been given bot permissions.")
        await ctx.send(embed=embed)

    elif action == "remove":
        role = ctx.guild.get_role(PERM_ROLE_ID)
        if role:
            try:
                await member.remove_roles(role, reason=f"Bot permission removed by {ctx.author}")
            except discord.Forbidden:
                return await ctx.send(embed=err_embed("❌ I don't have permission to remove that role."), delete_after=8)
        perms = data.get("perms", [])
        if member.id in perms:
            perms.remove(member.id)
            data["perms"] = perms
            save_data(data)
        embed = ok_embed(f"✅ **{member.display_name}**'s bot permissions have been removed.")
        await ctx.send(embed=embed)

    else:
        await ctx.send(embed=err_embed("Unknown action. Use: `give`, `remove`, or `list`"), delete_after=8)

@bot.tree.command(name="perms", description="Manage bot permissions (owners only)")
@discord.app_commands.describe(
    action="give / remove / list",
    member="The user to give/remove permissions from"
)
async def perms_slash(interaction: discord.Interaction, action: str, member: discord.Member = None):
    data = load_data()
    if not is_owner(interaction.user, data):
        return await interaction.response.send_message(embed=err_embed("❌ Only bot owners can manage permissions."), ephemeral=True)

    action = action.lower()

    if action == "list":
        perm_ids = data.get("perms", [])
        if not perm_ids:
            return await interaction.response.send_message(embed=ok_embed("No users have been given bot permissions yet."), ephemeral=True)
        lines = [f"• <@{uid}>" for uid in perm_ids]
        return await interaction.response.send_message(embed=ok_embed("**Users with bot permissions:**\n" + "\n".join(lines)), ephemeral=True)

    if member is None:
        return await interaction.response.send_message(embed=err_embed("Please provide a user for give/remove."), ephemeral=True)

    if action == "give":
        role = interaction.guild.get_role(PERM_ROLE_ID)
        if role is None:
            return await interaction.response.send_message(embed=err_embed(f"❌ Permission role not found (ID: `{PERM_ROLE_ID}`)."), ephemeral=True)
        try:
            await member.add_roles(role, reason=f"Bot permission granted by {interaction.user}")
        except discord.Forbidden:
            return await interaction.response.send_message(embed=err_embed("❌ Missing permission to assign role."), ephemeral=True)
        if member.id not in data.get("perms", []):
            data.setdefault("perms", []).append(member.id)
            save_data(data)
        await interaction.response.send_message(embed=ok_embed(f"✅ **{member.display_name}** has been given bot permissions."))

    elif action == "remove":
        role = interaction.guild.get_role(PERM_ROLE_ID)
        if role:
            try:
                await member.remove_roles(role, reason=f"Bot permission removed by {interaction.user}")
            except discord.Forbidden:
                return await interaction.response.send_message(embed=err_embed("❌ Missing permission to remove role."), ephemeral=True)
        perms = data.get("perms", [])
        if member.id in perms:
            perms.remove(member.id)
            data["perms"] = perms
            save_data(data)
        await interaction.response.send_message(embed=ok_embed(f"✅ **{member.display_name}**'s bot permissions have been removed."))
    else:
        await interaction.response.send_message(embed=err_embed("Unknown action. Use: `give`, `remove`, or `list`"), ephemeral=True)

# ─── EMBED ────────────────────────────────────────────────────────────────────
@bot.command(name="embed")
async def embed_cmd(ctx: commands.Context, channel: discord.TextChannel = None, *, message: str = None):
    data = load_data()
    if not has_bot_permission(ctx.author, data):
        return await ctx.send(embed=err_embed("❌ You don't have permission to use this command."), delete_after=5)
    if channel is None or message is None:
        return await ctx.send(embed=err_embed("Usage: `-embed #channel your message here`"), delete_after=8)
    embed = make_embed(message)
    try:
        await channel.send(embed=embed)
        await ctx.send(embed=ok_embed(f"✅ Embed sent to {channel.mention}."), delete_after=5)
    except discord.Forbidden:
        await ctx.send(embed=err_embed(f"❌ I don't have permission to send messages in {channel.mention}."), delete_after=8)

@bot.tree.command(name="embed", description="Send a transparent embed to a channel")
@discord.app_commands.describe(
    channel="Channel to send the embed to",
    message="The message content of the embed"
)
async def embed_slash(interaction: discord.Interaction, channel: discord.TextChannel, message: str):
    data = load_data()
    if not has_bot_permission(interaction.user, data):
        return await interaction.response.send_message(embed=err_embed("❌ You don't have permission to use this command."), ephemeral=True)
    embed = make_embed(message)
    try:
        await channel.send(embed=embed)
        await interaction.response.send_message(embed=ok_embed(f"✅ Embed sent to {channel.mention}."), ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(embed=err_embed(f"❌ Missing permission to send in {channel.mention}."), ephemeral=True)

# ─── OWNER MANAGEMENT ─────────────────────────────────────────────────────────
@bot.command(name="addowner")
async def addowner_cmd(ctx: commands.Context, member: discord.Member = None):
    data = load_data()
    if not is_owner(ctx.author, data):
        return await ctx.send(embed=err_embed("❌ Only bot owners can add new owners."), delete_after=5)
    if member is None:
        return await ctx.send(embed=err_embed("Usage: `-addowner @user`"), delete_after=8)
    owners = data.get("owners", list(OWNERS))
    if member.id in owners:
        return await ctx.send(embed=ok_embed(f"**{member.display_name}** is already a bot owner."))
    owners.append(member.id)
    data["owners"] = owners
    save_data(data)
    await ctx.send(embed=ok_embed(f"✅ **{member.display_name}** has been added as a bot owner."))

@bot.command(name="removeowner")
async def removeowner_cmd(ctx: commands.Context, member: discord.Member = None):
    data = load_data()
    if not is_owner(ctx.author, data):
        return await ctx.send(embed=err_embed("❌ Only bot owners can remove owners."), delete_after=5)
    if member is None:
        return await ctx.send(embed=err_embed("Usage: `-removeowner @user`"), delete_after=8)
    owners = data.get("owners", list(OWNERS))
    if member.id not in owners:
        return await ctx.send(embed=ok_embed(f"**{member.display_name}** is not a bot owner."))
    if len(owners) <= 1:
        return await ctx.send(embed=err_embed("❌ Cannot remove the last owner."), delete_after=8)
    owners.remove(member.id)
    data["owners"] = owners
    save_data(data)
    await ctx.send(embed=ok_embed(f"✅ **{member.display_name}** has been removed as a bot owner."))

@bot.command(name="owners")
async def owners_cmd(ctx: commands.Context):
    data = load_data()
    if not has_bot_permission(ctx.author, data):
        return await ctx.send(embed=err_embed("❌ You don't have permission to use this command."), delete_after=5)
    owners = data.get("owners", list(OWNERS))
    lines = [f"• <@{uid}> (`{uid}`)" for uid in owners]
    await ctx.send(embed=ok_embed("**Bot Owners:**\n" + "\n".join(lines)))

@bot.tree.command(name="addowner", description="Add a new bot owner (owners only)")
@discord.app_commands.describe(member="User to make a bot owner")
async def addowner_slash(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    if not is_owner(interaction.user, data):
        return await interaction.response.send_message(embed=err_embed("❌ Only bot owners can add new owners."), ephemeral=True)
    owners = data.get("owners", list(OWNERS))
    if member.id in owners:
        return await interaction.response.send_message(embed=ok_embed(f"**{member.display_name}** is already a bot owner."), ephemeral=True)
    owners.append(member.id)
    data["owners"] = owners
    save_data(data)
    await interaction.response.send_message(embed=ok_embed(f"✅ **{member.display_name}** has been added as a bot owner."))

@bot.tree.command(name="removeowner", description="Remove a bot owner (owners only)")
@discord.app_commands.describe(member="Owner to remove")
async def removeowner_slash(interaction: discord.Interaction, member: discord.Member):
    data = load_data()
    if not is_owner(interaction.user, data):
        return await interaction.response.send_message(embed=err_embed("❌ Only bot owners can remove owners."), ephemeral=True)
    owners = data.get("owners", list(OWNERS))
    if member.id not in owners:
        return await interaction.response.send_message(embed=ok_embed(f"**{member.display_name}** is not a bot owner."), ephemeral=True)
    if len(owners) <= 1:
        return await interaction.response.send_message(embed=err_embed("❌ Cannot remove the last owner."), ephemeral=True)
    owners.remove(member.id)
    data["owners"] = owners
    save_data(data)
    await interaction.response.send_message(embed=ok_embed(f"✅ **{member.display_name}** has been removed as a bot owner."))

@bot.tree.command(name="owners", description="List all bot owners")
async def owners_slash(interaction: discord.Interaction):
    data = load_data()
    if not has_bot_permission(interaction.user, data):
        return await interaction.response.send_message(embed=err_embed("❌ You don't have permission to use this command."), ephemeral=True)
    owners = data.get("owners", list(OWNERS))
    lines = [f"• <@{uid}> (`{uid}`)" for uid in owners]
    await interaction.response.send_message(embed=ok_embed("**Bot Owners:**\n" + "\n".join(lines)), ephemeral=True)

@bot.tree.command(name="help", description="Show all bot commands")
async def help_slash(interaction: discord.Interaction):
    data = load_data()
    if not has_bot_permission(interaction.user, data):
        return await interaction.response.send_message(embed=err_embed("❌ You don't have permission to use this command."), ephemeral=True)

    embed = make_embed()
    embed.title = "Bot Commands"
    embed.add_field(name="Permission Commands", value=(
        "`/perms give @user` — Give a user bot permissions\n"
        "`/perms remove @user` — Remove a user's bot permissions\n"
        "`/perms list` — List users with bot permissions"
    ), inline=False)
    embed.add_field(name="Embed Command", value=(
        "`/embed #channel message` — Send a transparent embed to a channel"
    ), inline=False)
    embed.add_field(name="Owner Commands", value=(
        "`/addowner @user` — Add a new bot owner\n"
        "`/removeowner @user` — Remove a bot owner\n"
        "`/owners` — List all bot owners"
    ), inline=False)
    embed.add_field(name="For Everyone", value=(
        "`/afk reason` — Set yourself as AFK"
    ), inline=False)
    embed.set_footer(text=BOT_STATUS)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# ─── ERROR HANDLER ────────────────────────────────────────────────────────────
@bot.event
async def on_command_error(ctx: commands.Context, error):
    if isinstance(error, commands.CommandNotFound):
        return
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(embed=err_embed(f"❌ Missing argument: `{error.param.name}`"), delete_after=8)
    elif isinstance(error, commands.MemberNotFound):
        await ctx.send(embed=err_embed("❌ User not found. Please mention a valid server member."), delete_after=8)
    elif isinstance(error, commands.BadArgument):
        await ctx.send(embed=err_embed("❌ Invalid argument. Please check your command usage."), delete_after=8)
    else:
        print(f"[ERROR] {type(error).__name__}: {error}")

# ─── RUN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_TOKEN environment variable is not set!")
    bot.run(token)
