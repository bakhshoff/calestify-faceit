import sys
sys.modules['audioop'] = type(sys)('audioop')

import discord
from discord.ext import commands
import json
import os
import random
from datetime import datetime

# ============================================================
BOT_TOKEN = "MTUxNjE3MzM1OTgwMzY2NjUwMg.G6RWgF.EY8pK9zY-hQfo9uqz6-dsgUniVQSUHeUKfAStQ"
MATCHMAKING_KANAL_ID = 1500580102151340132
NETICE_KANAL_ID = 1500580157600170125
MODERATOR_ROL_ID = 1487596991776034856
# ============================================================

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

XERITELER = [
    "Duel", "Sandstorm", "Bazzar", "Province",
    "Rust", "Agency", "Crossfire", "Infected"
]

RANKLAR = [
    {"ad": "Bronz",  "min": 0,    "max": 999,  "emoji": "🥉"},
    {"ad": "Gümüş",  "min": 1000, "max": 1999, "emoji": "🥈"},
    {"ad": "Qızıl",  "min": 2000, "max": 2999, "emoji": "🥇"},
    {"ad": "Platin", "min": 3000, "max": 3999, "emoji": "💎"},
    {"ad": "Əfsanə", "min": 4000, "max": 99999,"emoji": "👑"},
]

ELO_QALIBIYYƏT  = 25
ELO_MƏĞLUBIYYƏT = -20

queue = []
aktiv_matchlər = {}
DB_FAYL = "oyuncular.json"


def db_yukle():
    if os.path.exists(DB_FAYL):
        with open(DB_FAYL, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def db_saxla(data):
    with open(DB_FAYL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def rank_al(elo):
    for r in RANKLAR:
        if r["min"] <= elo <= r["max"]:
            return r
    return RANKLAR[-1]

def oyuncu_al(discord_id):
    db = db_yukle()
    return db.get(str(discord_id))

def oyuncu_saxla(discord_id, data):
    db = db_yukle()
    db[str(discord_id)] = data
    db_saxla(db)


def queue_embed_yarat():
    embed = discord.Embed(
        title="⚔️ Standoff 2 — 5v5 Matchmaking",
        description="Sıraya qoşulmaq üçün aşağıdakı düyməyə bas!",
        color=0xFF6B00
    )
    embed.add_field(
        name=f"🟢 Sıra — {len(queue)}/10",
        value="\n".join([f"• <@{o['discord_id']}> — {o['elo']} ELO" for o in queue]) or "Hələ heç kim yoxdur.",
        inline=False
    )
    embed.set_footer(text="10 nəfər dolduqda match avtomatik başlayır.")
    return embed


class QueueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Sıraya Qoşul", style=discord.ButtonStyle.success, custom_id="queue_qosul")
    async def qosul(self, interaction: discord.Interaction, button: discord.ui.Button):
        await queue_qosul_handler(interaction)

    @discord.ui.button(label="❌ Sıradan Çıx", style=discord.ButtonStyle.danger, custom_id="queue_cix")
    async def cix(self, interaction: discord.Interaction, button: discord.ui.Button):
        await queue_cix_handler(interaction)


async def queue_qosul_handler(interaction: discord.Interaction):
    global queue
    discord_id = interaction.user.id
    oyuncu = oyuncu_al(discord_id)

    if not oyuncu:
        await interaction.response.send_message(
            "❗ Əvvəlcə qeydiyyatdan keç! `/qeydiyyat oyuncu_adi oyuncu_id` əmrini istifadə et.",
            ephemeral=True
        )
        return

    if any(o["discord_id"] == discord_id for o in queue):
        await interaction.response.send_message("⚠️ Artıq sıradasınız!", ephemeral=True)
        return

    queue.append({
        "discord_id": discord_id,
        "ad": oyuncu["oyuncu_adi"],
        "elo": oyuncu["elo"]
    })

    await interaction.response.send_message(f"✅ Sıraya əlavə olundun! ({len(queue)}/10)", ephemeral=True)

    kanal = bot.get_channel(MATCHMAKING_KANAL_ID)
    if kanal:
        async for msg in kanal.history(limit=20):
            if msg.author == bot.user and msg.embeds:
                await msg.edit(embed=queue_embed_yarat())
                break

    if len(queue) >= 10:
        await match_baslat(kanal)


async def queue_cix_handler(interaction: discord.Interaction):
    global queue
    discord_id = interaction.user.id
    onceki = len(queue)
    queue = [o for o in queue if o["discord_id"] != discord_id]

    if len(queue) < onceki:
        await interaction.response.send_message("✅ Sıradan çıxdın.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Sırada deyilsiniz.", ephemeral=True)

    kanal = bot.get_channel(MATCHMAKING_KANAL_ID)
    if kanal:
        async for msg in kanal.history(limit=20):
            if msg.author == bot.user and msg.embeds:
                await msg.edit(embed=queue_embed_yarat())
                break


async def match_baslat(kanal):
    global queue
    oyuncular = queue[:10]
    queue = queue[10:]

    random.shuffle(oyuncular)
    komanda_a = oyuncular[:5]
    komanda_b = oyuncular[5:]

    kapitan_a = max(komanda_a, key=lambda o: o["elo"])
    kapitan_b = max(komanda_b, key=lambda o: o["elo"])

    xerite = random.choice(XERITELER)
    match_id = f"M{datetime.now().strftime('%d%m%H%M%S')}"

    aktiv_matchlər[match_id] = {
        "komanda_a": komanda_a,
        "komanda_b": komanda_b,
        "kapitan_a": kapitan_a,
        "kapitan_b": kapitan_b,
        "xerite": xerite,
        "bashlama": datetime.now().isoformat()
    }

    def oyuncu_siyahi(komanda, kapitan):
        satirlar = []
        for o in komanda:
            r = rank_al(o["elo"])
            prefix = "👑 " if o["discord_id"] == kapitan["discord_id"] else "• "
            satirlar.append(f"{prefix}<@{o['discord_id']}> — {o['elo']} ELO {r['emoji']}")
        return "\n".join(satirlar)

    embed = discord.Embed(title=f"⚔️ Match Başladı! | {match_id}", color=0x00FF88)
    embed.add_field(name="🗺️ Xəritə", value=xerite, inline=False)
    embed.add_field(name="🔵 Komanda A", value=oyuncu_siyahi(komanda_a, kapitan_a), inline=True)
    embed.add_field(name="🔴 Komanda B", value=oyuncu_siyahi(komanda_b, kapitan_b), inline=True)
    embed.add_field(
        name="👑 Kapitanlar",
        value=f"Komanda A: <@{kapitan_a['discord_id']}>\nKomanda B: <@{kapitan_b['discord_id']}>",
        inline=False
    )
    embed.add_field(
        name="📋 Növbəti addım",
        value="Kapitanlar lobi qurub hamını dəvət etsin.\nMatch bitəndə moderator `/netice` əmrini istifadə etsin.",
        inline=False
    )
    embed.set_footer(text=f"Match ID: {match_id}")

    mention_str = " ".join([f"<@{o['discord_id']}>" for o in oyuncular])
    await kanal.send(content=mention_str, embed=embed)

    async for msg in kanal.history(limit=20):
        if msg.author == bot.user and msg.embeds and "Matchmaking" in msg.embeds[0].title:
            await msg.edit(embed=queue_embed_yarat())
            break


@bot.tree.command(name="qeydiyyat", description="Matchmaking sistemə qeydiyyatdan keç")
async def qeydiyyat(interaction: discord.Interaction, oyuncu_adi: str, oyuncu_id: str):
    discord_id = str(interaction.user.id)
    db = db_yukle()

    if discord_id in db:
        await interaction.response.send_message("⚠️ Artıq qeydiyyatdan keçmisən!", ephemeral=True)
        return

    db[discord_id] = {
        "discord_id": interaction.user.id,
        "oyuncu_adi": oyuncu_adi,
        "oyuncu_id": oyuncu_id,
        "elo": 1000,
        "qalibiyyetler": 0,
        "meglubiyyetler": 0,
        "qeydiyyat_tarixi": datetime.now().isoformat()
    }
    db_saxla(db)

    r = rank_al(1000)
    embed = discord.Embed(title="✅ Qeydiyyat Uğurlu!", color=0x00FF88)
    embed.add_field(name="Oyunçu Adı", value=oyuncu_adi, inline=True)
    embed.add_field(name="Oyunçu ID", value=oyuncu_id, inline=True)
    embed.add_field(name="Başlanğıc ELO", value=f"1000 {r['emoji']} {r['ad']}", inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="stats", description="Oyunçu statistikasına bax")
async def stats(interaction: discord.Interaction, üzv: discord.Member = None):
    hedef = üzv or interaction.user
    oyuncu = oyuncu_al(hedef.id)

    if not oyuncu:
        await interaction.response.send_message("❗ Bu oyunçu qeydiyyatdan keçməyib.", ephemeral=True)
        return

    r = rank_al(oyuncu["elo"])
    umumi = oyuncu["qalibiyyetler"] + oyuncu["meglubiyyetler"]
    winrate = round(oyuncu["qalibiyyetler"] / umumi * 100) if umumi > 0 else 0

    embed = discord.Embed(title=f"{r['emoji']} {oyuncu['oyuncu_adi']} — Statistika", color=0xFF6B00)
    embed.set_thumbnail(url=hedef.display_avatar.url)
    embed.add_field(name="🏆 Rank", value=f"{r['emoji']} {r['ad']}", inline=True)
    embed.add_field(name="📊 ELO", value=str(oyuncu["elo"]), inline=True)
    embed.add_field(name="🎮 Oyunçu ID", value=oyuncu["oyuncu_id"], inline=True)
    embed.add_field(name="✅ Qalibiyyət", value=str(oyuncu["qalibiyyetler"]), inline=True)
    embed.add_field(name="❌ Məğlubiyyət", value=str(oyuncu["meglubiyyetler"]), inline=True)
    embed.add_field(name="📈 Winrate", value=f"{winrate}%", inline=True)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="liderboard", description="Ən yaxşı oyunçuların siyahısı")
async def liderboard(interaction: discord.Interaction):
    db = db_yukle()
    if not db:
        await interaction.response.send_message("Hələ heç kim qeydiyyatdan keçməyib.", ephemeral=True)
        return

    siralama = sorted(db.values(), key=lambda x: x["elo"], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Liderboard — Top 10", color=0xFFD700)
    satirlar = []
    medallar = ["🥇", "🥈", "🥉"]

    for i, o in enumerate(siralama):
        r = rank_al(o["elo"])
        medal = medallar[i] if i < 3 else f"{i+1}."
        satirlar.append(f"{medal} **{o['oyuncu_adi']}** — {o['elo']} ELO {r['emoji']}")

    embed.description = "\n".join(satirlar)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="netice", description="Match nəticəsini daxil et (Moderator)")
async def netice(interaction: discord.Interaction, match_id: str, qalib: str, skor: str):
    mod_rolu = interaction.guild.get_role(MODERATOR_ROL_ID)
    if mod_rolu not in interaction.user.roles:
        await interaction.response.send_message("❌ Bu əmr yalnız moderatorlar üçündür!", ephemeral=True)
        return

    if match_id not in aktiv_matchlər:
        await interaction.response.send_message(f"❌ `{match_id}` ID-li aktiv match tapılmadı.", ephemeral=True)
        return

    match = aktiv_matchlər[match_id]
    qalib = qalib.upper()

    if qalib not in ["A", "B"]:
        await interaction.response.send_message("❌ Qalib 'A' və ya 'B' olmalıdır.", ephemeral=True)
        return

    qalib_komanda  = match["komanda_a"] if qalib == "A" else match["komanda_b"]
    meglub_komanda = match["komanda_b"] if qalib == "A" else match["komanda_a"]

    db = db_yukle()
    for o in qalib_komanda:
        sid = str(o["discord_id"])
        if sid in db:
            db[sid]["elo"] = max(0, db[sid]["elo"] + ELO_QALIBIYYƏT)
            db[sid]["qalibiyyetler"] += 1

    for o in meglub_komanda:
        sid = str(o["discord_id"])
        if sid in db:
            db[sid]["elo"] = max(0, db[sid]["elo"] + ELO_MƏĞLUBIYYƏT)
            db[sid]["meglubiyyetler"] += 1

    db_saxla(db)
    del aktiv_matchlər[match_id]

    def siyahi_yaz(komanda, qalib_mi):
        satirlar = []
        for o in komanda:
            sid = str(o["discord_id"])
            yeni_elo = db[sid]["elo"] if sid in db else o["elo"]
            deyisim = f"+{ELO_QALIBIYYƏT}" if qalib_mi else str(ELO_MƏĞLUBIYYƏT)
            r = rank_al(yeni_elo)
            satirlar.append(f"<@{o['discord_id']}> — {yeni_elo} ELO ({deyisim}) {r['emoji']}")
        return "\n".join(satirlar)

    embed = discord.Embed(title=f"🏁 Match Nəticəsi | {match_id}", color=0x00FF88 if qalib == "A" else 0xFF4444)
    embed.add_field(name="🗺️ Xəritə", value=match["xerite"], inline=True)
    embed.add_field(name="📊 Skor", value=skor, inline=True)
    embed.add_field(name="🔵 Komanda A" + (" 🏆" if qalib == "A" else ""), value=siyahi_yaz(match["komanda_a"], qalib == "A"), inline=False)
    embed.add_field(name="🔴 Komanda B" + (" 🏆" if qalib == "B" else ""), value=siyahi_yaz(match["komanda_b"], qalib == "B"), inline=False)
    embed.set_footer(text=f"Moderator: {interaction.user.name} • {datetime.now().strftime('%d.%m.%Y %H:%M')}")

    netice_kanal = bot.get_channel(NETICE_KANAL_ID)
    if netice_kanal:
        await netice_kanal.send(embed=embed)

    await interaction.response.send_message(f"✅ Match `{match_id}` nəticəsi qeydə alındı!", ephemeral=True)


@bot.tree.command(name="aktiv_matchler", description="Hazırda davam edən matchlər")
async def aktiv_matchler(interaction: discord.Interaction):
    if not aktiv_matchlər:
        await interaction.response.send_message("Hazırda aktiv match yoxdur.", ephemeral=True)
        return

    embed = discord.Embed(title="⚔️ Aktiv Matchlər", color=0xFF6B00)
    for mid, m in aktiv_matchlər.items():
        embed.add_field(name=f"Match {mid}", value=f"Xəritə: {m['xerite']}\nBaşlama: {m['bashlama'][:16]}", inline=False)
    await interaction.response.send_message(embed=embed)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} aktiv oldu!")
    await bot.tree.sync()
    print("✅ Slash komandalar sinxronlaşdı!")

    kanal = bot.get_channel(MATCHMAKING_KANAL_ID)
    if kanal:
        async for msg in kanal.history(limit=50):
            if msg.author == bot.user:
                await msg.delete()
        await kanal.send(embed=queue_embed_yarat(), view=QueueView())
        print(f"✅ Matchmaking mesajı göndərildi!")

    bot.add_view(QueueView())


bot.run(BOT_TOKEN)
