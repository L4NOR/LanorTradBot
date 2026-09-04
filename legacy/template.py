# template.py
# ═══════════════════════════════════════════════════════════════════════════════
# COMMANDE !template — Crée la nouvelle structure du serveur (catégories,
# channels, rôles) en mode "soft" : ne supprime rien, idempotent, ré-exécutable.
# ═══════════════════════════════════════════════════════════════════════════════

import os
import json
import logging
from datetime import datetime, timezone

import discord
from discord.ext import commands

from config import ADMIN_ROLES, COLORS, MANGA_EMOJIS, DATA_DIR
from utils import safe_api_call


# ─── Spec du template ────────────────────────────────────────────────────────

ONGOING_MANGAS = ["Tougen Anki", "Catenaccio", "Ao No Exorcist"]
TRANSLATING_MANGAS = ["Satsudou", "Tokyo Underworld"]
ALL_MANGAS = ONGOING_MANGAS + TRANSLATING_MANGAS

LANG_SPEC = {
    "fr": {
        "lang_role_name": "🇫🇷 Français",
        "lang_role_color": 0x3B5BA5,
        "spoilers_role_name": "🇫🇷 Spoilers FR",
        "spoilers_role_color": 0x922B21,
        "category_name": "🇫🇷 ・ MANGAS FR",
        "label": "FR",
    },
    "en": {
        "lang_role_name": "🇬🇧 English",
        "lang_role_color": 0xC8102E,
        "spoilers_role_name": "🇬🇧 Spoilers EN",
        "spoilers_role_color": 0x6E2C00,
        "category_name": "🇬🇧 ・ MANGAS EN",
        "label": "EN",
    },
}

TEMPLATE_IDS_FILE = os.path.join(DATA_DIR, "template_ids.json")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def slugify_manga(name: str) -> str:
    base = name.lower().replace(" ", "-").replace("_", "-")
    return "".join(c for c in base if c.isalnum() or c == "-")


async def get_or_create_role(guild: discord.Guild, name: str, color: int):
    existing = discord.utils.get(guild.roles, name=name)
    if existing:
        return existing, False
    role = await safe_api_call(
        guild.create_role,
        name=name,
        color=discord.Color(color),
        mentionable=True,
        reason="!template",
    )
    return role, True


async def get_or_create_category(guild: discord.Guild, name: str, overwrites):
    existing = discord.utils.get(guild.categories, name=name)
    if existing:
        await safe_api_call(existing.edit, overwrites=overwrites, reason="!template (sync perms)")
        return existing, False
    cat = await safe_api_call(
        guild.create_category,
        name=name,
        overwrites=overwrites,
        reason="!template",
    )
    return cat, True


async def get_or_create_text_channel(guild, name, category, overwrites=None, topic=None):
    existing = discord.utils.find(
        lambda c: c.name == name and c.category_id == (category.id if category else None),
        guild.text_channels,
    )
    if existing:
        if overwrites is not None:
            await safe_api_call(existing.edit, overwrites=overwrites, reason="!template (sync perms)")
        return existing, False
    kwargs = {"name": name, "category": category, "reason": "!template"}
    if overwrites is not None:
        kwargs["overwrites"] = overwrites
    if topic:
        kwargs["topic"] = topic
    chan = await safe_api_call(guild.create_text_channel, **kwargs)
    return chan, True


def admin_overwrites(guild: discord.Guild):
    """Permission overwrites pour donner accès aux rôles admin + au bot."""
    out = {
        guild.me: discord.PermissionOverwrite(
            view_channel=True, send_messages=True, manage_channels=True, manage_messages=True
        )
    }
    for rid in ADMIN_ROLES:
        ar = guild.get_role(rid)
        if ar:
            out[ar] = discord.PermissionOverwrite(
                view_channel=True, send_messages=True, manage_messages=True
            )
    return out


# ─── Vue de confirmation ─────────────────────────────────────────────────────

class ConfirmView(discord.ui.View):
    def __init__(self, author_id: int):
        super().__init__(timeout=120)
        self.author_id = author_id
        self.value: bool | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Seul l'auteur de la commande peut confirmer.", ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="✅ Confirmer", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="❌ Annuler", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.value = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(view=self)
        self.stop()


# ─── Setup ───────────────────────────────────────────────────────────────────

def setup(bot: commands.Bot):

    @bot.command(name="template")
    @commands.has_any_role(*ADMIN_ROLES)
    async def template_cmd(ctx: commands.Context):
        """Crée la structure franco-anglaise du serveur (rôles + catégories + channels)."""
        guild = ctx.guild
        if guild is None:
            await ctx.send("Commande utilisable uniquement en serveur.")
            return

        # Aperçu
        plan_lines = ["**Rôles créés s'ils n'existent pas :**"]
        for spec in LANG_SPEC.values():
            plan_lines.append(f"• `{spec['lang_role_name']}`")
            plan_lines.append(f"• `{spec['spoilers_role_name']}`")
        plan_lines.append("")

        for lang_key, spec in LANG_SPEC.items():
            plan_lines.append(f"**Catégorie `{spec['category_name']}` :**")
            for manga in ALL_MANGAS:
                emoji = MANGA_EMOJIS.get(manga, "📖")
                badge = "🔥" if manga in ONGOING_MANGAS else "✅"
                plan_lines.append(f"  • `{badge}{emoji}-{slugify_manga(manga)}`")
            for manga in ONGOING_MANGAS:
                plan_lines.append(f"  • `👀-spoiler-{slugify_manga(manga)}` (réservé `{spec['spoilers_role_name']}`)")
            plan_lines.append("")

        embed = discord.Embed(
            title="🛠️ Template — Aperçu de la structure",
            description=(
                "Cette commande va **créer** rôles + catégories + channels "
                "**sans rien supprimer** (idempotent : ré-exécutable sans risque).\n\n"
                "🔥 = manga en cours JP · ✅ = fini JP / trad FR en cours\n\n"
                + "\n".join(plan_lines)
                + "\n*Channels admin/staff existants : non touchés.*"
            ),
            color=COLORS["info"],
        )
        embed.set_footer(text="Confirme dans les 120 secondes.")

        view = ConfirmView(ctx.author.id)
        msg = await ctx.send(embed=embed, view=view)
        await view.wait()

        if view.value is None:
            await msg.edit(content="⏱️ Confirmation expirée — template annulé.", embed=None, view=None)
            return
        if view.value is False:
            await msg.edit(content="❌ Template annulé.", embed=None, view=None)
            return

        progress = await ctx.send("⏳ Création en cours…")

        created_roles: dict[str, int] = {}
        created_categories: dict[str, int] = {}
        created_channels: dict[str, int] = {}
        existing_count = 0

        try:
            # 1. Rôles (langue + spoilers par langue)
            roles = {}
            for lang_key, spec in LANG_SPEC.items():
                lang_role, was_new = await get_or_create_role(
                    guild, spec["lang_role_name"], spec["lang_role_color"]
                )
                if was_new:
                    created_roles[f"{lang_key}_lang"] = lang_role.id
                else:
                    existing_count += 1

                spoilers_role, was_new = await get_or_create_role(
                    guild, spec["spoilers_role_name"], spec["spoilers_role_color"]
                )
                if was_new:
                    created_roles[f"{lang_key}_spoilers"] = spoilers_role.id
                else:
                    existing_count += 1

                roles[lang_key] = {"lang": lang_role, "spoilers": spoilers_role}

            # 2. Catégories + channels
            for lang_key, spec in LANG_SPEC.items():
                lang_role = roles[lang_key]["lang"]
                spoilers_role = roles[lang_key]["spoilers"]

                cat_overwrites = admin_overwrites(guild)
                cat_overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                cat_overwrites[lang_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    add_reactions=True, attach_files=True, embed_links=True,
                )

                category, was_new = await get_or_create_category(
                    guild, spec["category_name"], cat_overwrites
                )
                if was_new:
                    created_categories[lang_key] = category.id
                else:
                    existing_count += 1

                # Chat channels (tous les mangas)
                for manga in ALL_MANGAS:
                    slug = slugify_manga(manga)
                    emoji = MANGA_EMOJIS.get(manga, "📖")
                    badge = "🔥" if manga in ONGOING_MANGAS else "✅"
                    chan_name = f"{badge}{emoji}-{slug}"
                    topic = (
                        f"[{spec['label']}] {manga} — "
                        + ("manga en cours JP." if manga in ONGOING_MANGAS
                           else "fini JP, traduction FR en cours.")
                    )
                    chan, was_new = await get_or_create_text_channel(
                        guild, chan_name, category, topic=topic
                    )
                    if was_new:
                        created_channels[f"{lang_key}_{slug}_chat"] = chan.id
                    else:
                        existing_count += 1

                # Spoiler channels (mangas en cours uniquement)
                # Permissions: cachée au lang_role (override deny), visible au spoilers_role
                spoiler_overwrites = admin_overwrites(guild)
                spoiler_overwrites[guild.default_role] = discord.PermissionOverwrite(view_channel=False)
                spoiler_overwrites[lang_role] = discord.PermissionOverwrite(view_channel=False)
                spoiler_overwrites[spoilers_role] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, read_message_history=True,
                    add_reactions=True, attach_files=True, embed_links=True,
                )

                for manga in ONGOING_MANGAS:
                    slug = slugify_manga(manga)
                    chan_name = f"👀-spoiler-{slug}"
                    topic = (
                        f"[{spec['label']}] SPOILERS — propose tes traductions pour {manga}. "
                        f"Réservé aux membres avec le rôle « {spec['spoilers_role_name']} »."
                    )
                    chan, was_new = await get_or_create_text_channel(
                        guild, chan_name, category, overwrites=spoiler_overwrites, topic=topic
                    )
                    if was_new:
                        created_channels[f"{lang_key}_{slug}_spoiler"] = chan.id
                    else:
                        existing_count += 1

            # 3. Sauvegarde des IDs
            os.makedirs(DATA_DIR, exist_ok=True)
            snapshot = {
                "guild_id": guild.id,
                "applied_at": datetime.now(timezone.utc).isoformat(),
                "applied_by": ctx.author.id,
                "roles": {
                    lang_key: {
                        "lang": roles[lang_key]["lang"].id,
                        "spoilers": roles[lang_key]["spoilers"].id,
                    }
                    for lang_key in LANG_SPEC
                },
                "categories": {
                    lang_key: discord.utils.get(guild.categories, name=LANG_SPEC[lang_key]["category_name"]).id
                    for lang_key in LANG_SPEC
                },
                "channels_created_this_run": created_channels,
            }
            try:
                with open(TEMPLATE_IDS_FILE, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, indent=2, ensure_ascii=False)
            except OSError as e:
                logging.error(f"[template] Impossible d'écrire {TEMPLATE_IDS_FILE} : {e}")

        except discord.Forbidden:
            await progress.edit(content="❌ Permissions insuffisantes — le bot a besoin de **Manage Channels** et **Manage Roles**.")
            return
        except Exception as e:
            logging.exception("[template] Erreur lors de l'exécution")
            await progress.edit(content=f"❌ Erreur pendant l'exécution : `{e}`")
            return

        # 4. Récap
        total_new = len(created_roles) + len(created_categories) + len(created_channels)
        recap = discord.Embed(
            title="✅ Template appliqué",
            description=(
                f"**{total_new}** éléments créés · **{existing_count}** déjà existants (réutilisés/synchronisés)."
            ),
            color=COLORS["success"],
        )
        if created_roles:
            recap.add_field(
                name="🆕 Rôles",
                value="\n".join(f"<@&{rid}>" for rid in created_roles.values()),
                inline=False,
            )
        if created_categories:
            recap.add_field(
                name="🆕 Catégories",
                value="\n".join(f"<#{cid}>" for cid in created_categories.values()),
                inline=False,
            )
        if created_channels:
            mentions = [f"<#{cid}>" for cid in list(created_channels.values())[:25]]
            extra = "" if len(created_channels) <= 25 else f"\n… et {len(created_channels)-25} de plus"
            recap.add_field(name="🆕 Channels", value="\n".join(mentions) + extra, inline=False)
        recap.add_field(
            name="📁 IDs sauvegardés",
            value=f"`{TEMPLATE_IDS_FILE}`\nQuand tu seras prêt à basculer, recopie ces IDs dans `config.py`.",
            inline=False,
        )
        recap.set_footer(text="Channels admin/staff non touchés. Ré-exécute la commande pour synchroniser les permissions.")
        await progress.edit(content=None, embed=recap)
