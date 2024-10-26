from discord.ext import commands
import sqlite3

def get_db_connection():
    return sqlite3.connect('filter_words.db')

def setup(bot):
    @bot.command(name='add')
    @commands.has_permissions(administrator=True)
    async def add_keyword(ctx, *, keyword):
        conn = get_db_connection()
        c = conn.cursor()
        try:
            c.execute('INSERT INTO bad_words (word) VALUES (?)', (keyword.lower(),))
            conn.commit()
            await ctx.send(f"Keyword '{keyword}' has been added to the filter list.")
        except sqlite3.IntegrityError:
            await ctx.send(f"Keyword '{keyword}' is already in the filter list.")
        finally:
            conn.close()

    @bot.command(name='remove')
    @commands.has_permissions(administrator=True)
    async def remove_keyword(ctx, *, keyword):
        conn = get_db_connection()
        c = conn.cursor()
        c.execute('DELETE FROM bad_words WHERE word = ?', (keyword.lower(),))
        if c.rowcount == 0:
            await ctx.send(f"Keyword '{keyword}' was not found in the filter list.")
        else:
            conn.commit()
            await ctx.send(f"Keyword '{keyword}' has been removed from the filter list.")
        conn.close()

    @bot.command(name='list')
    @commands.has_permissions(administrator=True)
    async def list_keywords(ctx):
        conn = get_db_connection()
        c = conn.cursor()
        
        # cnt 값이 가장 큰 상위 15개만 불러오는 쿼리
        c.execute('SELECT word FROM bad_words ORDER BY cnt DESC LIMIT 15')
        words = c.fetchall()
        
        conn.close()
        
        if words:
            await ctx.send("Filtered keywords (Top 15):\n" + "\n".join(word[0] for word in words))
        else:
            await ctx.send("No keywords in the filter list.")

    @bot.command(name='unban')
    @commands.has_permissions(ban_members=True)
    async def unban(ctx, user_id: int):
        user = await bot.fetch_user(user_id)
        await ctx.guild.unban(user)
        invite = await ctx.channel.create_invite(max_age=300)  # 5분 동안 유효한 초대 링크 생성
        await send_dm(user, f"You have been unbanned from {ctx.guild.name}. You can rejoin using this link: {invite.url}")
        await ctx.send(f"{user.display_name} has been unbanned.")

    @bot.command(name='unmute')
    @commands.has_permissions(manage_roles=True)
    async def unmute(ctx, user_id: int):
        user = ctx.guild.get_member(user_id)
        mute_role = discord.utils.get(ctx.guild.roles, name="Mute")
        if mute_role in user.roles:
            await user.remove_roles(mute_role)
            await send_dm(user, f"You have been unmuted in {ctx.guild.name}.")
            await ctx.send(f"{user.display_name} has been unmuted.")
        else:
            await ctx.send("User is not muted.")

    @bot.command(name='kick')
    @commands.has_permissions(kick_members=True)
    async def kick(ctx, user_id: int):
        user = ctx.guild.get_member(user_id)
        await user.kick(reason="Kicked by command.")
        await send_dm(user, f"You have been kicked from {ctx.guild.name}.")
        await ctx.send(f"{user.display_name} has been kicked.")

async def send_dm(user, message):
    try:
        await user.send(message)
    except discord.HTTPException:
        pass  # 유저가 DM을 받지 않도록 설정했을 수 있습니다.
