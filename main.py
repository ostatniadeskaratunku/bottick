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

CHANNEL_PRICES = 1472372981366915214
CHANNEL_TICKET_CREATE = 1468940303099760744
CHANNEL_LEGIT_CHECK = 1468943349053526040

ROLE_SUPPORT = [1468941098465366148, 1468941219030765628]
ROLE_CLIENT = 1468941301050511412
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
            discord.SelectOption(label="DOSTĘP CAŁODOBOWY (24/7)", emoji="🔓")
        ]
        super().__init__(placeholder="Wybierz produkt...", options=options, custom_id="price_select_persistent")

    async def callback(self, interaction: discord.Interaction):
        prices = {
            "Sprawdzian": "20 PLN", "Kartkówka": "10 PLN", "Dysk zwykły": "80 PLN",
            "Dysk premium": "200 PLN", "Baza zadań": "od 40 PLN", "DOSTĘP CAŁODOBOWY (24/7)": "25 PLN / msc"
        }
        selection = self.values[0]
        embed = discord.Embed(title=f"💰 Cennik: {selection}", description=f"Cena: **{prices[selection]}**", color=COLOR)
        embed.set_footer(text="ᴏsᴛᴀᴛɴɪᴀ ᴅᴇsᴋᴀ ʀᴀᴛᴜɴᴋᴜ", icon_url=LOGO)
        await interaction.response.send_message(embed=embed, ephemeral=True)

class PriceView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PriceSelect())

# --- UI: TICKETY ---
class TicketModal(ui.Modal, title="Formularz Zakupu"):
    item = ui.TextInput(label="Produkt", placeholder="np. Sprawdzian...", min_length=2)
    amount = ui.TextInput(label="Ilość", placeholder="Wpisz liczbę...", min_length=1)
    payment = ui.TextInput(label="Płatność", placeholder="Blik / PSC")
    coupon = ui.TextInput(label="Kupon", placeholder="Wpisz, jeśli masz", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        category = None
        for cat_id in TICKET_CATEGORIES:
            cat = interaction.guild.get_channel(cat_id)
            if cat and len(cat.channels) < 50:
                category = cat
                break
        
        if not category:
            return await interaction.response.send_message("❌ Kategorie pełne!", ephemeral=True)

        ticket_ch = await interaction.guild.create_text_channel(
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
        embed.add_field(name="Płatność", value=self.payment.value, inline=True)
        embed.set_footer(text=f"Stworzono: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")

        await ticket_ch.send(content=f"<@&{ROLE_SUPPORT[0]}>", embed=embed, view=TicketControlView(interaction.user.id))
        await interaction.response.send_message(f"✅ Ticket stworzony: {ticket_ch.mention}", ephemeral=True)

class TicketControlView(ui.View):
    def __init__(self, owner_id=None):
        super().__init__(timeout=None)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if any(role.id in ROLE_SUPPORT for role in interaction.user.roles):
            return True
        await interaction.response.send_message("❌ Tylko administracja!", ephemeral=True)
        return False

    @ui.button(label="Przejmij", style=discord.ButtonStyle.success, custom_id="btn_claim")
    async def claim(self, interaction: discord.Interaction, button: ui.Button):
        embed = interaction.message.embeds[0]
        embed.set_author(name=f"Obsługuje: {interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message(f"👋 {interaction.user.mention} przejął ticket.")

    @ui.button(label="Wezwij (PV)", style=discord.ButtonStyle.secondary, custom_id="btn_summon")
    async def summon(self, interaction: discord.Interaction, button: ui.Button):
        if self.owner_id:
            user = interaction.guild.get_member(self.owner_id)
            if user:
                try:
                    await user.send(f"🔔 Personel prosi o odpowiedź w tickecie: {interaction.channel.mention}")
                    await interaction.response.send_message("✅ Wysłano PV.", ephemeral=True)
                except:
                    await interaction.response.send_message("❌ Zamknięte PV!", ephemeral=True)

    @ui.button(label="Odprzejmij", style=discord.ButtonStyle.grey, custom_id="btn_unclaim")
    async def unclaim(self, interaction: discord.Interaction, button: ui.Button):
        embed = interaction.message.embeds[0]
        embed.set_author(name=None)
        await interaction.message.edit(embed=embed)
        await interaction.response.send_message("🔓 Ticket jest wolny.")

    @ui.button(label="Zamknij + Ranga", style=discord.ButtonStyle.danger, custom_id="btn_close")
    async def close(self, interaction: discord.Interaction, button: ui.Button):
        user = interaction.guild.get_member(self.owner_id)
        role = interaction.guild.get_role(ROLE_CLIENT)
        
        # Nadaje rangę od razu
        if user and role:
            await user.add_roles(role)
            
        await interaction.response.send_message(
            f"✅ <@{self.owner_id}>, otrzymałeś rangę **Klienta**!\n"
            f"Ostatni krok: wystaw opinię na <#{CHANNEL_LEGIT_CHECK}> pisząc `+lc opinia`.\n"
            "Bot automatycznie usunie ten kanał po wykryciu Twojego wpisu."
        )

        def check(m):
            return m.channel.id == CHANNEL_LEGIT_CHECK and m.author.id == self.owner_id and "+lc" in m.content.lower()

        try:
            await interaction.client.wait_for('message', check=check, timeout=86400)
            await interaction.channel.send("🚀 Opinia wystawiona! Usuwam kanał za 5s...")
            await asyncio.sleep(5)
            await interaction.channel.delete()
        except asyncio.TimeoutError:
            await interaction.channel.send("⚠️ Czas na LC minął (24h).")

class TicketOpenView(ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @ui.button(label="Stwórz ticket", style=discord.ButtonStyle.primary, emoji="🛒", custom_id="ticket_open_btn")
    async def open_ticket(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(TicketModal())

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
    p_ch = bot.get_channel(CHANNEL_PRICES)
    if p_ch:
        await p_ch.send(embed=discord.Embed(title="💰 CENNIK", color=COLOR), view=PriceView())
    t_ch = bot.get_channel(CHANNEL_TICKET_CREATE)
    if t_ch:
        await t_ch.send(embed=discord.Embed(title="🛒 ZAKUPY", color=COLOR), view=TicketOpenView())
    await ctx.send("✅ Gotowe!", delete_after=5)

bot.run(TOKEN)
