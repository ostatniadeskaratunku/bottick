import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import os
import asyncio
from dotenv import load_dotenv

# Wczytywanie tokenu
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- KONFIGURACJA ---
COLOR = 0x222db4
LOGO = "https://cdn.discordapp.com/attachments/1468939867193872619/1472337480102576301/ostatnia_deska_logo26.png"

# ID Kanałów
CHANNEL_PRICES = 1472372981366915214
CHANNEL_TICKET_CREATE = 1468940303099760744
CHANNEL_LEGIT_CHECK = 1468943349053526040

# ID Ról
ROLE_VERIFIED_ID = 1468941420671926356
ROLE_SUPPORT = [1468941098465366148, 1468941219030765628]
ROLE_CLIENT = 1468941301050511412

# Kategorie Ticketów
TICKET_CATEGORIES = [1468940949139755142, 1468940973169053817, 1468940999375192178]

# --- UI: CENNIK ---
class PriceSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Sprawdzian", emoji="📝"),
            discord.SelectOption(label="Kartkówka", emoji="✏️"),
            discord.SelectOption(label="Dysk zwykły", emoji="📂"),
            discord.SelectOption(label="Dysk premium", emoji="💎"),
            discord.SelectOption(label="Baza zadań", emoji="📚"),
            discord.SelectOption(label="DOSTĘP CAŁODOBOWY do Darmówek (24/7)", emoji="🔓")
        ]
        super().__init__(placeholder="Wybierz produkt, aby zobaczyć cenę...", options=options, custom_id="price_select_persistent")

    async def callback(self, interaction: discord.Interaction):
        prices = {
            "Sprawdzian": "Cena: **20 PLN**",
            "Kartkówka": "Cena: **10 PLN**",
            "Dysk zwykły": "Cena: **80 PLN**",
            "Dysk premium": "Cena: **200 PLN**",
            "Baza zadań": "Cena: **od 40 PLN**",
            "DOSTĘP CAŁODOBOWY do Darmówek (24/7)": "Cena: **25 PLN / msc**"
        }
        selection = self.values[0]
        embed = discord.Embed(title=f"💰 Cennik: {selection}", description=prices[selection], color=COLOR)
        embed.set_footer(text="ᴏsᴛᴀᴛɴɪᴀ ᴅᴇsᴋᴀ ʀᴀᴛᴜɴᴋᴜ", icon_url=LOGO)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PriceView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PriceSelect())

# --- UI: TICKETY ---
class TicketModal(ui.Modal, title="Formularz Zakupu"):
    item = ui.TextInput(label="Jaki produkt chcesz zakupić?", placeholder="np. Sprawdzian, Dysk Premium...", min_length=2)
    amount = ui.TextInput(label="Ilość produktów", placeholder="Wpisz liczbę...", min_length=1)
    payment = ui.TextInput(label="Metoda płatności", placeholder="Blik / PSC")
    coupon = ui.TextInput(label="Kupon rabatowy", placeholder="Wpisz, jeśli posiadasz", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        category = None
        for cat_id in TICKET_CATEGORIES:
            cat = interaction.guild.get_channel(cat_id)
            if cat and len(cat.channels) < 50:
                category = cat
                break
        
        if not category:
            return await interaction.response.send_message("❌ Wszystkie kategorie są pełne!", ephemeral=True)

        ticket_channel = await interaction.guild.create_text_channel(
            name=f"zakup-{interaction.user.name}",
            category=category,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
        )

        embed = discord.Embed(title="🎫 NOWE ZAMÓWIENIE", color=COLOR)
        embed.add_field(name="Użytkownik", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="Produkt", value=self.item.value, inline=True)
        embed.add_field(name="Ilość", value=self.amount.value, inline=True)
        embed.add_field(name="Płatność", value=self.payment.value, inline=True)
        embed.add_field(name="Kupon", value=self.coupon.value or "Brak", inline=True)
        embed.set_footer(text=f"Stworzono: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # Wysyłamy wiadomość z kontrolerem, przekazując ID właściciela ticketa
        await ticket_channel.send(content=f"<@&{ROLE_SUPPORT[0]}>", embed=embed, view=TicketControlView(interaction.user.id))
        await interaction.response.send_message(f"✅ Ticket został stworzony: {ticket_channel.mention}", ephemeral=True)

class TicketControlView(ui.View):
    def __init__(self, owner_id=None):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Sprawdzenie czy użytkownik ma rolę z listy ROLE_SUPPORT
        if any(role.id in ROLE_SUPPORT for role in interaction.user.roles):
            return True
        await interaction.response.send_message("❌ Tylko administracja może to zrobić!", ephemeral=True)
        return False

    @ui.button(label="Przejmij ticket", style=discord.ButtonStyle.success, custom_id="ticket_claim")
    async def claim(self, interaction: discord.Interaction):
        await interaction.response.send_message(f"👋 Ticket przejęty przez: {interaction.user.mention}")

    @ui.button(label="Wezwij użytkownika", style=discord.ButtonStyle.secondary, custom_id="ticket_summon")
    async def summon(self, interaction: discord.Interaction):
        if self.owner_id:
            await interaction.channel.send(f"🔔 <@{self.owner_id}>, prosimy o odpowiedź w celu kontynuacji zakupu!")
        else:
            await interaction.response.send_message("❌ Nie można znaleźć właściciela ticketa.", ephemeral=True)

    @ui.button(label="Odprzejmij", style=discord.ButtonStyle.grey, custom_id="ticket_unclaim")
    async def unclaim(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔓 Ticket jest ponownie wolny.")

    @ui.button(label="Zamknij ticket", style=discord.ButtonStyle.danger, custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔒 Zamykanie... Pamiętaj o wystawieniu Legit Checka na kanale LC!")
        # Małe opóźnienie, żeby wiadomość zdążyła się wyświetlić
        await asyncio.sleep(5)
        await interaction.channel.delete()

class TicketOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Stwórz ticket zakup", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="ticket_open_btn")
    async def open_ticket(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TicketModal())

# --- BOT CLASS ---
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Rejestracja widoków z custom_id dla trwałości (persistent views)
        self.add_view(PriceView())
        self.add_view(TicketOpenView())
        # Uwaga: TicketControlView wymaga owner_id, więc pełna trwałość po restarcie bota 
        # dla starych ticketów wymagałaby bazy danych, ale przyciski będą "żyć" do restartu.
        self.add_view(TicketControlView()) 
        await self.tree.sync()

    async def on_message(self, message):
        # Automatyczne nadawanie roli Klienta po napisaniu +lc na odpowiednim kanale
        if message.channel.id == CHANNEL_LEGIT_CHECK and "+lc" in message.content.lower():
            role_client = message.guild.get_role(ROLE_CLIENT)
            if role_client and role_client not in message.author.roles:
                await message.author.add_roles(role_client)
                await message.add_reaction("✅")
        
        await self.process_commands(message)

bot = MyBot()

# --- KOMENDA SETUP ---
@bot.command()
@commands.has_permissions(administrator=True)
async def setup(ctx):
    await ctx.message.delete()

    # Cennik
    price_ch = bot.get_channel(CHANNEL_PRICES)
    if price_ch:
        await price_ch.purge(limit=10)
        await price_ch.send(embed=discord.Embed(title="💰 CENNIK INTERAKTYWNY", description="Wybierz produkt z listy poniżej:", color=COLOR), view=PriceView())

    # Ticket Create
    ticket_ch = bot.get_channel(CHANNEL_TICKET_CREATE)
    if ticket_ch:
        await ticket_ch.purge(limit=10)
        await ticket_ch.send(embed=discord.Embed(title="🛒 ZAKUPY", description="Kliknij przycisk, aby otworzyć ticket zakupowy.", color=COLOR), view=TicketOpenView())

    await ctx.send("✅ Wszystkie kanały zostały skonfigurowane!", delete_after=5)

bot.run(TOKEN)
