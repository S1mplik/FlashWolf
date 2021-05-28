import datetime
import io
import json
from itertools import cycle
import aiohttp
import discord
import time
import sys
import youtube_dl
import mysql
from colorama import Fore
from discord.ext import commands, tasks
import random
import asyncio
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib import style
import os
import http


style.use("fivethirtyeight")

client = commands.Bot(command_prefix='!')

client.remove_command("help")

status = cycle(
    ['na příkaz !help'])


@client.event
async def on_ready():
    change_status.start()
    print(f"{client.user} se připojil")


@tasks.loop(seconds=5)
async def change_status():
    await client.change_presence(activity=discord.Game(next(status)))


#economy

mainshop = [{"name": "Hodinky", "price": 100, "description": "Čas"},
            {"name": "Notebook", "price": 1000, "description": "Práce"},
            {"name": "Počítač", "price": 10000, "description": "Hraní"},
            {"name": "Ferrari", "price": 99999, "description": "Sportovní auto"}]


@client.command(aliases=['bal'])
async def balance(ctx):
    await open_account(ctx.author)
    user = ctx.author

    users = await get_bank_data()

    wallet_amt = users[str(user.id)]["wallet"]
    bank_amt = users[str(user.id)]["bank"]

    embed = discord.Embed(title=f'{ctx.author.name} Balance', color=discord.Color.red())
    embed.add_field(name="Wallet Balance", value=wallet_amt)
    embed.add_field(name='Bank Balance', value=bank_amt)
    await ctx.send(embed=embed)


@client.command()
async def beg(ctx):
    await open_account(ctx.author)
    user = ctx.author

    users = await get_bank_data()

    earnings = random.randrange(101)

    await ctx.send(f'{ctx.author.mention} získal {earnings} peněz!!')

    users[str(user.id)]["wallet"] += earnings

    with open("mainbank.json", 'w') as f:
        json.dump(users, f)


@client.command(aliases=['wd'])
async def withdraw(ctx, amount=None):
    await open_account(ctx.author)
    if amount == None:
        await ctx.send("Zadej hodnotu")
        return

    bal = await update_bank(ctx.author)

    amount = int(amount)

    if amount > bal[1]:
        await ctx.send('Nemáš dostatek peněz')
        return
    if amount < 0:
        await ctx.send('Částka musí být v pozitivním. Čísla 1 - nekonečno')
        return

    await update_bank(ctx.author, amount)
    await update_bank(ctx.author, -1 * amount, 'bank')
    await ctx.send(f'{ctx.author.mention} Withdraw {amount} peněz')


@client.command(aliases=['dp'])
async def deposit(ctx, amount=None):
    await open_account(ctx.author)
    if amount == None:
        await ctx.send("Zadej částku")
        return

    bal = await update_bank(ctx.author)

    amount = int(amount)

    if amount > bal[0]:
        await ctx.send('Nemáš dostatek peněz')
        return
    if amount < 0:
        await ctx.send('Částka musí být v pozitivním. Čísla 1 - nekonečno')
        return

    await update_bank(ctx.author, -1 * amount)
    await update_bank(ctx.author, amount, 'bank')
    await ctx.send(f'{ctx.author.mention} Deposit {amount} peněz')


@client.command(aliases=['sm'])
async def send(ctx, member: discord.Member, amount=None):
    await open_account(ctx.author)
    await open_account(member)
    if amount == None:
        await ctx.send("Zadej hodnotu")
        return

    bal = await update_bank(ctx.author)
    if amount == 'all':
        amount = bal[0]

    amount = int(amount)

    if amount > bal[0]:
        await ctx.send('Nemáš dostatek peněz')
        return
    if amount < 0:
        await ctx.send('Částka musí být v pozitivním. Čísla 1 - nekonečno')
        return

    await update_bank(ctx.author, -1 * amount, 'bank')
    await update_bank(member, amount, 'bank')
    await ctx.send(f'{ctx.author.mention} Dostal {member} {amount} peněz')


@client.command(aliases=['rb'])
async def rob(ctx, member: discord.Member):
    await open_account(ctx.author)
    await open_account(member)
    bal = await update_bank(member)

    if bal[0] < 100:
        await ctx.send('Je zbytečné ho okrádat, když nemáš o co :(')

        return

    earning = random.randrange(0, bal[0])

    await update_bank(ctx.author, earning)
    await update_bank(member, -1 * earning)
    await ctx.send(f'{ctx.author.mention} okradl {member} o {earning} peněz')



@client.command(aliases=['wk'])
async def work(ctx):
    await open_account(ctx.author)

    earning = random.randrange(1, 2)
    await update_bank(ctx.author, earning)
    await ctx.send(f'{ctx.author.mention} získal si {earning} peněz')


@client.command(aliases=['crim'])
async def crime(ctx):
    await open_account(ctx.author)

    earning = random.randrange(50, 500)
    await update_bank(ctx.author, earning)
    await ctx.send(f'{ctx.author.mention} ukradl si {earning} peněz')



@client.command()
async def slots(ctx, amount=None):
    await open_account(ctx.author)
    if amount == None:
        await ctx.send("Zadej částku")
        return

    bal = await update_bank(ctx.author)

    amount = int(amount)

    if amount > bal[0]:
        await ctx.send('Nemáš dostatek vložené částky')
        return
    if amount < 0:
        await ctx.send('Částka musí být v pozitivním. Čísla 1 - nekonečno')
        return
    final = []
    for i in range(3):
        a = random.choice(['X', 'O', 'Q'])

        final.append(a)

    await ctx.send(str(final))

    if final[0] == final[1] or final[1] == final[2] or final[0] == final[2]:
        await update_bank(ctx.author, 2 * amount)
        await ctx.send(f'Vyhrál jsi :) {ctx.author.mention}')
    else:
        await update_bank(ctx.author, -1 * amount)
        await ctx.send(f'Prohrál si :( {ctx.author.mention}')


@client.command()
async def shop(ctx):
    embed = discord.Embed(title="Obchod")

    for item in mainshop:
        name = item["name"]
        price = item["price"]
        desc = item["description"]
        embed.add_field(name=name, value=f"${price} | {desc}")

    await ctx.send(embed=embed)


@client.command()
async def buy(ctx, item, amount=1):
    await open_account(ctx.author)

    res = await buy_this(ctx.author, item, amount)

    if not res[0]:
        if res[1] == 1:
            await ctx.send("Tento předmět zde není")
            return
        if res[1] == 2:
            await ctx.send(f"Nemáš dostatek penež na koupení {amount} {item}")
            return

    await ctx.send(f"Získal si {amount} {item}")


@client.command()
async def bag(ctx):
    await open_account(ctx.author)
    user = ctx.author
    users = await get_bank_data()

    try:
        bag = users[str(user.id)]["bag"]
    except:
        bag = []

    embed = discord.Embed(title="Batoh")
    for item in bag:
        name = item["item"]
        amount = item["amount"]

        embed.add_field(name=name, value=amount)

    await ctx.send(embed=embed)


async def buy_this(user, item_name, amount):
    item_name = item_name.lower()
    name_ = None
    for item in mainshop:
        name = item["name"].lower()
        if name == item_name:
            name_ = name
            price = item["price"]
            break

    if name_ == None:
        return [False, 1]

    cost = price * amount

    users = await get_bank_data()

    bal = await update_bank(user)

    if bal[0] < cost:
        return [False, 2]

    try:
        index = 0
        t = None
        for thing in users[str(user.id)]["bag"]:
            n = thing["item"]
            if n == item_name:
                old_amt = thing["amount"]
                new_amt = old_amt + amount
                users[str(user.id)]["bag"][index]["amount"] = new_amt
                t = 1
                break
            index += 1
        if t == None:
            obj = {"item": item_name, "amount": amount}
            users[str(user.id)]["bag"].append(obj)
    except:
        obj = {"item": item_name, "amount": amount}
        users[str(user.id)]["bag"] = [obj]

    with open("mainbank.json", "w") as f:
        json.dump(users, f)

    await update_bank(user, cost * -1, "wallet")

    return [True, "Odpracováno"]


@client.command()
async def sell(ctx, item, amount=1):
    await open_account(ctx.author)

    res = await sell_this(ctx.author, item, amount)

    if not res[0]:
        if res[1] == 1:
            await ctx.send("Tento předmět tu není")
            return
        if res[1] == 2:
            await ctx.send(f"Toto nemůžeš prodat {amount} {item}, protože to není v tvém batohu")
            return
        if res[1] == 3:
            await ctx.send(f"Toto nemůžeš prodat {item}, protože to nemáš v batohu")
            return

    await ctx.send(f"Bylo prodáno {amount} {item}.")


async def sell_this(user, item_name, amount, price=None):
    item_name = item_name.lower()
    name_ = None
    for item in mainshop:
        name = item["name"].lower()
        if name == item_name:
            name_ = name
            if price == None:
                price = 0.7 * item["price"]
            break

    if name_ == None:
        return [False, 1]

    cost = price * amount

    users = await get_bank_data()

    bal = await update_bank(user)

    try:
        index = 0
        t = None
        for thing in users[str(user.id)]["bag"]:
            n = thing["item"]
            if n == item_name:
                old_amt = thing["amount"]
                new_amt = old_amt - amount
                if new_amt < 0:
                    return [False, 2]
                users[str(user.id)]["bag"][index]["amount"] = new_amt
                t = 1
                break
            index += 1
        if t == None:
            return [False, 3]
    except:
        return [False, 3]

    with open("mainbank.json", "w") as f:
        json.dump(users, f)

    await update_bank(user, cost, "wallet")

    return [True, "Odpracováno"]


@client.command(aliases=["lb"])
async def leaderboard(ctx, x=1):
    users = await get_bank_data()
    leader_board = {}
    total = []
    for user in users:
        name = int(user)
        total_amount = users[user]["wallet"] + users[user]["bank"]
        leader_board[total_amount] = name
        total.append(total_amount)

    total = sorted(total, reverse=True)

    embed = discord.Embed(title=f"Top {x} Nejbohatší člověk",
                       description="Toto zobrazuje tvé bohatství",
                       color=discord.Color(0xfa43ee))
    index = 1
    for amt in total:
        id_ = leader_board[amt]
        member = client.get_user(id_)
        name = member.name
        embed.add_field(name=f"{index}. {name}", value=f"{amt}", inline=False)
        if index == x:
            break
        else:
            index += 1

    await ctx.send(embed=embed)


async def open_account(user):
    users = await get_bank_data()

    if str(user.id) in users:
        return False
    else:
        users[str(user.id)] = {}
        users[str(user.id)]["wallet"] = 0
        users[str(user.id)]["bank"] = 0

    with open('mainbank.json', 'w') as f:
        json.dump(users, f)

    return True


async def get_bank_data():
    with open('mainbank.json', 'r') as f:
        users = json.load(f)

    return users


async def update_bank(user, change=0, mode='wallet'):
    users = await get_bank_data()

    users[str(user.id)][mode] += change

    with open('mainbank.json', 'w') as f:
        json.dump(users, f)
    bal = users[str(user.id)]['wallet'], users[str(user.id)]['bank']
    return bal




#cogs


for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')



#main



# token
TOKEN = ('YOUR-DISCORD-BOT-TOKEN')













@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("Neznámý příkaz")

@client.command()
async def meme(ctx):
    async with aiohttp.ClientSession() as cs:
        async with cs.get("https://www.reddit.com/r/memes.json") as r:
            memes = await r.json()
            embed = discord.Embed(color = discord.Color.blue())
            embed.set_image(url=memes["data"]["children"][random.randint(0, 25)]["data"]["url"])
            embed.set_footer(text=f"Memes jsou brány z platformy Reddit || Meme byl vyžádán od {ctx.author}")
            await ctx.send(embed=embed)


@client.command()
async def ping(ctx):
    await ctx.send(f'Odezva: {round(client.latency * 1000)}ms' )


@client.command()
async def serverinfo(ctx):
    embed = discord.Embed(title=f" Název Serveru: {ctx.guild.name}\n", description="Informace", timestamp=datetime.datetime.utcnow(), color=discord.Color.blue())
    embed.add_field(name="Vytvoření Serveru", value=f"{ctx.guild.created_at}\n")
    embed.add_field(name="Majitel Serveru", value=f"{ctx.guild.owner}\n")
    embed.add_field(name="Oblast", value=f"{ctx.guild.region}\n")
    embed.add_field(name="ID Serveru", value=f"{ctx.guild.id}\n")
    # embed.set_thumbnail(url=f"{ctx.guild.icon}")
    embed.set_thumbnail(url="https://upload.hicoria.com/files/Tc2qBXx1.png")

    await ctx.send(embed=embed)






support_channel = 845344459016765500

channel_2_people = 845344506932232203
channel_5_people = 845344537504776202
channel_10_people = 845344563522568263
channel_no_limit = 845344650876813322

group_channels = []
onleave_channels = []




async def createSupportChannel(member, category):
    global onleave_channels

    # Generate new voice channel
    new_channel = await category.create_voice_channel(f"{member.name} ✋🏼")
    onleave_channels.append(new_channel.id)

    # Move user to newly created voice channel
    await member.move_to(new_channel)
    print(new_channel.name, "byl vytvořen")


async def createGroupChannel(member, limit, category):
    global group_channels

    # Generates new group channel with group #
    new_channel = await category.create_voice_channel(f"{member.name} kanál 😆")

    # Adds a user limit to newly generated channel if required
    if limit > 0:
        await new_channel.edit(user_limit=limit)

    # Adds newly generated channel id to lists
    group_channels.append(new_channel.id)
    onleave_channels.append(new_channel.id)

    # Move user to newly created voice channel
    await member.move_to(new_channel)
    print(new_channel.name, "byl vytvořen")


async def updateGroupChannels(deleted_channel):
    # Updates name numbering of group channels
    for channel in deleted_channel.category.channels:
        if channel.id in group_channels:
            await channel.edit(name=f"Skupina #{group_channels.index(channel.id) + 1}")


async def checkAfterChannels(member, after_channel):
    # Checks if channel joined is a support channel
    if after_channel.id == support_channel:
        print(f"{member.name} vytvořil pomocný kanál")
        await createSupportChannel(member, after_channel.category)

    # Checks if channel joined is 2 person channel
    elif after_channel.id == channel_2_people:
        print(f"{member.name} vytvořil kanál pro 2 osoby")
        await createGroupChannel(member, 2, after_channel.category)

    # Checks if channel joined is 5 person channel
    elif after_channel.id == channel_5_people:
        print(f"{member.name} vytvořil kanál pro 5 osob")
        await createGroupChannel(member, 5, after_channel.category)

    # Checks if channel joined is 10 person channel
    elif after_channel.id == channel_10_people:
        print(f"{member.name} vytvořil kanál pro 10 osob")
        await createGroupChannel(member, 10, after_channel.category)

    # Checks if channel joined is no limit channel
    elif after_channel.id == channel_no_limit:
        print(f"{member.name} vytvořil neomezený kanál")
        await createGroupChannel(member, 0, after_channel.category)


async def checkBeforeChannels(before_channel):
    # Check if channel should be deleted and is empty
    if before_channel.id in onleave_channels and len(client.get_channel(before_channel.id).members) == 0:
        onleave_channels.remove(before_channel.id)

        # Delete empty channel
        await client.get_channel(before_channel.id).delete()

        # Check if channel is a group channel
        if before_channel.id in group_channels:
            group_channels.remove(before_channel.id)
            await updateGroupChannels(before_channel)

        print(before_channel.name, "byl smazán")


async def checkChannels(member, before_channel, after_channel):

    # Checks if channel left exists
    if before_channel != None:
        await checkBeforeChannels(before_channel)

    # Checks if channel joined exists
    if after_channel != None:
        await checkAfterChannels(member, after_channel)






@client.event
async def on_voice_state_update(member, before, after):
    await checkChannels(member, before.channel, after.channel)





@client.command()
async def clear(ctx, amount=10):
    await ctx.channel.purge(limit=amount)
    await ctx.send(f"Bylo smazáno **{amount}** zpráv. Uživatelem **{ctx.author}** ")

@client.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, user: discord.Member, *, reason=None):
    if not reason:
        await ctx.send("Musíš uvést důvod proč chceš hráče vyhodit")
    else:
        await user.kick(reason=reason)
        await ctx.send(f"**{user}** byl vyhozen. Důvod: **{reason}**.")

@client.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, user: discord.Member, *, reason=None):
     if not reason:
        await ctx.send("Musíš uvést důvod proč chceš hráče zabanovat")
     else:
        await user.ban(reason=reason)
        await ctx.send(f"**{user}** byl zabanován. Důvod: **{reason}**.")

@client.command()
@commands.has_permissions(administrator=True)
async def unban(self, ctx, *, member):
    banned_users = await ctx.guild.bans()
    member_name, member_discriminator = member.split("#")

    for ban_entry in banned_users:
        user = ban_entry.user

        if (user.name, user.discriminator) == (member_name, member_discriminator):
            await ctx.guild.unban(user)
            await ctx.send(f'{user.mention} byl odbanován')
            return

@client.command()
async def help(ctx):
    embed = discord.Embed(title="Pomocné menu", description="Pomocné menu slouží pro lidi co si neví rady jak aktivovat dočasné místnosti", color=discord.Color.blue())
    embed.add_field(name="Jak aktivovat dočasný kanál", value="Je to naprosto jednoduché stačí jen kliknout na kanál pro 2 či pro 5 či pro 10 nebo neomezený pokud toto uděláte vytvoří se vám dočasný kanál s vaším názvem", inline=False)
    embed.add_field(name="!kick", value="Vyhodí hráče ze serveru")
    embed.add_field(name="!ban", value="Zabanuje hráče na serveru")
    embed.add_field(name="!clear", value="Smaže určitou část textu v určitém kanále")
    embed.add_field(name="!meme", value="Zobrazí nějáký vtip v podobě fotky")
    embed.add_field(name="!unban", value="Odbanuje hráče ze serveru")
    embed.add_field(name="!serverinfo", value="Zobrazí informace o serveru")
    embed.add_field(name="!bot", value="Zobrazí statisticky o botovi")
    embed.add_field(name="!roll", value="Vyhodí náhodné číslo")
    embed.add_field(name="!balance", value="Tvé peníze")
    embed.add_field(name="!shop", value="Obchod")
    embed.add_field(name="!rob", value="Okrade někoho na serveru")
    embed.add_field(name="!bag", value="Tvůj batoh")
    embed.add_field(name="!buy", value="Můžeš si něco koupit")
    embed.add_field(name="!sell", value="Můžeš cokoliv co vlastníš prodat")
    embed.add_field(name="!beg", value="Můžeš vyhrát peníze")
    embed.add_field(name="!slots + částka", value="Výherní automat")
    embed.add_field(name="!send", value="Můžeš poslat peníze")
    embed.add_field(name="!withdraw", value="Můžeš si uložit své peníze do banky")
    embed.add_field(name="!deposit", value="Můžeš si peníze vzít v bankovkách")
    embed.add_field(name="!add (jméno kanálu) + (zprávu)", value="Pošle zprávu po reakci na emodži")
    embed.add_field(name="!delete (jméno kanálu) + (zprávu)", value="Smaže zprávu po reakci na emodži")
    embed.add_field(name="!mute", value="Umlčí uživatele")
    embed.add_field(name="!gstart (čas) + (výhru)", value="Aktivuje soutěž")
    embed.add_field(name="!giveaway", value="Aktivuješ soutěž kde chceš a na jak dlouho")
    embed.add_field(name="!new (název ticketu)", value="Vytvoří ticket s uvedeným názvem")
    embed.add_field(name="!close", value="Uzavře ticket")
    embed.add_field(name="!addaccess", value="Přidá oprávnění roli k ticketu")
    embed.add_field(name="!delaccess", value="Odstraní oprávnění roli k ticketu")
    embed.add_field(name="!addpingedrole", value="Přídá roli do ticketu")
    embed.add_field(name="!delpingedrole", value="Odstraní roli z ticketu")
    embed.add_field(name="!addadminrole", value="Přidá admin roli do ticketu")
    embed.add_field(name="!deladminrole", value="Odstraní admin roli z ticketu")
    embed.set_thumbnail(url="https://upload.hicoria.com/files/wkwzWcEA.png")
    await ctx.send(embed=embed)

@client.command()
async def roll(self, ctx):
    n = random.randrange(1, 101)
    await ctx.send(f"Padlo ti číslo: **{n}**")



@client.command(description="Umlčíš určitého uživatele")
@commands.has_permissions(manage_messages=True)
async def mute(ctx, member: discord.Member, *, reason=None):
    guild = ctx.guild
    mutedRole = discord.utils.get(guild.roles, name="Muted")

    if not mutedRole:
        mutedRole = await guild.create_role(name="Muted")

        for channel in guild.channels:
            await channel.set_permissions(mutedRole, speak=False, send_messages=False, read_message_history=True, read_messages=False)
    embed = discord.Embed(title="Muted", description=f"{member.mention} byl umlčen ", colour=discord.Colour.light_gray())
    embed.add_field(name="Důvod:", value=reason, inline=False)
    await ctx.send(embed=embed)
    await member.add_roles(mutedRole, reason=reason)
    await member.send(f"Byl si umlčen na: {guild.name} Důvod: {reason}")

@client.event
async def on_member_join(member):
    with open('users.json', 'r') as f:
        users = json.load(f)

    await update_data(users, member)

    with open('users.json', 'w') as f:
        json.dump(users, f)





@client.event
async def on_message(message):
    with io.open("chatlogs.txt", "a", encoding="utf-8") as f:
        f.write(
            "[{}] | [{}] | [{}] @ {}: {}\n".format(message.guild,
                                                   message.channel,
                                                   message.author,
                                                   message.created_at,
                                                   message.content))
    f.close()
    print(
        Fore.WHITE + "[" + Fore.LIGHTRED_EX + '+' + Fore.WHITE + "]"
        + Fore.GREEN + "[{}] | [{}] | [{}] @ {}: {}".format(
            message.guild, message.channel, message.author,
            message.created_at, message.content))




    bad_words = ["fuck", "zmrde", "mrtko", "kurvo", "píčo", "debile", "arschloch", "https://discord.gg", "http://disord.gg", "discord.gg", "fick", "arsch", "Arschgesicht", "arschgesicht", "Arschloch", "Asshole", "asshole", "Fotze", "fotze", "Miststück", "miststück", "Bitch", "bitch", "Schlampe", "schlampe", "Sheisse", "sheisse", "Shit", "shit", "Fick", "huren", "Verpiss", "verpiss", "masturbiert", "Idiot", "idiot", "depp", "Depp", "Dumm", "dumm", "jude", "Bastard", "bastard", "Wichser", "wichser", "wixxer", "Wixxer", "Hurensohn" "Wixer", "Pisser", "Arschgesicht", "huso", "hure", "Hure", "verreck" "Verreck", "fehlgeburt", "Fehlgeburt", "ficken", "adhs", "ADHS", "Btch", "faggot", "fck", "f4ck", "nigga", "Nutted", "flaschengeburt", "penis", "pusse", "pusse", "pussy", "pussys", "nigger", "kacke", "fuucker"]
    for word in bad_words:
        if message.content.count(word) > 0:
            await message.channel.purge(limit=1)
            await message.channel.send(f"Byl si varován {message.author.mention}")



    await client.process_commands(message)


    with open('users.json', 'r') as f:
        users = json.load(f)

    await update_data(users, message.author)
    await add_experience(users, message.author, 5)
    await level_up(users, message.author, message.channel)

    with open('users.json', 'w') as f:
        json.dump(users, f)

async def update_data(users, user):
    if not user.id in users:
        users[user.id] = {}
        users[user.id]['experience'] = 0
        users[user.id]['level'] = 1



async def add_experience(users, user, exp):
    users[user.id]['experience'] += exp


async def level_up(users, user, channel):
    experience = users[user.id]['experience']
    lvl_start = users[user.id]['level']
    lvl_end = int(experience ** (1/4))




    if lvl_start < lvl_end:
        await client.send_message(channel, '{} dosáhl vyšší úrovně {}'.format(user.mention, lvl_end))
        users[user.id]['level'] = lvl_end





@client.command()
@commands.has_permissions(administrator=True)
async def giveaway(ctx):
    await ctx.send("Pojďme začít s nastavením soutěže. Budou ti položeny otázky a ty na ně musíš odpovědět do 15 vteřin")

    questions = ["Ve kterém kanálu chceš soutěž pořádat ?",
                 "Jak dlouho bude trvat soutěž (s|m|h|d)",
                 "O co se bude hrát (cena) ?"]

    answers = []

    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    for i in questions:
        await ctx.send(i)

        try:
            msg = await client.wait_for('message', timeout=15.0, check=check)
        except asyncio.TimeoutError:
            await ctx.send("Čas vypršel. Musíš začnout od znova")
            return
        else:
            answers.append(msg.content)


    try:
        c_id = int(answers[0][2:-1])
    except:
        await ctx.send(f"Urči správný kanál {ctx.channel.mention}")


    channel = client.get_channel(c_id)

    time = convert(answers[1])
    if time == -1:
        await ctx.send(f"Odpověď neodpovídá zadání")
        return
    elif time == -2:
        await ctx.send(f"Čas se neshoduje se zadáním")
        return
    prize = answers[2]

    await ctx.send(f"Soutěž proběhne v {channel.mention} v posledních {answers[1]} sekundách")

    embed = discord.Embed(title="Soutěž", description=f"{prize}", color = ctx.author.color)

    embed.add_field(name="Hostováno od:", value=ctx.author.mention)

    embed.set_footer(text=f"Konec {answers[1]} od teď!")

    my_msg = await channel.send(embed=embed)

    await my_msg.add_reaction("🎉")

    await asyncio.sleep(time)

    new_msg = await channel.fetch_message(my_msg.id)

    users = await new_msg.reactions[0].users().flatten()
    users.pop(users.index(client.user))

    winner = random.choice(users)

    await channel.send(f"Gratuluji! {winner.mention} vyhrál {prize}!")



@client.command()
@commands.has_permissions(administrator=True)
async def reroll(ctx, channel : discord.TextChannel, id_ :int):
    try:
        new_msg = await channel.fetch_message(id_)
    except:
        await ctx.send("ID se neshoduje.")
        return

    users = await new_msg.reactions[0].users().flatten()
    users.pop(users.index(client.user))

    winner = random.choice(users)

    await channel.send(f"Gratuluji! Nový výherce {winner.mention}.")



@client.command()
@commands.has_permissions(administrator=True)
async def gstart(ctx, mins : int, *, prize: str ):
    embed = discord.Embed(title="Soutěž", description=f"{prize}", color = ctx.author.color)

    end = datetime.datetime.utcnow() + datetime.timedelta(seconds = mins*60)

    embed.add_field(name="Konec soutěže", value=f"{end} UTC")
    embed.set_footer(text=f"Konec za {mins} minut od teď")

    my_msg = await ctx.send(embed=embed)

    await my_msg.add_reaction("🎉")

    await asyncio.sleep(mins)

    new_msg = await ctx.channel.fetch_message(my_msg.id)

    users = await new_msg.reactions[0].users().flattern()
    users.pop(users.index(client.user))

    winner = random.choice(users)

    await ctx.send(f"Gratuluji {winner.mention} za výhru. Vyhrál: {prize} !")


def convert(time):
    pos = ["s", "m", "h", "d"]

    time_dict = {"s" : 1, "m" : 60, "h" : 3600, "d" : 3600*24}

    unit = time[-1]

    if unit not in pos:
        return -1
    try:
        val = int(time[:-1])
    except:
        return -2


    return val * time_dict[unit]


@client.command()
async def new(ctx, *, args=None):
    await client.wait_until_ready()

    if args == None:
        message_content = "Chvilku vydržte"

    else:
        message_content = "".join(args)

    with open("data.json") as f:
        data = json.load(f)

    ticket_number = int(data["ticket-counter"])
    ticket_number += 1

    ticket_channel = await ctx.guild.create_text_channel("ticket-{}".format(ticket_number))
    await ticket_channel.set_permissions(ctx.guild.get_role(ctx.guild.id), send_messages=False, read_messages=False)

    for role_id in data["valid-roles"]:
        role = ctx.guild.get_role(role_id)

        await ticket_channel.set_permissions(role, send_messages=True, read_messages=True, add_reactions=True,
                                             embed_links=True, attach_files=True, read_message_history=True,
                                             external_emojis=True)

    await ticket_channel.set_permissions(ctx.author, send_messages=True, read_messages=True, add_reactions=True,
                                         embed_links=True, attach_files=True, read_message_history=True,
                                         external_emojis=True)

    em = discord.Embed(title="Nový ticket od {}#{}".format(ctx.author.name, ctx.author.discriminator),
                       description="{}".format(message_content), color=0x00a8ff)

    await ticket_channel.send(embed=em)

    pinged_msg_content = ""
    non_mentionable_roles = []

    if data["pinged-roles"] != []:

        for role_id in data["pinged-roles"]:
            role = ctx.guild.get_role(role_id)

            pinged_msg_content += role.mention
            pinged_msg_content += " "

            if role.mentionable:
                pass
            else:
                await role.edit(mentionable=True)
                non_mentionable_roles.append(role)

        await ticket_channel.send(pinged_msg_content)

        for role in non_mentionable_roles:
            await role.edit(mentionable=False)

    data["ticket-channel-ids"].append(ticket_channel.id)

    data["ticket-counter"] = int(ticket_number)
    with open("data.json", 'w') as f:
        json.dump(data, f)

    created_em = discord.Embed(title="Ticket",
                               description="Ticket byl vytvořen {}".format(ticket_channel.mention),
                               color=0x00a8ff)

    await ctx.send(embed=created_em)


@client.command()
async def close(ctx):
    with open('data.json') as f:
        data = json.load(f)

    if ctx.channel.id in data["ticket-channel-ids"]:

        channel_id = ctx.channel.id

        def check(message):
            return message.author == ctx.author and message.channel == ctx.channel and message.content.lower() == "close"

        try:

            em = discord.Embed(title="Tickets",
                               description="Jste si jistý, že chce smazat ticket. Pokud ano napište `close`.",
                               color=0x00a8ff)

            await ctx.send(embed=em)
            await client.wait_for('message', check=check, timeout=60)
            await ctx.channel.delete()

            index = data["ticket-channel-ids"].index(channel_id)
            del data["ticket-channel-ids"][index]

            with open('data.json', 'w') as f:
                json.dump(data, f)

        except asyncio.TimeoutError:
            em = discord.Embed(title="Ticket",
                               description="Ticket byl časově uzavřen použij spouštěcí příkaz nebo si udělej nový.",
                               color=0x00a8ff)
            await ctx.send(embed=em)


@client.command()
async def addaccess(ctx, role_id=None):
    with open('data.json') as f:
        data = json.load(f)

    valid_user = False

    for role_id in data["verified-roles"]:
        try:
            if ctx.guild.get_role(role_id) in ctx.author.roles:
                valid_user = True
        except:
            pass

    if valid_user or ctx.author.guild_permissions.administrator:
        role_id = int(role_id)

        if role_id not in data["valid-roles"]:

            try:
                role = ctx.guild.get_role(role_id)

                with open("data.json") as f:
                    data = json.load(f)

                data["valid-roles"].append(role_id)

                with open('data.json', 'w') as f:
                    json.dump(data, f)

                em = discord.Embed(title="Ticket",
                                   description="Byl si úspešně přidán `{}` do potvrzených rolí v tomto ticketu".format(
                                       role.name), color=0x00a8ff)

                await ctx.send(embed=em)

            except:
                em = discord.Embed(title="Ticket",
                                   description="Toto není ID role. Jste si jistý, že zadáváte id správně")
                await ctx.send(embed=em)

        else:
            em = discord.Embed(title="Ticket", description="Tato role je v ticketu přidána",
                               color=0x00a8ff)
            await ctx.send(embed=em)

    else:
        em = discord.Embed(title="Ticket", description="Nemáš právo na použití tohoto příkazu",
                           color=0x00a8ff)
        await ctx.send(embed=em)


@client.command()
async def delaccess(ctx, role_id=None):
    with open('data.json') as f:
        data = json.load(f)

    valid_user = False

    for role_id in data["verified-roles"]:
        try:
            if ctx.guild.get_role(role_id) in ctx.author.roles:
                valid_user = True
        except:
            pass

    if valid_user or ctx.author.guild_permissions.administrator:

        try:
            role_id = int(role_id)
            role = ctx.guild.get_role(role_id)

            with open("data.json") as f:
                data = json.load(f)

            valid_roles = data["valid-roles"]

            if role_id in valid_roles:
                index = valid_roles.index(role_id)

                del valid_roles[index]

                data["valid-roles"] = valid_roles

                with open('data.json', 'w') as f:
                    json.dump(data, f)

                em = discord.Embed(title="Ticket",
                                   description="Úspešně odstraněn `{}` z listu potvrzeních rolí".format(
                                       role.name), color=0x00a8ff)

                await ctx.send(embed=em)

            else:

                em = discord.Embed(title="Ticket",
                                   description="Tato roli je v seznamu", color=0x00a8ff)
                await ctx.send(embed=em)

        except:
            em = discord.Embed(title="Ticket",
                               description="Jste si jistý, že jste zadal správný ID Role")
            await ctx.send(embed=em)

    else:
        em = discord.Embed(title="Ticket", description="Nemáš právo na použití tohoto příkazu",
                           color=0x00a8ff)
        await ctx.send(embed=em)


@client.command()
async def addpingedrole(ctx, role_id=None):
    with open('data.json') as f:
        data = json.load(f)

    valid_user = False

    for role_id in data["verified-roles"]:
        try:
            if ctx.guild.get_role(role_id) in ctx.author.roles:
                valid_user = True
        except:
            pass

    if valid_user or ctx.author.guild_permissions.administrator:

        role_id = int(role_id)

        if role_id not in data["pinged-roles"]:

            try:
                role = ctx.guild.get_role(role_id)

                with open("data.json") as f:
                    data = json.load(f)

                data["pinged-roles"].append(role_id)

                with open('data.json', 'w') as f:
                    json.dump(data, f)

                em = discord.Embed(title="Ticket",
                                   description="Byla přidána `{}` role do ticketu".format(
                                       role.name), color=0x00a8ff)

                await ctx.send(embed=em)

            except:
                em = discord.Embed(title="Ticket",
                                   description="Jste si jistý, že jste zadal správný ID Role")
                await ctx.send(embed=em)

        else:
            em = discord.Embed(title="Ticket",
                               description="Tato role už je v ticketu", color=0x00a8ff)
            await ctx.send(embed=em)

    else:
        em = discord.Embed(title="Ticket", description="Nemáš oprávnění",
                           color=0x00a8ff)
        await ctx.send(embed=em)


@client.command()
async def delpingedrole(ctx, role_id=None):
    with open('data.json') as f:
        data = json.load(f)

    valid_user = False

    for role_id in data["verified-roles"]:
        try:
            if ctx.guild.get_role(role_id) in ctx.author.roles:
                valid_user = True
        except:
            pass

    if valid_user or ctx.author.guild_permissions.administrator:

        try:
            role_id = int(role_id)
            role = ctx.guild.get_role(role_id)

            with open("data.json") as f:
                data = json.load(f)

            pinged_roles = data["pinged-roles"]

            if role_id in pinged_roles:
                index = pinged_roles.index(role_id)

                del pinged_roles[index]

                data["pinged-roles"] = pinged_roles

                with open('data.json', 'w') as f:
                    json.dump(data, f)

                em = discord.Embed(title="Ticket",
                                   description="Byla úspěšně odstraněna `{}` z listu tohoto ticketu".format(
                                       role.name), color=0x00a8ff)
                await ctx.send(embed=em)

            else:
                em = discord.Embed(title="Ticket",
                                   description="Tato role, ale je v ticketu",
                                   color=0x00a8ff)
                await ctx.send(embed=em)

        except:
            em = discord.Embed(title="Ticket",
                               description="Jste si jistý, že jste zadal správný ID Role")
            await ctx.send(embed=em)

    else:
        em = discord.Embed(title="Ticket", description="Nemáš oprávnění",
                           color=0x00a8ff)
        await ctx.send(embed=em)


@client.command()
@commands.has_permissions(administrator=True)
async def addadminrole(ctx, role_id=None):
    try:
        role_id = int(role_id)
        role = ctx.guild.get_role(role_id)

        with open("data.json") as f:
            data = json.load(f)

        data["verified-roles"].append(role_id)

        with open('data.json', 'w') as f:
            json.dump(data, f)

        em = discord.Embed(title="Ticket",
                           description="Byl přidán do `{}` listu na admin úrovni".format(
                               role.name), color=0x00a8ff)
        await ctx.send(embed=em)

    except:
        em = discord.Embed(title="Ticket",
                           description="Jste si jistý, že jste zadal správný ID Role")
        await ctx.send(embed=em)


@client.command()
@commands.has_permissions(administrator=True)
async def deladminrole(ctx, role_id=None):
    try:
        role_id = int(role_id)
        role = ctx.guild.get_role(role_id)

        with open("data.json") as f:
            data = json.load(f)

        admin_roles = data["verified-roles"]

        if role_id in admin_roles:
            index = admin_roles.index(role_id)

            del admin_roles[index]

            data["verified-roles"] = admin_roles

            with open('data.json', 'w') as f:
                json.dump(data, f)

            em = discord.Embed(title="Ticket",
                               description="Byl odstraněn z `{}` vytvořeného ticketu".format(
                                   role.name), color=0x00a8ff)

            await ctx.send(embed=em)

        else:
            em = discord.Embed(title="Ticket",
                               description="Tato role není v ticketu",
                               color=0x00a8ff)
            await ctx.send(embed=em)

    except:
        em = discord.Embed(title="Ticket",
                           description="Zadal si ID role správně")
        await ctx.send(embed=em)




client.run(TOKEN)
