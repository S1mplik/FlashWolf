from discord import User, Member, Message, Permissions, Embed, Role
from discord import Reaction, Emoji, PartialEmoji
from discord import TextChannel, Guild
from discord.ext.commands import AutoShardedBot as Bot
from discord.ext.commands import Cog, Context, command, group
from discord.ext.commands import has_guild_permissions
from discord.ext.commands import CheckFailure, BadArgument
from discord.ext.tasks import loop

from typing import Tuple, List, Dict, Union, Optional

from os.path import isfile, exists
import json
import asyncio
import traceback


class ReactionRole(Cog):
    file_name = "reaction_roles.json"

    def __init__(self, bot: Bot):
        self.bot = bot

        # target_messages[(guild_id, channel_id)] = Dict[message_id, Dict[reaction_id, role_id]]
        self._target_messages: Dict[str, Dict[str, Dict[str, int]]] = {}

    @property
    def target_messages(self):
        return self._target_messages

    @target_messages.setter
    def target_messages(self, arg):
        self._target_messages = arg
        self.save_messages()

    def save_messages(self):
        print("Saving targets")
        open(self.file_name, "w").write(json.dumps(self._target_messages))

    @Cog.listener()
    async def on_ready(self):
        self.reload_cache_task.start()
        return await self.reload_caches()

    @loop(minutes=10)
    async def reload_cache_task(self, *args, **kwargs):
        print("Reloading caches")
        await self.reload_caches()

    async def reload_caches(self):
        if exists(self.file_name):
            self.target_messages = json.load(open(self.file_name))

        print(self.target_messages)
        for g_c, v in self.target_messages.items():
            guild_id, channel_id = map(int, g_c.split(", "))
            try:
                # guild: Guild = await self.bot.fetch_guild(guild_id)
                channel: TextChannel = await self.bot.fetch_channel(channel_id)

                for msg_id in v.keys():
                    try:
                        msg = await channel.fetch_message(int(msg_id))
                        if msg_id not in [x.id for x in self.bot._connection._messages]:
                            self.bot._connection._messages.append(msg)
                            print("Added message cache:", msg_id)
                    except:
                        print(msg_id, traceback.format_exc())
                        pass
            except:
                print(traceback.format_exc())
                pass
        print(self.target_messages)

    async def get_registered_reactions(self, msg: Message) -> Dict[str, int]:
        guild_id: int = msg.guild.id if msg.guild else 0  # DM 채널 -> 0
        channel_id: int = msg.channel.id
        guild: Optional[Guild] = msg.guild

        if f"{guild_id}, {channel_id}" not in self.target_messages:
            return {}

        targets = self.target_messages[f"{guild_id}, {channel_id}"]
        if targets and targets.get(str(msg.id), None):
            return targets[str(msg.id)]

        return {}

    async def is_target_reaction(self, reaction, user):
        msg: Message = reaction.message
        guild: Optional[Guild] = msg.guild

        reactions = await self.get_registered_reactions(msg)
        key: str = ""

        if isinstance(reaction.emoji, str):
            if reaction.emoji not in reactions:
                return False, "Not in target emojis", None
            key = reaction.emoji

        else:
            if str(reaction.emoji.id) not in reactions:
                return False, "Not in target emojis", None
            key = str(reaction.emojiid)

        role_id = reactions[key]
        role = guild.get_role(role_id)

        if role:
            return True, "", role
        return False, "Role not found", None

    @Cog.listener()
    async def on_reaction_add(self, reaction: Reaction, user: Union[Member, User]):
        if user.bot:
            return

        # print(user, reaction.message.guild, reaction.message.channel, reaction)
        result, feedback, role = await self.is_target_reaction(reaction, user)

        if result:
            await user.add_roles(role)

            for _reac, _ in (await self.get_registered_reactions(reaction.message)).items():
                if _reac != reaction.emoji:
                    await reaction.message.remove_reaction(_reac, user)
        else:
            print(feedback)

    @Cog.listener()
    async def on_reaction_remove(self, reaction: Reaction, user: Union[Member, User]):
        result, feedback, role = await self.is_target_reaction(reaction, user)

        if result:
            await user.remove_roles(role)
        else:
            print(feedback)

    @command(name="add")
    @has_guild_permissions(administrator=True)
    async def c_add(self, ctx: Context, channel: TextChannel, *, content: str):
        perm_target: Permissions = channel.permissions_for(ctx.me)
        perm_this: Permissions = ctx.channel.permissions_for(ctx.me)
        if not perm_target.send_messages:
            return ctx.send(f"{ctx.author.mention} {channel.mention} nelze použít zkontrolujte práva")
        if not perm_this.add_reactions:
            return ctx.send(f"{ctx.author.mention} nelze připojit oprávnění k emodži na tomto kanálu.")
        if not perm_this.manage_messages:
            return ctx.send(f"{ctx.author.mention} z tohoto kanálu nemůžete smazat zprávy")

        embed_data = Embed(title="Emoji - Nová role", description=f"Titul: {content}").to_dict()
        embed_data["fields"] = [
            {
                "name": "Seznam registrovaných emodži",
                "value": "<Žádný>",
                "inline": False,
                },
            {
                "name": "Přidejte emoji",
                "value": "Chcete-li na tuto zprávu odpovědět, připojte emodži.\n"
                         "Dokončit ✅ klikněte na emodži.",
                "inline": False,
                }
            ]
        print(embed_data)
        msg = await ctx.send(embed=Embed.from_dict(embed_data))
        await msg.add_reaction("✅")

        def check_same_context(r: Reaction, u: Union[User, Member]):
            print(r, u)
            return u.id == ctx.author.id and r.message.id == msg.id

        def check_same_user(m: Message):
            print(m)
            return m.author.id == ctx.author.id

        first = True
        reactions: Dict[Reaction, Role] = {}
        while True:
            try:
                if not first and reactions:
                    embed_data["fields"][0]["value"] = "\n".join(f"{k} {v}" for k, v in reactions.items())
                else:
                    embed_data["fields"][0]["value"] = "<žádný>"

                embed_data["fields"][1] = {
                    "name": "Přidejte emodži",
                    "value": "Chcete-li na tuto zprávu odpovědět, připojte emodži.\n"
                             "Dokončit ✅ klikněte na emodži.",
                    "inline": False,
                    }
                await msg.edit(embed=Embed.from_dict(embed_data))

                reaction, user = await self.bot.wait_for("reaction_add", check=check_same_context)

                if reaction.emoji == "✅":
                    break

                if (isinstance(reaction.emoji, Emoji) and not reaction.emoji.available) or \
                        isinstance(reaction.emoji, PartialEmoji):
                    await ctx.send("Tuto emodži nemohou roboti použít. Vraťte se zpět k registraci emodži.", delete_after=5)
                    continue

                embed_data["fields"][1]["name"] = f"{reaction} nastavení role"
                embed_data["fields"][1]["value"] = "Uveďte roli, kterou chcete za tyto emodži zaplatit."
                await msg.edit(embed=Embed.from_dict(embed_data))

                try:
                    role_message: Message = await self.bot.wait_for("message", check=check_same_user, timeout=60*10)
                    if not role_message.role_mentions:
                        await ctx.send("Nezmínil jste správnou roli. Vraťte se zpět k registraci emodži.", delete_after=5)
                        continue

                    target_role = role_message.role_mentions[0]
                    reactions[reaction] = target_role
                    first = False
                    continue
                except asyncio.TimeoutError:
                    await ctx.send("Zrušil jsem registraci z důvodu časového limitu. Vraťte se zpět k registraci emodži.", delete_after=5)
                    continue
            except asyncio.TimeoutError:
                embed_data["fields"][1] = {
                    "name": "Přidejte emodži",
                    "value": "Chcete-li na tuto zprávu odpovědět, připojte emodži.\n"
                             "Dokončit ✅ klikněte na emodži.",
                    "inline": False,
                    }
                await msg.edit(embed=Embed.from_dict(embed_data))
            except:
                await ctx.send("Zrušil jsem registraci kvůli chybě.")
                return await ctx.send(traceback.format_exc())

        await msg.clear_reactions()
        del embed_data["fields"][1]
        embed_data["title"] = ""
        embed_data["description"] = ""
        embed_data["fields"][0]["name"] = content

        g_c = f"{ctx.guild.id}, {channel.id}"
        target_msg = await channel.send(
            "{}\n".format(content) + "\n".join("> {} {}".format(reac, role.mention) for reac, role in reactions.items())
            )
        for k in reactions:
            await target_msg.add_reaction(k.emoji)

        if g_c not in self.target_messages:
            self.target_messages[g_c] = {}

        self.target_messages[g_c][str(target_msg.id)] = \
            dict((k.emoji if isinstance(k.emoji, str) else str(k.emoji.id), v.id) for k, v in reactions.items())

        print(self.target_messages)
        self.save_messages()
        await ctx.send(f"{ctx.author.mention} registrace je dokončena.")

    @command(name="delete")
    @has_guild_permissions(administrator=True)
    async def c_remove(self, ctx: Context, msg_id: int):
        target_msg: Optional[Message] = None

        for g_c, v in self.target_messages.items():
            guild_id, channel_id = map(int, g_c.split(", "))
            if str(msg_id) in v.keys():
                channel: TextChannel = self.bot.get_channel(channel_id)
                target_msg = await channel.fetch_message(msg_id)

                await target_msg.delete()
                return await ctx.send(f"{ctx.author.mention} úspěšně jsem to smazal.")

        if not target_msg:
            return await ctx.send(f"{ctx.author.mention} nebyla nalezena žádná cílová zpráva.")

    @command(name="r")
    async def c_r(self, ctx: Context):
        try:
            await self.reload_caches()
            return await ctx.send(f"{ctx.author.mention} úspěch obnovy")
        except:
            return await ctx.send(traceback.format_exc())

    @c_add.error
    async def c_add_error(self, ctx: Context, error):
        if isinstance(error, CheckFailure):
            return await ctx.send(f"{ctx.author.mention} abyste mohli používat tento příkaz, musíte být administrátorem serveru.")
        elif isinstance(error, BadArgument):
            return await ctx.send(f"{ctx.author.mention} správné použití\n"
                                  f"> {self.bot.command_prefix} přidat <zmínku o kanálu> [... zprávu k odeslání]")
        else:
            return await ctx.send(traceback.format_exc())

    @c_remove.error
    async def c_remove_error(self, ctx: Context, error):
        if isinstance(error, CheckFailure):
            return await ctx.send(f"{ctx.author.mention} abyste mohli používat tento příkaz, musíte být administrátorem serveru.")
        elif isinstance(error, BadArgument):
            return await ctx.send(f"{ctx.author.mention} správné použití\n"
                                  f"> {self.bot.command_prefix} Odstranit <ID zprávy>\n\n"
                                  f"* Informace o tom, jak zjistit ID zprávy, najdete na níže uvedeném odkazu.\n"
                                  f"<https://support.discordapp.com/hc/ko/articles/"
                                  f"206346498-%EC%9C%A0%EC%A0%80-%EC%84%9C%EB%B2%84-"
                                  f"%EB%A9%94%EC%8B%9C%EC%A7%80-ID%EB%8A%94-%EC%96%B4%EB%94%94%EC%84%9C-"
                                  f"%EC%B0%BE%EB%82%98%EC%9A%94->")
        else:
            return await ctx.send(traceback.format_exc())

    @command(name="b")
    async def c_b(self, ctx: Context):
        await ctx.send(f"```py\n{self.bot.cached_messages}\n```")
        await ctx.send(f"```py\n{[x.id for x in self.bot._connection._messages]}\n```")

    @command(name="c1")
    async def c_c1(self, ctx, *args):
        return await ctx.send(repr(args))

    @command(name="c2")
    async def c_c2(self, ctx, *, args):
        return await ctx.send(repr(args))


def setup(bot: Bot):
    bot.add_cog(ReactionRole(bot))