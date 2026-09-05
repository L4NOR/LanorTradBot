"""
Recrutement scantrad — de la candidature au rôle
==================================================
Un membre clique sur le poste visé → formulaire (expérience, dispos,
portfolio, motivation) → un **thread de candidature** est créé côté staff
avec le test technique, et deux boutons : **Accepter** (attribue le rôle
automatiquement) ou **Refuser** (avec motif).

  /recrutement_panel — (admin) pose le panneau dans #recrutement
  /postuler          — ouvre le formulaire directement
  /candidatures      — (staff) liste les candidatures en cours

Postes et rôles attribués : RECRUIT_POSTS dans bot_config.py.
"""
import logging
import time

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import (
    GUILD_ID, CHANNELS, ROLES,
    COLOR_NEUTRAL, COLOR_SUCCESS, COLOR_ERROR, COLOR_WARNING,
    RECRUIT_POSTS, RECRUIT_TEST_FORUM, RECRUIT_FALLBACK,
    RECRUIT_STAFF_ROLE, RECRUIT_TEST_DELAY, RECRUIT_OPEN,
)
from bot.embeds import brand_embed
from bot.storage import JSONStore

log = logging.getLogger("lanortrad.recruit")

GUILD = discord.Object(id=GUILD_ID) if GUILD_ID else None

_POSTS = {key: (label, emoji, role_key, desc)
          for key, label, emoji, role_key, desc in RECRUIT_POSTS}

# thread_id → {"user", "post", "ts", "status"}
_store = JSONStore("recruit.json", default={"apps": {}})


def _apps() -> dict:
    return _store.setdefault("apps", {})


def _open_app_of(user_id: int):
    for tid, app in _apps().items():
        if app.get("user") == user_id and app.get("status") == "open":
            return tid, app
    return None, None


# ═══════════════════════════════════════════════════════
# Formulaire de candidature
# ═══════════════════════════════════════════════════════

class ApplicationModal(discord.ui.Modal):
    def __init__(self, post_key: str):
        label, emoji, _, _ = _POSTS[post_key]
        super().__init__(title=f"{emoji} Candidature · {label}"[:45])
        self.post_key = post_key

        self.experience = discord.ui.TextInput(
            label="Ton expérience",
            style=discord.TextStyle.paragraph,
            placeholder="Teams précédentes, années de pratique, logiciels maîtrisés…",
            max_length=700, required=True,
        )
        self.availability = discord.ui.TextInput(
            label="Tes disponibilités",
            placeholder="ex : 4-6 h par semaine, surtout le week-end",
            max_length=200, required=True,
        )
        self.portfolio = discord.ui.TextInput(
            label="Portfolio / exemples (liens)",
            placeholder="Drive, Imgur, MangaDex… (facultatif)",
            max_length=400, required=False,
        )
        self.motivation = discord.ui.TextInput(
            label="Pourquoi LanorTrad ?",
            style=discord.TextStyle.paragraph,
            max_length=500, required=False,
        )
        for item in (self.experience, self.availability, self.portfolio, self.motivation):
            self.add_item(item)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        cog = interaction.client.get_cog("Recruit")
        if cog is None:
            await interaction.followup.send("❌ Module recrutement indisponible.", ephemeral=True)
            return
        await cog.create_application(interaction, self.post_key, {
            "experience": str(self.experience),
            "availability": str(self.availability),
            "portfolio": str(self.portfolio) or "—",
            "motivation": str(self.motivation) or "—",
        })


class PostSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=label, value=key, emoji=emoji, description=desc[:100])
            for key, label, emoji, role_key, desc in RECRUIT_POSTS
        ]
        super().__init__(
            placeholder="Choisis le poste visé…",
            min_values=1, max_values=1, options=options,
            custom_id="lanorbot:recruit_select",
        )

    async def callback(self, interaction: discord.Interaction):
        if not RECRUIT_OPEN:
            await interaction.response.send_message(
                "🚪 Les candidatures sont **fermées** pour le moment. Reviens bientôt !",
                ephemeral=True)
            return
        tid, _ = _open_app_of(interaction.user.id)
        if tid:
            await interaction.response.send_message(
                "⚠️ Tu as déjà une candidature en cours — le staff te répondra dans son thread.",
                ephemeral=True)
            return
        await interaction.response.send_modal(ApplicationModal(self.values[0]))


class RecruitPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(PostSelect())


# ═══════════════════════════════════════════════════════
# Décision du staff
# ═══════════════════════════════════════════════════════

class RefuseModal(discord.ui.Modal, title="Refuser la candidature"):
    reason = discord.ui.TextInput(
        label="Motif (envoyé au candidat)",
        style=discord.TextStyle.paragraph,
        placeholder="Sois constructif : ce qui manque, et s'il peut retenter plus tard.",
        max_length=600, required=True,
    )

    async def on_submit(self, interaction: discord.Interaction):
        cog = interaction.client.get_cog("Recruit")
        await cog.decide(interaction, accepted=False, reason=str(self.reason))


class DecisionView(discord.ui.View):
    """Boutons persistants Accepter / Refuser dans le thread de candidature."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="✅ Accepter", style=discord.ButtonStyle.success,
                       custom_id="lanorbot:recruit_accept")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "🚫 Réservé au staff.", ephemeral=True)
            return
        await interaction.response.defer()
        cog = interaction.client.get_cog("Recruit")
        await cog.decide(interaction, accepted=True, reason=None)

    @discord.ui.button(label="❌ Refuser", style=discord.ButtonStyle.danger,
                       custom_id="lanorbot:recruit_refuse")
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("🚫 Réservé au staff.", ephemeral=True)
            return
        await interaction.response.send_modal(RefuseModal())


# ═══════════════════════════════════════════════════════
# Cog
# ═══════════════════════════════════════════════════════

class Recruit(commands.Cog):
    """Candidatures scantrad."""

    def __init__(self, bot):
        self.bot = bot
        self.bot.add_view(RecruitPanelView())
        self.bot.add_view(DecisionView())

    # ─────────────────────────────────────────────
    async def _target_channel(self, guild):
        for key in (RECRUIT_TEST_FORUM, RECRUIT_FALLBACK, "staff_chat", "tickets"):
            ch_id = CHANNELS.get(key)
            if ch_id:
                ch = guild.get_channel(ch_id)
                if ch is not None:
                    return ch
        return None

    async def create_application(self, interaction: discord.Interaction,
                                 post_key: str, answers: dict):
        guild = interaction.guild
        label, emoji, role_key, _ = _POSTS[post_key]
        channel = await self._target_channel(guild)
        if channel is None:
            await interaction.followup.send(
                "❌ Aucun salon de candidature configuré — préviens un admin.", ephemeral=True)
            return

        deadline = int(time.time()) + RECRUIT_TEST_DELAY * 3600
        joined = interaction.user.joined_at
        description = (
            f"**Candidat·e :** {interaction.user.mention} (`{interaction.user.id}`)\n"
            f"**Compte créé :** <t:{int(interaction.user.created_at.timestamp())}:R>"
        )
        if joined:
            description += f"\n**Sur le serveur depuis :** <t:{int(joined.timestamp())}:R>"

        embed = brand_embed(
            guild,
            title=f"{emoji} Candidature · {label}",
            description=description,
            color=COLOR_NEUTRAL,
        )
        embed.add_field(name="🧪 Expérience", value=answers["experience"][:1024], inline=False)
        embed.add_field(name="🕒 Disponibilités", value=answers["availability"][:1024], inline=False)
        embed.add_field(name="🔗 Portfolio", value=answers["portfolio"][:1024], inline=False)
        embed.add_field(name="💬 Motivation", value=answers["motivation"][:1024], inline=False)
        embed.add_field(
            name="⏳ Test technique",
            value=f"À rendre avant <t:{deadline}:F> (<t:{deadline}:R>)",
            inline=False,
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        ping = ""
        if RECRUIT_STAFF_ROLE and ROLES.get(RECRUIT_STAFF_ROLE):
            ping = f"<@&{ROLES[RECRUIT_STAFF_ROLE]}>"

        thread = None
        try:
            if isinstance(channel, discord.ForumChannel):
                tags = [t for t in channel.available_tags
                        if t.name.lower().startswith(label.lower()[:4])]
                created = await channel.create_thread(
                    name=f"{emoji} {label} · {interaction.user.display_name}"[:100],
                    content=f"{ping} nouvelle candidature de {interaction.user.mention}".strip(),
                    embed=embed,
                    view=DecisionView(),
                    applied_tags=tags[:5],
                    allowed_mentions=discord.AllowedMentions(roles=True, users=True),
                )
                thread = created.thread
            else:
                thread = await channel.create_thread(
                    name=f"{emoji} {label} · {interaction.user.display_name}"[:100],
                    type=discord.ChannelType.private_thread,
                    invitable=False,
                )
                await thread.send(
                    content=f"{ping} nouvelle candidature de {interaction.user.mention}".strip(),
                    embed=embed, view=DecisionView(),
                    allowed_mentions=discord.AllowedMentions(roles=True, users=True),
                )
        except discord.Forbidden:
            await interaction.followup.send(
                "❌ Je n'ai pas la permission de créer le thread de candidature.", ephemeral=True)
            return
        except discord.HTTPException as e:
            log.error("Création candidature KO : %s", e)
            await interaction.followup.send(
                "❌ Création de la candidature impossible.", ephemeral=True)
            return

        _apps()[str(thread.id)] = {
            "user": interaction.user.id,
            "post": post_key,
            "ts": int(time.time()),
            "deadline": deadline,
            "status": "open",
        }
        _store.save()

        try:
            await interaction.user.send(
                f"{emoji} **Candidature reçue — {label}**\n\n"
                f"Merci ! Le staff LanorTrad va l'étudier et t'enverra un **test technique**.\n"
                f"Tu as **{RECRUIT_TEST_DELAY} h** pour le rendre une fois reçu.\n\n"
                "Tu recevras la réponse ici même. 🩸"
            )
        except discord.HTTPException:
            pass

        await interaction.followup.send(
            "✅ Candidature envoyée ! Le staff te répondra en MP.", ephemeral=True)
        log.info("Candidature %s de %s", post_key, interaction.user)

    # ─────────────────────────────────────────────
    async def decide(self, interaction: discord.Interaction, *, accepted: bool, reason):
        thread = interaction.channel
        app = _apps().get(str(getattr(thread, "id", 0)))
        if app is None:
            msg = "❌ Cette candidature n'est plus suivie (thread inconnu)."
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
            return

        member = interaction.guild.get_member(app["user"])
        label, emoji, role_key, _ = _POSTS.get(app["post"], ("?", "📋", None, ""))
        app["status"] = "accepted" if accepted else "refused"
        app["decided_by"] = interaction.user.id
        _store.save()

        role_note = ""
        if accepted and member and role_key and ROLES.get(role_key):
            role = interaction.guild.get_role(ROLES[role_key])
            if role:
                try:
                    await member.add_roles(role, reason=f"Candidature {label} acceptée")
                    role_note = f"\n🎭 Rôle attribué : {role.mention}"
                except discord.HTTPException as e:
                    role_note = f"\n⚠️ Rôle non attribué : {e}"

        embed = brand_embed(
            interaction.guild,
            title="✅ Candidature acceptée" if accepted else "❌ Candidature refusée",
            description=(
                f"**Poste :** {emoji} {label}\n"
                f"**Candidat·e :** {member.mention if member else app['user']}\n"
                f"**Décision par :** {interaction.user.mention}"
                + (f"\n**Motif :** {reason}" if reason else "")
                + role_note
            ),
            color=COLOR_SUCCESS if accepted else COLOR_ERROR,
        )
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed)
        else:
            await interaction.response.send_message(embed=embed)

        if member:
            try:
                if accepted:
                    await member.send(
                        f"🎉 **Bienvenue dans la team LanorTrad !**\n\n"
                        f"Ta candidature au poste **{emoji} {label}** est **acceptée**.\n"
                        "Tu as maintenant accès à l'atelier scantrad — passe dire bonjour "
                        "dans le salon de l'atelier, on t'expliquera le pipeline. 🩸"
                    )
                else:
                    await member.send(
                        f"📋 **Candidature — {emoji} {label}**\n\n"
                        f"Elle n'est **pas retenue** cette fois.\n\n"
                        f"**Retour du staff :** {reason}\n\n"
                        "Tu peux retenter plus tard — ça n'a rien de définitif. 🩸"
                    )
            except discord.HTTPException:
                pass

        try:
            await thread.edit(archived=True, locked=True)
        except discord.HTTPException:
            pass

    # ─────────────────────────────────────────────
    # Commandes
    # ─────────────────────────────────────────────
    @app_commands.command(name="recrutement_panel",
                          description="(Admin) Pose le panneau de candidature")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guilds(GUILD)
    async def recrutement_panel(self, interaction: discord.Interaction):
        postes = "\n".join(
            f"{emoji} **{label}** — {desc}"
            for key, label, emoji, role_key, desc in RECRUIT_POSTS
        )
        embed = brand_embed(
            interaction.guild,
            title="📋 Rejoindre la team LanorTrad",
            description=(
                ("On recrute ! Choisis ton poste dans le menu ci-dessous.\n"
                 if RECRUIT_OPEN else
                 "🚪 **Candidatures actuellement fermées.**\n")
                + "\n" + postes +
                "\n\n**Comment ça se passe :**\n"
                "1️⃣ Tu remplis le formulaire (2 min)\n"
                "2️⃣ Le staff t'envoie un **test technique**\n"
                f"3️⃣ Tu as **{RECRUIT_TEST_DELAY} h** pour le rendre\n"
                "4️⃣ Retour + période d'essai sur 1-2 chapitres\n\n"
                "*Aucune expérience obligatoire pour Clean et QC — on forme.*"
            ),
            color=COLOR_NEUTRAL,
        )
        await interaction.channel.send(embed=embed, view=RecruitPanelView())
        await interaction.response.send_message("✅ Panneau recrutement posté.", ephemeral=True)

    @app_commands.command(name="postuler", description="Postuler pour rejoindre la team scantrad")
    @app_commands.guilds(GUILD)
    async def postuler(self, interaction: discord.Interaction):
        if not RECRUIT_OPEN:
            await interaction.response.send_message(
                "🚪 Les candidatures sont fermées pour le moment.", ephemeral=True)
            return
        tid, _ = _open_app_of(interaction.user.id)
        if tid:
            await interaction.response.send_message(
                "⚠️ Tu as déjà une candidature en cours.", ephemeral=True)
            return
        embed = brand_embed(
            interaction.guild,
            title="📋 Quel poste vises-tu ?",
            description="\n".join(
                f"{emoji} **{label}** — {desc}"
                for key, label, emoji, role_key, desc in RECRUIT_POSTS
            ),
            color=COLOR_NEUTRAL,
        )
        await interaction.response.send_message(
            embed=embed, view=RecruitPanelView(), ephemeral=True)

    @app_commands.command(name="candidatures",
                          description="(Staff) Liste les candidatures en cours")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.guilds(GUILD)
    async def candidatures(self, interaction: discord.Interaction):
        opened = [(tid, a) for tid, a in _apps().items() if a.get("status") == "open"]
        if not opened:
            await interaction.response.send_message(
                "📭 Aucune candidature en cours.", ephemeral=True)
            return

        lines = []
        for tid, a in sorted(opened, key=lambda kv: kv[1].get("ts", 0)):
            label, emoji, _, _ = _POSTS.get(a["post"], ("?", "📋", None, ""))
            deadline = a.get("deadline", 0)
            when = "⏰ délai dépassé" if deadline < time.time() else f"échéance <t:{deadline}:R>"
            lines.append(f"{emoji} **{label}** — <@{a['user']}> · <#{tid}> · {when}")

        embed = brand_embed(
            interaction.guild,
            title="📋 Candidatures en cours",
            description="\n".join(lines),
            color=COLOR_WARNING,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Recruit(bot))
