class AutoEmoji(Command):
    server_only = True
    name = ["NQN", "Emojis"]
    min_level = 0
    description = "Causes all failed emojis starting and ending with : to be deleted and reposted with a webhook, when possible."
    usage = "(enable|disable)?"
    flags = "aed"
    directions = [b'\xe2\x8f\xab', b'\xf0\x9f\x94\xbc', b'\xf0\x9f\x94\xbd', b'\xe2\x8f\xac', b'\xf0\x9f\x94\x84']
    dirnames = ["First", "Prev", "Next", "Last", "Refresh"]
    rate_limit = 1

    async def __call__(self, bot, flags, guild, message, user, name, perm, **void):
        data = bot.data.autoemojis
        if flags and perm < 3:
            reason = "to modify autoemoji for " + guild.name
            raise self.perm_error(perm, 3, reason)
        if "e" in flags or "a" in flags:
            data[guild.id] = True
            return italics(css_md(f"Enabled automatic emoji substitution for {sqr_md(guild)}."))
        elif "d" in flags:
            data.pop(guild.id, None)
            return italics(css_md(f"Disabled automatic emoji substitution for {sqr_md(guild)}."))
        buttons = [cdict(emoji=dirn, name=name, custom_id=dirn) for dirn, name in zip(map(as_str, self.directions), self.dirnames)]
        await send_with_reply(
            None,
            message,
            "*```" + "\n" * ("z" in flags) + "callback-admin-autoemoji-"
            + str(user.id) + "_0"
            + "-\nLoading AutoEmoji database...```*",
            buttons=buttons,
        )
    
    async def _callback_(self, bot, message, reaction, user, perm, vals, **void):
        u_id, pos = list(map(int, vals.split("_", 1)))
        if reaction not in (None, self.directions[-1]) and u_id != user.id and perm < 3:
            return
        if reaction not in self.directions and reaction is not None:
            return
        guild = message.guild
        user = await bot.fetch_user(u_id)
        data = bot.data.autoemojis
        curr = {f":{e.name}:": f"({e.id})` {min_emoji(e)}" for e in sorted(guild.emojis, key=lambda e: full_prune(e.name)) if e.is_usable()}
        page = 16
        last = max(0, len(curr) - page)
        if reaction is not None:
            i = self.directions.index(reaction)
            if i == 0:
                new = 0
            elif i == 1:
                new = max(0, pos - page)
            elif i == 2:
                new = min(last, pos + page)
            elif i == 3:
                new = last
            else:
                new = pos
            pos = new
        content = message.content
        if not content:
            content = message.embeds[0].description
        i = content.index("callback")
        content = "```" + "\n" * ("\n" in content[:i]) + (
            "callback-admin-autoemoji-"
            + str(u_id) + "_" + str(pos)
            + "-\n"
        )
        if guild.id in data:
            content += f"Automatic emoji substitution is currently enabled in {sqr_md(guild)}.```"
        else:
            content += f'Automatic emoji substitution is currently disabled in {sqr_md(guild)}. Use "{bot.get_prefix(guild)}autoemoji enable" to enable.```'
        if not curr:
            msg = italics(code_md(f"No custom emojis found for {str(message.guild).replace('`', '')}."))
        else:
            msg = italics(code_md(f"{len(curr)} custom emojis currently assigned for {str(message.guild).replace('`', '')}:")) + "\n" + iter2str({k + " " * (32 - len(k)): curr[k] for k in tuple(curr)[pos:pos + page]}, left="`", right="")
        colour = await self.bot.get_colour(guild)
        emb = discord.Embed(
            description=msg,
            colour=colour,
        )
        emb.set_author(**get_author(user))
        more = len(curr) - pos - page
        if more > 0:
            emb.set_footer(text=f"{uni_str('And', 1)} {more} {uni_str('more...', 1)}")
        create_task(message.edit(content=content, embed=emb))
        if hasattr(message, "int_token"):
            await bot.ignore_interaction(message)


class UpdateAutoEmojis(Database):
    name = "autoemojis"

    def guild_emoji_map(self, guild, emojis={}):
        for e in sorted(guild.emojis, key=lambda e: e.id):
            if not e.is_usable():
                continue
            n = e.name
            while n in emojis:
                if emojis[n] == e.id:
                    break
                t = n.rsplit("-", 1)
                if t[-1].isnumeric():
                    n = t[0] + "-" + str(int(t[-1]) + 1)
                else:
                    n = t[0] + "-1"
            emojis[n] = e
        return emojis

    async def _nocommand_(self, message, recursive=True, edit=False, **void):
        if edit or not message.content or getattr(message, "webhook_id", None) or message.content.count("```") > 1:
            return
        emojis = find_emojis(message.content)
        for e in emojis:
            name, e_id = e.split(":")[1:]
            e_id = int("".join(regexp("[0-9]+").findall(e_id)))
            animated = self.bot.cache.emojis.get(name)
            if not animated:
                animated = await create_future(self.bot.is_animated, e_id, verify=True)
            else:
                name = animated.name
            if animated is not None and not message.webhook_id:
                orig = self.bot.data.emojilists.setdefault(message.author.id, {})
                orig[name] = e_id
                self.bot.data.emojilists.update(message.author.id)
        if not message.guild or message.guild.id not in self.data:
            return
        m_id = None
        msg = message.content
        guild = message.guild
        orig = self.bot.data.emojilists.get(message.author.id, {})
        emojis = None
        if msg.startswith("+"):
            emi = msg[1:].strip()
            spl = emi.rsplit(None, 1)
            if len(spl) > 1:
                ems, m_id = spl
                if not m_id.isnumeric():
                    spl = [emi]
            if len(spl) == 1:
                ems = spl[0]
                m2 = await self.bot.history(message.channel, limit=1, before=message.id).__anext__()
            else:
                m2 = None
                if m_id:
                    m_id = int(m_id)
            if not m2 and m_id:
                try:
                    m2 = await self.bot.fetch_message(m_id, message.channel)
                except LookupError:
                    m2 = None
            if m2:
                futs = deque()
                ems = regexp("<a?:[A-Za-z0-9\\-~_]{1,32}").sub("", ems.replace(" ", "").replace("\\", "")).replace(">", ":")
                possible = (n.strip(":") for n in regexp(":[A-Za-z0-9\\-~_]{1,32}:|[^\\x00-\\x7F]").findall(ems))
                for name in (n for n in possible if n):
                    emoji = None
                    if emojis is None:
                        emojis = self.guild_emoji_map(guild, dict(orig))
                    if ord(name[0]) >= 128:
                        emoji = name
                    else:
                        emoji = emojis.get(name)
                    if not emoji:
                        r1 = regexp("^[A-Za-z0-9\\-~_]{1,32}$")
                        if r1.fullmatch(name):
                            if name.isnumeric():
                                emoji = int(name)
                            else:
                                t = name[::-1].replace("~", "-", 1)[::-1].rsplit("-", 1)
                                if t[-1].isnumeric():
                                    i = int(t[-1])
                                    if i < 1000:
                                        if not emoji:
                                            name = t[0]
                                            emoji = emojis.get(name)
                                        while i > 1 and not emoji:
                                            i -= 1
                                            name = t[0] + "-" + str(i)
                                            emoji = emojis.get(name)
                    if emoji:
                        if type(emoji) is int:
                            e_id = emoji
                            emoji = self.bot.cache.emojis.get(e_id)
                        futs.append(create_task(m2.add_reaction(emoji)))
                if futs:
                    futs.append(create_task(self.bot.silent_delete(message)))
                    for fut in futs:
                        await fut
                    return
        if message.content.count(":") < 2:
            return
        regex = regexp("(?:^|^[^<\\\\`]|[^<][^\\\\`]|.[^a\\\\`])(:[A-Za-z0-9\\-~_]{1,32}:)(?:(?![^0-9]).)*(?:$|[^0-9>`])")
        pops = set()
        offs = 0
        while offs < len(msg):
            matched = regex.search(msg[offs:])
            if not matched:
                break
            substitutes = None
            s = matched.group()
            start = matched.start()
            while s and not regexp(":[A-Za-z0-9\\-~_]").fullmatch(s[:2]):
                s = s[1:]
                start += 1
            while s and not regexp("[A-Za-z0-9\\-~_]:").fullmatch(s[-2:]):
                s = s[:-1]
            offs = start = offs + start
            offs += len(s)
            if not s:
                continue
            name = s[1:-1]
            if emojis is None:
                emojis = self.guild_emoji_map(guild, dict(orig))
            emoji = emojis.get(name)
            if not emoji:
                if name.isnumeric():
                    emoji = int(name)
                else:
                    t = name[::-1].replace("~", "-", 1)[::-1].rsplit("-", 1)
                    if t[-1].isnumeric():
                        i = int(t[-1])
                        if i < 1000:
                            if not emoji:
                                name = t[0]
                                emoji = emojis.get(name)
                            while i > 1 and not emoji:
                                i -= 1
                                name = t[0] + "-" + str(i)
                                emoji = emojis.get(name)
            if type(emoji) is int:
                e_id = emoji
                emoji = self.bot.cache.emojis.get(e_id)
                if not emoji:
                    animated = await create_future(self.bot.is_animated, e_id, verify=True)
                    if animated is not None:
                        emoji = cdict(id=e_id, animated=animated)
                if not emoji and not message.webhook_id:
                    self.bot.data.emojilists.get(message.author.id, {}).pop(name, None)
                    self.bot.data.emojilists.update(message.author.id)
            if emoji:
                pops.add((str(name), emoji.id))
                if len(msg) < 1936:
                    sub = "<"
                    if emoji.animated:
                        sub += "a"
                    name = getattr(emoji, "name", None) or "_"
                    sub += f":{name}:{emoji.id}>"
                else:
                    sub = min_emoji(emoji)
                substitutes = (start, sub, start + len(s))
                if getattr(emoji, "name", None):
                    if not message.webhook_id:
                        orig = self.bot.data.emojilists.setdefault(message.author.id, {})
                        orig.setdefault(name, emoji.id)
                        self.bot.data.emojilists.update(message.author.id)
            if substitutes:
                msg = msg[:substitutes[0]] + substitutes[1] + msg[substitutes[2]:]
        if not msg or msg == message.content:
            return
        msg = escape_everyone(msg).strip("\u200b")
        if not msg or msg == message.content or len(msg) > 2000:
            return
        if not recursive:
            return msg
        files = deque()
        for a in message.attachments:
            b = await self.bot.get_request(a.url, full=False)
            files.append(CompatFile(seq(b), filename=a.filename))
        create_task(self.bot.silent_delete(message))
        url = await self.bot.get_proxy_url(message.author)
        m = await self.bot.send_as_webhook(message.channel, msg, files=files, username=message.author.display_name, avatar_url=url)
        if recursive and regex.search(m.content):
            for k in tuple(pops):
                if str(k[1]) not in m.content:
                    orig.pop(k[0], None)
                else:
                    pops.discard(k)
            if pops:
                print("Removed emojis:", pops)
                msg = await self._nocommand_(message, recursive=False)
                if msg and msg != m.content:
                    create_task(self.bot.silent_delete(m))
                    await self.bot.send_as_webhook(message.channel, msg, files=files, username=message.author.display_name, avatar_url=url)


class EmojiList(Command):
    description = "Sets a custom alias for an emoji, usable by ~autoemoji."
    usage = "(add|delete)? <name>? <id>?"
    flags = "aed"
    no_parse = True
    directions = [b'\xe2\x8f\xab', b'\xf0\x9f\x94\xbc', b'\xf0\x9f\x94\xbd', b'\xe2\x8f\xac', b'\xf0\x9f\x94\x84']
    dirnames = ["First", "Prev", "Next", "Last", "Refresh"]

    async def __call__(self, bot, flags, message, user, name, argv, args, **void):
        data = bot.data.emojilists
        if "d" in flags:
            try:
                e_id = bot.data.emojilists[user.id].pop(args[0])
            except KeyError:
                raise KeyError(f'Emoji name "{args[0]}" not found.')
            return italics(css_md(f"Successfully removed emoji alias {sqr_md(args[0])}: {sqr_md(e_id)} for {sqr_md(user)}."))
        elif argv:
            try:
                name, e_id = argv.rsplit(None, 1)
            except ValueError:
                raise ArgumentError("Please input alias followed by emoji, separated by a space.")
            name = name.strip(":")
            if not regexp("[A-Za-z0-9\\-~_]{1,32}").fullmatch(name):
                raise ArgumentError("Emoji aliases may only contain 1~32 alphanumeric characters, dashes, tildes and underscores.")
            e_id = e_id.rsplit(":", 1)[-1].rstrip(">").strip(":")
            if not e_id.isnumeric():
                raise ArgumentError("Only custom emojis are supported.")
            e_id = int(e_id)
            animated = await create_future(bot.is_animated, e_id, verify=True)
            if animated is None:
                raise LookupError(f"Emoji {e_id} does not exist.")
            bot.data.emojilists.setdefault(user.id, {})[name] = e_id
            bot.data.emojilists.update(user.id)
            return ini_md(f"Successfully added emoji alias {sqr_md(name)}: {sqr_md(e_id)} for {sqr_md(user)}.")
        buttons = [cdict(emoji=dirn, name=name, custom_id=dirn) for dirn, name in zip(map(as_str, self.directions), self.dirnames)]
        await send_with_reply(
            None,
            message,
            "*```" + "\n" * ("z" in flags) + "callback-fun-emojilist-"
            + str(user.id) + "_0"
            + "-\nLoading EmojiList database...```*",
            buttons=buttons,
        )
    
    async def _callback_(self, bot, message, reaction, user, perm, vals, **void):
        u_id, pos = list(map(int, vals.split("_", 1)))
        if reaction not in (None, self.directions[-1]) and u_id != user.id and perm <= inf:
            return
        if reaction not in self.directions and reaction is not None:
            return
        guild = message.guild
        user = await bot.fetch_user(u_id)
        following = bot.data.emojilists
        items = following.get(user.id, {}).items()
        page = 16
        last = max(0, len(items) - page)
        if reaction is not None:
            i = self.directions.index(reaction)
            if i == 0:
                new = 0
            elif i == 1:
                new = max(0, pos - page)
            elif i == 2:
                new = min(last, pos + page)
            elif i == 3:
                new = last
            else:
                new = pos
            pos = new
        curr = {}
        for k, v in sorted(items, key=lambda n: full_prune(n[0]))[pos:pos + page]:
            try:
                try:
                    e = bot.cache.emojis[v]
                    if not e.is_usable():
                        raise LookupError
                    me = " " + str(e)
                except KeyError:
                    await bot.min_emoji(v)
                    me = ""
            except LookupError:
                following[user.id].pop(k)
                following.update(user.id)
                continue
            curr[f":{k}:"] = f"({v})` {me}"
        content = message.content
        if not content:
            content = message.embeds[0].description
        i = content.index("callback")
        content = "*```" + "\n" * ("\n" in content[:i]) + (
            "callback-fun-emojilist-"
            + str(u_id) + "_" + str(pos)
            + "-\n"
        )
        if not items:
            content += f"No currently assigned emoji aliases for {str(user).replace('`', '')}.```*"
            msg = ""
        else:
            content += f"{len(items)} emoji aliases currently assigned for {str(user).replace('`', '')}:```*"
            key = lambda x: "\n" + ", ".join(x)
            msg = iter2str({k + " " * (32 - len(k)): curr[k] for k in curr}, left="`", right="")
        colour = await self.bot.get_colour(user)
        emb = discord.Embed(
            description=content + msg,
            colour=colour,
        )
        emb.set_author(**get_author(user))
        more = len(curr) - pos - page
        if more > 0:
            emb.set_footer(text=f"{uni_str('And', 1)} {more} {uni_str('more...', 1)}")
        create_task(message.edit(content=None, embed=emb, allowed_mentions=discord.AllowedMentions.none()))
        if hasattr(message, "int_token"):
            await bot.ignore_interaction(message)


class UpdateEmojiLists(Database):
    name = "emojilists"


class MimicConfig(Command):
    name = ["PluralConfig", "RPConfig"]
    description = "Modifies an existing webhook mimic's attributes."
    usage = "<0:mimic_id> (prefix|name|avatar|description|gender|birthday)? <1:new>?"
    no_parse = True
    rate_limit = 1

    async def __call__(self, bot, user, message, perm, flags, args, **void):
        update = bot.data.mimics.update
        mimicdb = bot.data.mimics
        mimics = set_dict(mimicdb, user.id, {})
        prefix = args.pop(0)
        perm = bot.get_perms(user.id)
        try:
            mlist = mimics[prefix]
            if mlist is None:
                raise KeyError
            mimlist = [bot.get_mimic(verify_id(p)) for p in mlist]
        except KeyError:
            mimic = bot.get_mimic(verify_id(prefix))
            mimlist = [mimic]
        try:
            opt = args.pop(0).casefold()
        except IndexError:
            opt = None
        if opt in ("name", "username", "nickname", "tag"):
            setting = "name"
        elif opt in ("avatar", "icon", "url", "pfp", "image", "img"):
            setting = "url"
        elif opt in ("status", "description"):
            setting = "description"
        elif opt in ("gender", "birthday", "prefix"):
            setting = opt
        elif opt in ("auto", "copy", "user", "auto", "user-id", "user_id"):
            setting = "user"
        elif is_url(opt):
            args = [opt]
            setting = "url"
        elif opt:
            raise TypeError("Invalid target attribute.")
        if args:
            new = " ".join(args)
        else:
            new = None
        output = ""
        noret = False
        for mimic in mimlist:
            await bot.data.mimics.update_mimic(mimic, message.guild)
            if mimic.u_id != user.id and not isnan(perm):
                raise PermissionError(f"Target mimic {mimic.name} does not belong to you.")
            args.extend(best_url(a) for a in message.attachments)
            if new is None:
                if not opt:
                    emb = await bot.commands.info[0].getMimicData(mimic, "v")
                    bot.send_as_embeds(message.channel, emb)
                    noret = True
                else:
                    output += f"Current {setting} for {sqr_md(mimic.name)}: {sqr_md(mimic[setting])}.\n"
                continue
            m_id = mimic.id
            if setting == "birthday":
                new = utc_ts(tzparse(new))
            # This limit is actually to comply with webhook usernames
            elif setting == "name":
                if len(new) > 80:
                    raise OverflowError("Name must be 80 or fewer in length.")
            # Prefixes must not be too long
            elif setting == "prefix":
                if len(new) > 16:
                    raise OverflowError("Prefix must be 16 or fewer in length.")
                for prefix in mimics:
                    with suppress(ValueError, IndexError):
                        mimics[prefix].remove(m_id)
                if new in mimics:
                    mimics[new].append(m_id)
                else:
                    mimics[new] = [m_id]
            elif setting == "url":
                urls = await bot.follow_url(new, best=True)
                new = urls[0]
            # May assign a user to the mimic
            elif setting == "user":
                if new.casefold() in ("none", "null", "0", "false", "f"):
                    new = None
                else:
                    mim = None
                    try:
                        mim = verify_id(new)
                        user = await bot.fetch_user(mim)
                        if user is None:
                            raise EOFError
                        new = user.id
                    except:
                        try:
                            mimi = bot.get_mimic(mim, user)
                            new = mimi.id
                        except:
                            raise LookupError("Target user or mimic ID not found.")
            elif setting != "description":
                if len(new) > 512:
                    raise OverflowError("Must be 512 or fewer in length.")
            name = mimic.name
            mimic[setting] = new
            update(m_id)
            update(user.id)
        if noret:
            return
        if output:
            return ini_md(output.rstrip())
        return css_md(f"Changed {setting} for {sqr_md(', '.join(m.name for m in mimlist))} to {sqr_md(new)}.")


class Mimic(Command):
    name = ["RolePlay", "Plural", "RP", "RPCreate"]
    description = "Spawns a webhook mimic with an optional username and icon URL, or lists all mimics with their respective prefixes. Mimics require permission level of 1 to invoke."
    usage = "<0:prefix>? <1:user|name>? <2:url[]>? <delete{?d}>?"
    flags = "aedzf"
    no_parse = True
    directions = [b'\xe2\x8f\xab', b'\xf0\x9f\x94\xbc', b'\xf0\x9f\x94\xbd', b'\xe2\x8f\xac', b'\xf0\x9f\x94\x84']
    dirnames = ["First", "Prev", "Next", "Last", "Refresh"]
    rate_limit = (1, 2)

    async def __call__(self, bot, message, user, perm, flags, args, argv, **void):
        update = self.data.mimics.update
        mimicdb = bot.data.mimics
        args.extend(best_url(a) for a in reversed(message.attachments))
        if len(args) == 1 and "d" not in flags:
            user = await bot.fetch_user(verify_id(argv))
        mimics = set_dict(mimicdb, user.id, {})
        if not argv or (len(args) == 1 and "d" not in flags):
            if "d" in flags:
                # This deletes all mimics for the current user
                if "f" not in flags and len(mimics) > 1:
                    return css_md(sqr_md(f"WARNING: {len(mimics)} MIMICS TARGETED. REPEAT COMMAND WITH ?F FLAG TO CONFIRM."), force=True)
                mimicdb.pop(user.id)
                return italics(css_md(f"Successfully removed all {sqr_md(len(mimics))} webhook mimics for {sqr_md(user)}."))
            # Set callback message for scrollable list
            buttons = [cdict(emoji=dirn, name=name, custom_id=dirn) for dirn, name in zip(map(as_str, self.directions), self.dirnames)]
            await send_with_reply(
                None,
                message,
                "*```" + "\n" * ("z" in flags) + "callback-fun-mimic-"
                + str(user.id) + "_0"
                + "-\nLoading Mimic database...```*",
                buttons=buttons,
            )
            return
        u_id = user.id
        prefix = args.pop(0)
        if "d" in flags:
            try:
                mlist = mimics[prefix]
                if mlist is None:
                    raise KeyError
                if len(mlist):
                    m_id = mlist.pop(0)
                    mimic = mimicdb.pop(m_id)
                else:
                    mimics.pop(prefix)
                    update(user.id)
                    raise KeyError
                if not mlist:
                    mimics.pop(prefix)
            except KeyError:
                mimic = bot.get_mimic(prefix, user)
                # Users are not allowed to delete mimics that do not belong to them
                if not isnan(perm) and mimic.u_id != user.id:
                    raise PermissionError("Target mimic does not belong to you.")
                mimics = mimicdb[mimic.u_id]
                user = await bot.fetch_user(mimic.u_id)
                m_id = mimic.id
                for prefix in mimics:
                    with suppress(ValueError, IndexError):
                        mimics[prefix].remove(m_id)
                mimicdb.pop(mimic.id)
            update(user.id)
            return italics(css_md(f"Successfully removed webhook mimic {sqr_md(mimic.name)} for {sqr_md(user)}."))
        if not prefix:
            raise IndexError("Prefix must not be empty.")
        if len(prefix) > 16:
            raise OverflowError("Prefix must be 16 or fewer in length.")
        if " " in prefix:
            raise TypeError("Prefix must not contain spaces.")
        # This limit is ridiculous. I like it.
        if sum(len(i) for i in iter(mimics.values())) >= 32768:
            raise OverflowError(f"Mimic list for {user} has reached the maximum of 32768 items. Please remove an item to add another.")
        dop = None
        mid = discord.utils.time_snowflake(dtn())
        ctime = utc()
        m_id = "&" + str(mid)
        mimic = None
        # Attempt to create a new mimic, a mimic from a user, or a copy of an existing mimic.
        if len(args):
            if len(args) > 1:
                urls = await bot.follow_url(args[-1], best=True)
                url = urls[0]
                name = " ".join(args[:-1])
            else:
                mim = 0
                try:
                    mim = verify_id(args[-1])
                    user = await bot.fetch_user(mim)
                    if user is None:
                        raise EOFError
                    dop = user.id
                    name = user.name
                    url = await bot.get_proxy_url(user)
                except:
                    try:
                        mimi = bot.get_mimic(mim, user)
                        dop = mimi.id
                        mimic = copy.deepcopy(mimi)
                        mimic.id = m_id
                        mimic.u_id = u_id
                        mimic.prefix = prefix
                        mimic.count = mimic.total = 0
                        mimic.created_at = ctime
                        mimic.auto = dop
                    except:
                        name = args[0]
                        url = "https://cdn.discordapp.com/embed/avatars/0.png"
        else:
            name = user.name
            url = await bot.get_proxy_url(user)
        # This limit is actually to comply with webhook usernames
        if len(name) > 80:
            raise OverflowError("Name must be 80 or fewer in length.")
        while m_id in mimics:
            mid += 1
            m_id = "&" + str(mid)
        if mimic is None:
            mimic = cdict(
                id=m_id,
                u_id=u_id,
                prefix=prefix,
                auto=dop,
                name=name,
                url=url,
                description="",
                gender="N/A",
                birthday=ctime,
                created_at=ctime,
                count=0,
                total=0,
            )
        mimicdb[m_id] = mimic
        if prefix in mimics:
            mimics[prefix].append(m_id)
        else:
            mimics[prefix] = [m_id]
        update(m_id)
        update(u_id)
        out = f"Successfully added webhook mimic {sqr_md(mimic.name)} with prefix {sqr_md(mimic.prefix)} and ID {sqr_md(mimic.id)}"
        if dop is not None:
            out += f", bound to user [{user_mention(dop) if type(dop) is int else f'<{dop}>'}]"
        return css_md(out)

    async def _callback_(self, bot, message, reaction, user, perm, vals, **void):
        u_id, pos = list(map(int, vals.split("_", 1)))
        if reaction not in (None, self.directions[-1]) and u_id != user.id and perm <= inf:
            return
        if reaction not in self.directions and reaction is not None:
            return
        guild = message.guild
        update = self.data.mimics.update
        mimicdb = bot.data.mimics
        user = await bot.fetch_user(u_id)
        mimics = mimicdb.get(user.id, {})
        for k in tuple(mimics):
            if not mimics[k]:
                mimics.pop(k)
                update(user.id)
        page = 24
        last = max(0, len(mimics) - page)
        if reaction is not None:
            i = self.directions.index(reaction)
            if i == 0:
                new = 0
            elif i == 1:
                new = max(0, pos - page)
            elif i == 2:
                new = min(last, pos + page)
            elif i == 3:
                new = last
            else:
                new = pos
            pos = new
        content = message.content
        if not content:
            content = message.embeds[0].description
        i = content.index("callback")
        content = "*```" + "\n" * ("\n" in content[:i]) + (
            "callback-fun-mimic-"
            + str(u_id) + "_" + str(pos)
            + "-\n"
        )
        if not mimics:
            content += f"No currently enabled webhook mimics for {str(user).replace('`', '')}.```*"
            msg = ""
        else:
            content += f"{len(mimics)} currently enabled webhook mimics for {str(user).replace('`', '')}:```*"
            key = lambda x: lim_str("⟨" + ", ".join(i + ": " + (str(no_md(mimicdb[i].name)), "[<@" + str(getattr(mimicdb[i], "auto", "None")) + ">]")[bool(getattr(mimicdb[i], "auto", None))] for i in iter(x)) + "⟩", 1900 / len(mimics))
            msg = ini_md(iter2str({k: mimics[k] for k in sorted(mimics)[pos:pos + page]}, key=key))
        colour = await bot.get_colour(user)
        emb = discord.Embed(
            description=content + msg,
            colour=colour,
        )
        emb.set_author(**get_author(user))
        more = len(mimics) - pos - page
        if more > 0:
            emb.set_footer(text=f"{uni_str('And', 1)} {more} {uni_str('more...', 1)}")
        create_task(message.edit(content=None, embed=emb, allowed_mentions=discord.AllowedMentions.none()))
        if hasattr(message, "int_token"):
            await bot.ignore_interaction(message)


class MimicSend(Command):
    name = ["RPSend", "PluralSend"]
    description = "Sends a message using a webhook mimic, to the target channel."
    usage = "<0:mimic> <1:channel> <2:string>"
    no_parse = True
    rate_limit = 0.5

    async def __call__(self, bot, channel, message, user, perm, argv, args, **void):
        update = bot.data.mimics.update
        mimicdb = bot.data.mimics
        mimics = set_dict(mimicdb, user.id, {})
        prefix = args.pop(0)
        c_id = verify_id(args.pop(0))
        channel = await bot.fetch_channel(c_id)
        guild = channel.guild
        msg = argv.split(None, 2)[-1]
        if not msg:
            raise IndexError("Message is empty.")
        perm = bot.get_perms(user.id, guild)
        try:
            mlist = mimics[prefix]
            if mlist is None:
                raise KeyError
            m = [bot.get_mimic(verify_id(p)) for p in mlist]
        except KeyError:
            mimic = bot.get_mimic(verify_id(prefix))
            m = [mimic]
        admin = not inf > perm
        try:
            enabled = bot.data.enabled[channel.id]
        except KeyError:
            enabled = bot.data.enabled.get(guild.id, ())
        # Because this command operates across channels and servers, we need to make sure these cannot be sent to channels without this command enabled
        if not admin and ("fun" not in enabled or perm < 1):
            raise PermissionError("Not permitted to send into target channel.")
        if m:
            msg = escape_roles(msg)
            if msg.startswith("/tts "):
                msg = msg[5:]
                tts = True
            else:
                tts = False
            if guild and "logM" in bot.data and guild.id in bot.data.logM:
                c_id = bot.data.logM[guild.id]
                try:
                    c = await self.bot.fetch_channel(c_id)
                except (EOFError, discord.NotFound):
                    bot.data.logM.pop(guild.id)
                    return
                emb = await bot.as_embed(message, link=True)
                emb.colour = discord.Colour(0x00FF00)
                action = f"**Mimic invoked in** {channel_mention(channel.id)}:\n"
                emb.description = lim_str(action + emb.description, 4096)
                emb.timestamp = message.created_at
                self.bot.send_embeds(c, emb)
            for mimic in m:
                await bot.data.mimics.update_mimic(mimic, guild)
                name = mimic.name
                url = mimic.url
                await wait_on_none(bot.send_as_webhook(channel, msg, username=name, avatar_url=url, tts=tts))
                mimic.count += 1
                mimic.total += len(msg)
            create_task(message.add_reaction("👀"))


class UpdateMimics(Database):
    name = "mimics"

    async def _nocommand_(self, message, **void):
        if not message.content:
            return
        user = message.author
        if user.id in self.data:
            bot = self.bot
            perm = bot.get_perms(user.id, message.guild)
            if perm < 1:
                return
            admin = not inf > perm
            if message.guild is not None:
                try:
                    enabled = bot.data.enabled[message.channel.id]
                except KeyError:
                    enabled = ()
            else:
                enabled = list(bot.categories)
            # User must have permission to use ~mimicsend in order to invoke by prefix
            if admin or "fun" in enabled:
                database = self.data[user.id]
                msg = message.content
                with bot.ExceptionSender(message.channel, Exception, reference=message):
                    # Stack multiple messages to send, may be separated by newlines
                    sending = alist()
                    channel = message.channel
                    for line in msg.splitlines():
                        found = False
                        # O(1) time complexity per line regardless of how many mimics a user is assigned
                        if len(line) > 2 and " " in line:
                            i = line.index(" ")
                            prefix = line[:i]
                            if prefix in database:
                                mimics = database[prefix]
                                if mimics:
                                    line = line[i + 1:].strip(" ")
                                    for m in mimics:
                                        sending.append(cdict(m_id=m, msg=line))
                                    found = True
                        if not sending:
                            break
                        if not found:
                            sending[-1].msg += "\n" + line
                    if sending:
                        guild = message.guild
                        create_task(bot.silent_delete(message))
                        if guild and "logM" in bot.data and guild.id in bot.data.logM:
                            c_id = bot.data.logM[guild.id]
                            try:
                                c = await self.bot.fetch_channel(c_id)
                            except (EOFError, discord.NotFound):
                                bot.data.logM.pop(guild.id)
                                return
                            emb = await self.bot.as_embed(message, link=True)
                            emb.colour = discord.Colour(0x00FF00)
                            action = f"**Mimic invoked in** {channel_mention(channel.id)}:\n"
                            emb.description = lim_str(action + emb.description, 4096)
                            emb.timestamp = message.created_at
                            self.bot.send_embeds(c, emb)
                        for k in sending:
                            mimic = self.data[k.m_id]
                            await self.update_mimic(mimic, guild=guild)
                            name = mimic.name
                            url = mimic.url
                            msg = escape_roles(k.msg)
                            if msg.startswith("/tts "):
                                msg = msg[5:]
                                tts = True
                            else:
                                tts = False
                            await wait_on_none(bot.send_as_webhook(channel, msg, username=name, avatar_url=url, tts=tts))
                            mimic.count += 1
                            mimic.total += len(k.msg)
                            bot.data.users.add_xp(user, math.sqrt(len(msg)) * 2)

    async def update_mimic(self, mimic, guild=None, it=None):
        if mimic.setdefault("auto", None):
            bot = self.bot
            mim = 0
            try:
                mim = verify_id(mimic.auto)
                if guild is not None:
                    user = guild.get_member(mim)
                if user is None:
                    user = await bot.fetch_user(mim)
                if user is None:
                    raise LookupError
                mimic.name = user.display_name
                mimic.url = await bot.get_proxy_url(user)
            except (discord.NotFound, LookupError):
                try:
                    mimi = bot.get_mimic(mim)
                    if it is None:
                        it = {}
                    # If we find the same mimic twice, there is an infinite loop
                    elif mim in it:
                        raise RecursionError("Infinite recursive loop detected.")
                    it[mim] = True
                    if not len(it) & 255:
                        await asyncio.sleep(0.2)
                    await self.update_mimic(mimi, guild=guild, it=it)
                    mimic.name = mimi.name
                    mimic.url = mimi.url
                except LookupError:
                    mimic.name = str(mimic.auto)
                    mimic.url = "https://cdn.discordapp.com/embed/avatars/0.png"
        return mimic

    async def __call__(self):
        with tracebacksuppressor(SemaphoreOverflowError):
            async with self._semaphore:
                async with Delay(120):
                    # Garbage collector for unassigned mimics
                    i = 1
                    for m_id in tuple(self.data):
                        if type(m_id) is str:
                            mimic = self.data[m_id]
                            try:
                                if mimic.u_id not in self.data or mimic.id not in self.data[mimic.u_id][mimic.prefix]:
                                    self.data.pop(m_id)
                            except:
                                self.data.pop(m_id)
                        if not i % 8191:
                            await asyncio.sleep(0.45)
                        i += 1