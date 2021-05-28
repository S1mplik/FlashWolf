import discord
from discord.ext import commands
import psutil


class Info(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()

    async def on_ready(self):
        print('info.py načteno úspěšně')

    @commands.command(aliases=['python', 'botinfo'])
    async def bot(self, ctx):
        values = psutil.virtual_memory()
        val2 = values.available * 0.001
        val3 = val2 * 0.001
        val4 = val3 * 0.001

        values2 = psutil.virtual_memory()
        value21 = values2.total
        values22 = value21 * 0.001
        values23 = values22 * 0.001
        values24 = values23 * 0.001

        embedve = discord.Embed(
            title="Bot Informace", description="", color=0x9370DB)
        embedve.add_field(
            name="Odezva", value=f"Bot odezva - {round(self.client.latency * 1000)}ms", inline=False)
        embedve.add_field(name="Běží na:", value="Python 3.9", inline=False)
        embedve.add_field(name='Hostingové statistiky', value=f'Využití procesoru- {psutil.cpu_percent(1)}%'
                          f'\n(Skutečné využití CPU se může lišit)'
                          f'\n'

                          f'\nPočet jader procesoru - {psutil.cpu_count()} '
                          f'\nPočet fyzických jader procesoru- {psutil.cpu_count(logical=False)}'
                          f'\n'

                          f'\nCelková počet RAM- {round(values24, 2)} GB'
                          f'\nK dispozici RAM - {round(val4, 2)} GB')


        await ctx.send(embed=embedve)

def setup(client):
    client.add_cog(Info(client))
