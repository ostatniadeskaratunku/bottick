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
CHANNEL_PRICES = 1472372981366915214
CHANNEL_TICKET_CREATE = 1468940303099760744 # Zakupy
CHANNEL_SUPPORT_CREATE = 1468940212204732492 # Pomoc
CHANNEL_LEGIT_CHECK = 1468943349053526040

ROLE_SUPPORT = [1468941098465366148, 1468941219030765628]
ROLE_CLIENT = 1468941301050511412

CAT_SHOP = 1468940949139755142
CAT_HELP = 1468940274955976786

# --- UI: CENNIK ---
class PriceSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Sprawdzian", description="20 PLN", emoji="📝"),
            discord.SelectOption(label="Kartkówka", description="10 PLN", emoji="✏️"),
            discord.SelectOption(label="Dysk zwykły", description="80 PLN", emoji="📂"),
            discord.SelectOption(label="Dysk premium", description="200 PLN", emoji="💎"),
            discord.SelectOption(label="Baza zadań", description="od 40 PLN", emoji="📚"),
            discord.SelectOption(label="DOSTĘP CAŁODOBOWY (24/7)", description="25 PLN / msc", emoji="🔓")
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

# --- UI: MODAL ZAMÓWIENIA ---
class TicketModal(ui.Modal, title="Formularz Zamówienia"):
    item = ui.TextInput(label="Produkt", placeholder="np. Sprawdzian...", min_length=2)
    amount = ui.TextInput(label="Ilość/Zakres", placeholder="Np. 1 sprawdzian...", min_length=1)
    payment = ui.TextInput(label="Metoda płatności", placeholder="Blik lub PSC")
    coupon = ui.TextInput(label="Kupon rabatowy", placeholder="Wpisz kod JEŚLI go posiadasz", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        category = interaction.guild.get_channel(CAT_SHOP)
        ticket_ch = await interaction.guild.create_text_channel(
            name=f"🛒-{interaction.user.name}",
            category=category,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
        )
        embed = discord.Embed(title="🎫 NOWE ZAMÓWIENIE", color=COLOR)
        embed.add_field(name="👤 Klient", value=interaction.user.mention, inline=False)
        embed.add_field(name="📦 Produkt", value=self.item.value, inline=True)
        embed.add_field(name="🔢 Ilość", value=self.amount.value, inline=True)
        embed.add_field(name="💳 Płatność", value=self.payment.value, inline=True)
        embed.add_field(name="🎟️ Kupon", value=self.coupon.value or "Brak", inline=True)
        
        await ticket_ch.send(content=f"<@&{ROLE_SUPPORT[0]}>", embed=embed, view=TicketControlView(interaction.user.id))
        await interaction.response.send_message(f"✅ Ticket otwarty: {ticket_ch.mention}", ephemeral=True)

# --- UI: KONTROLA TICKETA ---
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

    @ui.button(label="Zamknij (5h)", style=discord.ButtonStyle.danger, custom_id="btn_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        # Jeśli owner_id nie jest przekazany (po restarcie), próbujemy go wyciągnąć z embeda
        if not self.owner_id:
            try:
                self.owner_id = int(interaction.message.embeds[0].fields[0].value.replace('<@', '').replace('>', '').replace('!', ''))
            except:
                return await interaction.response.send_message("❌ Błąd identyfikacji właściciela.", ephemeral=True)

        user = interaction.guild.get_member(self.owner_id)
        role = interaction.guild.get_role(ROLE_CLIENT)
        
        if user and role:
            await user.add_roles(role)

        msg_text = (f"✅ **Dziękujemy za zakupy!**\n\n"
                   f"Ranga <@&{ROLE_CLIENT}> została nadana.\n"
                   f"Będziemy wdzięczni za opinię na kanale <#{CHANNEL_LEGIT_CHECK}>.\n"
                   f"**Ten kanał zostanie automatycznie usunięty za 5 godzin.**")

        embed_info = discord.Embed(title="🔒 Ticket Zamknięty", description=msg_text, color=discord.Color.red())
        
        await interaction.response.send_message(embed=embed_info)
        
        if user:
            try: await user.send(embed=embed_info)
            except: pass

        # Logika usuwania po 5 godzinach (18000 sekund)
        await asyncio.sleep(18000)
        try:
            await interaction.channel.delete()
        except:
            pass

# --- UI: OTWIERANIE ---
class TicketOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Otwórz Ticket Zakupowy", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="t_shop")
    async def open_shop(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TicketModal())

    @ui.button(label="Pomoc / Pytanie", style=discord.ButtonStyle.secondary, emoji="🆘", custom_id="t_help")
    async def open_help(self, interaction: discord.Interaction, button: ui.Button):
        category = interaction.guild.get_channel(CAT_HELP)
        ticket_ch = await interaction.guild.create_text_channel(
            name=f"🆘-{interaction.user.name}",
            category=category,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
        )
        embed = discord.Embed(title="🆘 POMOC / PYTANIE", description=f"Witaj {interaction.user.mention}, opisz w czym możemy Ci pomóc.", color=COLOR)
        await ticket_ch.send(content=f"<@&{ROLE_SUPPORT[0]}>", embed=embed, view=TicketControlView(interaction.user.id))
        await interaction.response.send_message(f"✅ Ticket pomocy otwarty: {ticket_ch.mention}", ephemeral=True)

# --- BOT MAIN ---
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(PriceView())
        self.add_view(TicketOpenView())
        self.add_view(TicketControlView())
        await self.tree.sync()

bot = MyBot()

@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()
    
    # Kanał Cennik
    p_ch = bot.get_channel(CHANNEL_PRICES)
    if p_ch:
        await p_ch.send(embed=discord.Embed(title="💰 CENNIK USŁUG", description="Wybierz produkt z listy poniżej, aby poznać szczegóły.", color=COLOR), view=PriceView())
    
    # Kanał Zakupy
    t_ch = bot.get_channel(CHANNEL_TICKET_CREATE)
    if t_ch:
        await t_ch.send(embed=discord.Embed(title="🛒 ZAKUPY", description="Kliknij przycisk poniżej, aby wypełnić formularz zamówienia.", color=COLOR), view=TicketOpenView())

    # Kanał Pomoc
    h_ch = bot.get_channel(CHANNEL_SUPPORT_CREATE)
    if h_ch:
        await h_ch.send(embed=discord.Embed(title="🆘 CENTRUM POMOCY", description="Masz pytanie? Potrzebujesz wsparcia? Otwórz ticket.", color=COLOR), view=TicketOpenView())

    await ctx.send("✅ Systemy zostały zainicjowane pomyślnie.", delete_after=5)

bot.run(TOKEN)
