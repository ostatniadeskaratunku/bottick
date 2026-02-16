import discord
from discord.ext import commands
from discord import app_commands, ui
import datetime
import os
import asyncio
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# --- KONFIGURACJA ---
COLOR = 0x222db4
LOGO = "https://cdn.discordapp.com/attachments/1468939867193872619/1472337480102576301/ostatnia_deska_logo26.png"

# ID Kanałów i Ról
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
            discord.SelectOption(label="Sprawdzian", description="Sprawdzian (tzw. gotowiec) od wydawnictwa", emoji="📝"),
            discord.SelectOption(label="Kartkówka", description="Kartkówka - możliwe opcje to: Gotowiec, Baza zadań z generatora).", emoji="✏️"),
            discord.SelectOption(label="Dysk zwykły", description="Dostęp do bazy materiałów edukacyjnych. W dysku znajdziesz same gotowce.", emoji="📂"),
            discord.SelectOption(label="Dysk premium", description="Najszersza baza materiałów do książki: Gotowce, bazy zadań, Klasówki.", emoji="💎"),
            discord.SelectOption(label="Baza zadań", description="Wszystkie dostępne zadania w generatorze do działu/tematu.", emoji="📚"),
            discord.SelectOption(label="DOSTĘP CAŁODOBOWY (24/7)", description="Dostęp do darmówek bez limitu.", emoji="🔓")
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
        
        embed = discord.Embed(title=f"💰 Szczegóły produktu: {selection}", color=COLOR)
        embed.add_field(name="Cena", value=f"**{cena}**", inline=True)
        embed.add_field(name="Opis", value=opis, inline=False)
        embed.set_footer(text="ᴏsᴛᴀᴛɴɪᴀ ᴅᴇsᴋᴀ ʀᴀᴛᴜɴᴋᴜ", icon_url=LOGO)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PriceView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PriceSelect())

# --- UI: TICKETY I FORMULARZE ---
class TicketModal(ui.Modal, title="Formularz Zamówienia"):
    item = ui.TextInput(label="Produkt", placeholder="np. Sprawdzian, Dysk Premium...", min_length=2)
    amount = ui.TextInput(label="Ilość/Zakres", placeholder="Np. 1 sprawdzian, dział 2...", min_length=1)
    payment = ui.TextInput(label="Metoda płatności", placeholder="Blik / PSC / PayPal")
    coupon = ui.TextInput(label="Kupon rabatowy", placeholder="Wpisz kod, jeśli posiadasz", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        category = None
        for cat_id in TICKET_CATEGORIES:
            cat = interaction.guild.get_channel(cat_id)
            if cat and len(cat.channels) < 50:
                category = cat
                break
        
        if not category:
            return await interaction.response.send_message("❌ Przepraszamy, system jest obecnie przeciążony. Spróbuj później.", ephemeral=True)

        ticket_ch = await interaction.guild.create_text_channel(
            name=f"🛒-{interaction.user.name}",
            category=category,
            overwrites={
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
        )

        embed = discord.Embed(title="🎫 NOWE ZAMÓWIENIE", color=COLOR, timestamp=datetime.datetime.now())
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        embed.add_field(name="👤 Klient", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=False)
        embed.add_field(name="📦 Produkt", value=self.item.value, inline=True)
        embed.add_field(name="🔢 Ilość", value=self.amount.value, inline=True)
        embed.add_field(name="💳 Płatność", value=self.payment.value, inline=True)
        embed.add_field(name="🎟️ Kupon", value=self.coupon.value if self.coupon.value else "Brak", inline=True)
        embed.set_footer(text="Czekaj na odpowiedź sprzedawcy...", icon_url=LOGO)

        await ticket_ch.send(content=f"<@&{ROLE_SUPPORT[0]}>", embed=embed, view=TicketControlView(interaction.user.id))
        await interaction.response.send_message(f"✅ Ticket został otwarty: {ticket_ch.mention}", ephemeral=True)

class TicketControlView(ui.View):
    def __init__(self, owner_id=None):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if any(role.id in ROLE_SUPPORT for role in interaction.user.roles):
            return True
        await interaction.response.send_message("❌ Ta akcja jest zarezerwowana dla sprzedawcy.", ephemeral=True)
        return False

    @ui.button(label="Przejmij", style=discord.ButtonStyle.success, custom_id="btn_claim", emoji="🤝")
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        embed = interaction.message.embeds[0]
        embed.set_author(name=f"Obsługa: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"👋 {interaction.user.mention} zajął się Twoim zgłoszeniem!")

    @ui.button(label="Wezwij na PV", style=discord.ButtonStyle.secondary, custom_id="btn_summon", emoji="🔔")
    async def summon(self, interaction: discord.Interaction, button: ui.Button):
        if self.owner_id:
            user = interaction.guild.get_member(self.owner_id)
            if user:
                try:
                    await user.send(f"🔔 Witaj! Sprzedawca czeka na Ciebie w tickecie: {interaction.channel.mention}")
                    await interaction.response.send_message("✅ Wysłano powiadomienie PV.", ephemeral=True)
                except:
                    await interaction.response.send_message("❌ Nie można wysłać PV (użytkownik ma zablokowane wiadomości).", ephemeral=True)

    @ui.button(label="Zamknij + Ranga", style=discord.ButtonStyle.danger, custom_id="btn_close", emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.guild.get_member(self.owner_id)
        role = interaction.guild.get_role(ROLE_CLIENT)
        
        if user:
            # Nadanie rangi
            if role: await user.add_roles(role)
            # Powiadomienie PV
            try:
                dm_embed = discord.Embed(title="🔒 Twój ticket został zamknięty", color=COLOR)
                dm_embed.description = f"Dziękujemy za skorzystanie z usług **Ostatnia Deska Ratunku**!\n\nProsimy o wystawienie opinii na kanale <#{CHANNEL_LEGIT_CHECK}> wpisując:\n`+lc Twoja opinia`"
                dm_embed.set_footer(text="Do zobaczenia ponownie!", icon_url=LOGO)
                await user.send(embed=dm_embed)
            except: pass
            
        await interaction.response.send_message(
            f"✅ <@{self.owner_id}> otrzymał rangę klienta.\n"
            f"Oczekiwanie na opinię na <#{CHANNEL_LEGIT_CHECK}>... Kanał zostanie usunięty po wykryciu `+lc`."
        )

        def check(m):
            return m.channel.id == CHANNEL_LEGIT_CHECK and m.author.id == self.owner_id and "+lc" in m.content.lower()

        try:
            await interaction.client.wait_for('message', check=check, timeout=86400)
            await interaction.channel.send("🚀 Opinia znaleziona! Zamykanie kanału za 5 sekund...")
            await asyncio.sleep(5)
            await interaction.channel.delete()
        except asyncio.TimeoutError:
            await interaction.channel.send("⚠️ Upłynął czas oczekiwania na opinię (24h). Kanał pozostaje otwarty do ręcznego usunięcia.")

class TicketOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Otwórz Ticket Zakupowy", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="ticket_open_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TicketModal())

# --- BOT CLASS ---
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
    
    # Cennik
    p_ch = bot.get_channel(CHANNEL_PRICES)
    if p_ch:
        embed = discord.Embed(title="💰 Ostatnia Deska Ratunku - CENNIK", color=COLOR)
        embed.description = "Wybierz produkt z listy poniżej, aby poznać jego cenę i szczegóły."
        embed.set_image(url=LOGO)
        await p_ch.send(embed=embed, view=PriceView())

    # Zakupy
    t_ch = bot.get_channel(CHANNEL_TICKET_CREATE)
    if t_ch:
        embed = discord.Embed(title="🛒 Sklep - Zakup Materiałów", color=COLOR)
        embed.description = "Kliknij przycisk poniżej, aby wypełnić formularz i otworzyć ticket.\n\n*Nasi sprzedawcy odpowiedzą najszybciej jak to możliwe.*"
        await t_ch.send(embed=embed, view=TicketOpenView())

    await ctx.send("✨ Konfiguracja zakończona pomyślnie!", delete_after=5)

bot.run(TOKEN)
