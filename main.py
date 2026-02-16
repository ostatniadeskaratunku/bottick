import discord
from discord.ext import commands
from discord import ui
import datetime
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- KONFIGURACJA ---
COLOR = 0x222db4
LOGO = "https://cdn.discordapp.com/attachments/1468939867193872619/1472337480102576301/ostatnia_deska_logo26.png"

CHANNEL_PRICES = 1472372981366915214
CHANNEL_TICKET_CREATE = 1468940303099760744
CHANNEL_LEGIT_CHECK = 1468943349053526040
ROLE_SUPPORT = [1468941098465366148, 1468941219030765628]
ROLE_CLIENT = 1468941301050511412
TICKET_CATEGORIES = [1468940949139755142, 1468940973169053817, 1468940999375192178]

# --- UI: CENNIK Z OPISAMI ---
class PriceSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Sprawdzian", description="Otwórz cennik: Sprawdzian", emoji="📝"),
            discord.SelectOption(label="Kartkówka", description="Otwórz cennik: Kartkówka", emoji="✏️"),
            discord.SelectOption(label="Dysk zwykły", description="Otwórz cennik: Dysk zwykły", emoji="📂"),
            discord.SelectOption(label="Dysk premium", description="Otwórz cennik: Dysk premium", emoji="💎"),
            discord.SelectOption(label="Baza zadań", description="Otwórz cennik: Baza zadań", emoji="📚"),
            discord.SelectOption(label="DOSTĘP CAŁODOBOWY (24/7)", description="Otwórz cennik: Dostęp do darmówek całodobowy (24/7)", emoji="🔓")
        ]
        super().__init__(placeholder="Wybierz produkt, aby zobaczyć szczegóły...", options=options, custom_id="price_select_persistent")

    async def callback(self, interaction: discord.Interaction):
        prices = {
            "Sprawdzian": ("20 PLN", "Sprawdzian (tzw. gotowiec) od wydawnictwa"),
            "Kartkówka": ("10 PLN", "Kartkówka - możliwe opcje to: Gotowiec, Baza zadań z generatora)."),
            "Dysk zwykły": ("80 PLN", "Dostęp do bazy materiałów edukacyjnych. W dysku znajdziesz same gotowce."),
            "Dysk premium": ("200 PLN", "Najszersza baza materiałów do książki: Gotowce, bazy zadań, Klasówki."),
            "Baza zadań": ("od 40 PLN", "Wszystkie dostępne zadania w generatorze do działu/tematu."),
            "DOSTĘP CAŁODOBOWY (24/7)": ("25 PLN / msc", "Dostęp do darmówek bez limitu.")
        }
        selection = self.values[0]
        cena, opis = prices[selection]
        embed = discord.Embed(title=f"💰 Produkt: {selection}", color=COLOR)
        embed.add_field(name="Cena", value=f"**{cena}**", inline=True)
        embed.add_field(name="Opis", value=opis, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PriceView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PriceSelect())

# --- UI: TICKETY ---
class TicketModal(ui.Modal, title="Formularz Zamówienia"):
    item = ui.TextInput(label="Produkt", placeholder="np. Sprawdzian...", min_length=2)
    amount = ui.TextInput(label="Ilość/Zakres", placeholder="Np. 1 sprawdzian...", min_length=1)
    payment = ui.TextInput(label="Metoda płatności", placeholder="Blik lub PSC")
    coupon = ui.TextInput(label="Kupon rabatowy", placeholder="Wpisz kod JEŚLI go posiadasz", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        category = discord.utils.get(interaction.guild.categories, id=TICKET_CATEGORIES[0])
        ticket_ch = await interaction.guild.create_text_channel(
            name=f"🛒-{interaction.user.name}",
            category=category,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
        )
        embed = discord.Embed(title="🎫 NOWE ZAMÓWIENIE", color=COLOR)
        embed.add_field(name="👤 Klient", value=f"{interaction.user.mention}", inline=False)
        embed.add_field(name="📦 Produkt", value=self.item.value, inline=True)
        embed.add_field(name="🔢 Ilość", value=self.amount.value, inline=True)
        embed.add_field(name="💳 Płatność", value=self.payment.value, inline=True)
        embed.add_field(name="🎟️ Kupon", value=self.coupon.value if self.coupon.value else "Brak", inline=True)
        
        await ticket_ch.send(content=f"<@&{ROLE_SUPPORT[0]}>", embed=embed, view=TicketControlView(interaction.user.id))
        await interaction.response.send_message(f"✅ Ticket otwarty: {ticket_ch.mention}", ephemeral=True)

class TicketControlView(ui.View):
    def __init__(self, owner_id=None):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    @ui.button(label="Przejmij", style=discord.ButtonStyle.success, custom_id="btn_claim", emoji="🤝")
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        embed = interaction.message.embeds[0]
        embed.set_author(name=f"Obsługa: {interaction.user.display_name}")
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"👋 {interaction.user.mention} przejął ticket.")

    @ui.button(label="Wezwij (PV)", style=discord.ButtonStyle.secondary, custom_id="btn_summon", emoji="🔔")
    async def summon(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.guild.get_member(self.owner_id)
        if user:
            try:
                await user.send(f"🔔 Personel czeka na Ciebie w tickecie: {interaction.channel.mention}")
                await interaction.response.send_message("✅ Wysłano powiadomienie PV.", ephemeral=True)
            except:
                await interaction.response.send_message("❌ Zablokowane PV!", ephemeral=True)

    @ui.button(label="Zamknij + Ranga", style=discord.ButtonStyle.danger, custom_id="btn_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.guild.get_member(self.owner_id)
        role = interaction.guild.get_role(ROLE_CLIENT)
        if user and role:
            await user.add_roles(role)
        
        # Wyślij instrukcję na kanał i na PV
        msg = (f"✅ <@{self.owner_id}>, ranga Klienta została nadana!\n"
               f"Ostatni krok: wystaw opinię na <#{CHANNEL_LEGIT_CHECK}> wpisując `+lc TWOJA OPINIA`.\n"
               "Gdy to zrobisz, ten kanał zostanie automatycznie usunięty.")
        
        await interaction.response.send_message(msg)
        try:
            embed_dm = discord.Embed(title="🔒 Twój ticket został zakończony", description=msg, color=COLOR)
            await user.send(embed=embed_dm)
        except: pass

class TicketOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Otwórz Ticket Zakupowy", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="ticket_open_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- BOT MAIN ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(PriceView())
        self.add_view(TicketOpenView())
        self.add_view(TicketControlView())
        await self.tree.sync()

    async def on_message(self, message):
        if message.author.bot: return

        # LOGIKA AUTOMATYCZNEGO KASOWANIA TICKETA PO +LC
        if message.channel.id == CHANNEL_LEGIT_CHECK and "+lc" in message.content.lower():
            # Szukamy kanału ticketu tego użytkownika
            # Nazwa kanału to zakup-nazwa lub 🛒-nazwa
            search_name = f"🛒-{message.author.name}".lower()
            for channel in message.guild.text_channels:
                if channel.name.lower() == search_name:
                    await channel.send("🚀 Opinia wystawiona! Usuwam kanał za 10 sekund...")
                    await asyncio.sleep(10)
                    await channel.delete()
                    break
        
        await self.process_commands(message)

bot = MyBot()

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()
    p_ch = bot.get_channel(CHANNEL_PRICES)
    if p_ch:
        await p_ch.send(embed=discord.Embed(title="💰 CENNIK", color=COLOR), view=PriceView())
    t_ch = bot.get_channel(CHANNEL_TICKET_CREATE)
    if t_ch:
        await t_ch.send(embed=discord.Embed(title="🛒 ZAKUPY", color=COLOR), view=TicketOpenView())
    await ctx.send("✅ Gotowe!", delete_after=5)

bot.run(TOKEN)
