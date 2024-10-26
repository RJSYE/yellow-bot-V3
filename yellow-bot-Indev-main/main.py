
import discord
from discord.ext import commands
import re
from datetime import timedelta
import sqlite3

# 명령어 파일에서 명령어 로드를 위해 import
import command as cmd_module
TOKEN = 'MTI0MTI4MzQwMjAyMDE1OTU3OQ.GJ4eJa.9UaKilhWquK-II2YcVT9r12ETO4jrjJVVLPlBM'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

jail_channel_id = 1244145964340609124

# 데이터베이스 초기화
def initialize_db():
    """bad_words 테이블을 초기화하고 cnt 칼럼을 추가"""
    conn = sqlite3.connect('filter_words.db')
    c = conn.cursor()
    
    # bad_words 테이블이 존재하는지 확인
    c.execute('''
        CREATE TABLE IF NOT EXISTS bad_words (
            word TEXT UNIQUE,
            cnt INTEGER DEFAULT 1
        )
    ''')
    conn.commit()

    # cnt 칼럼이 존재하는지 확인
    c.execute("PRAGMA table_info(bad_words)")
    columns = [column[1] for column in c.fetchall()]
    
    if 'cnt' not in columns:
        # cnt 칼럼 추가
        c.execute('ALTER TABLE bad_words ADD COLUMN cnt INTEGER DEFAULT 1')
        conn.commit()
    
    conn.close()


# 부적절한 키워드를 데이터베이스에서 가져옴
def get_bad_words():
    conn = sqlite3.connect('filter_words.db')
    c = conn.cursor()
    c.execute('SELECT word FROM bad_words')
    words = c.fetchall()
    conn.close()
    return [word[0] for word in words]

class PunishmentView(discord.ui.View):
    def __init__(self, user: discord.Member):
        super().__init__()
        self.user = user

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.guild_permissions.administrator

    @discord.ui.button(label='Ban', style=discord.ButtonStyle.danger)
    async def ban(self, interaction: discord.Interaction, _):
        await self.user.ban(reason="Inappropriate behavior")
        await interaction.response.send_message(f"{self.user.display_name} has been banned.")

    @discord.ui.button(label='Kick', style=discord.ButtonStyle.green)
    async def kick(self, interaction: discord.Interaction, _):
        await self.user.kick(reason="Inappropriate behavior")
        await interaction.response.send_message(f"{self.user.display_name} has been kicked.")

    @discord.ui.button(label='Mute', style=discord.ButtonStyle.primary)
    async def mute(self, interaction: discord.Interaction, _):
        mute_role = discord.utils.get(interaction.guild.roles, name="Mute")
        await self.user.add_roles(mute_role)
        await interaction.response.send_message(f"{self.user.display_name} has been muted.")

    @discord.ui.button(label='Decline', style=discord.ButtonStyle.secondary)
    async def decline(self, interaction: discord.Interaction, _):
        await self.user.edit(timed_out_until=None)  # Remove timeout
        await interaction.response.edit_message(content="Action canceled and timeout removed.", view=None)
        await interaction.followup.send(f"Penalty and timeout for {self.user.display_name} have been canceled.", ephemeral=True)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    print(f'Bot ID: {bot.user.id}')
    initialize_db()  # 데이터베이스 초기화

@bot.event
async def on_message(message):
    if message.author == bot.user or message.author.bot:
        return

    bad_words = get_bad_words()
    word_pattern = re.compile(r'\b(?:' + '|'.join(map(re.escape, bad_words)) + r')\b', re.IGNORECASE) if bad_words else None

    if word_pattern and word_pattern.search(message.content) and not message.author.guild_permissions.administrator:
        await message.delete()
        timeout_duration = timedelta(minutes=2)
        await message.author.edit(timed_out_until=discord.utils.utcnow() + timeout_duration)
        embed = discord.Embed(title="Inappropriate Message Detected", description=f"**User:** {message.author.display_name}\n**Message:** {message.content}", color=discord.Color.red())
        embed.set_thumbnail(url=message.author.display_avatar.url)
        view = PunishmentView(message.author)
        await bot.get_channel(jail_channel_id).send(embed=embed, view=view)
        print(f"Inappropriate message by {message.author.display_name} deleted and reported.")

    await bot.process_commands(message)

# Load commands from commands.py
cmd_module.setup(bot)
bot.run(TOKEN)
  