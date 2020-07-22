import os, sys, subprocess, psutil, asyncio, discord, json, pytz, requests, aiohttp, inspect, importlib
import urllib.request, urllib.parse, concurrent.futures


from smath import *

python = ("python3", "python")[os.name == "nt"]
Process = psutil.Process()
urlParse = urllib.parse.quote
escape_markdown = discord.utils.escape_markdown
escape_everyone = lambda s: s.replace("@everyone", "@\xadeveryone").replace("@here", "@\xadhere").replace("<@&", "<@\xad&")
time_snowflake = discord.utils.time_snowflake
snowflake_time = discord.utils.snowflake_time

class ArgumentError(LookupError):
    pass
class TooManyRequests(PermissionError):
    pass


# Decodes HTML encoded characters in a string.
def htmlDecode(s):
    while len(s) > 7:
        try:
            i = s.index("&#")
        except ValueError:
            break
        try:
            if s[i + 2] == "x":
                h = "0x"
                p = i + 3
            else:
                h = ""
                p = i + 2
            for a in range(4):
                if s[p + a] == ";":
                    v = int(h + s[p:p + a])
                    break
            c = chr(v)
            s = s[:i] + c + s[p + a + 1:]
        except ValueError:
            continue
        except IndexError:
            continue
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    return s.replace("&quot;", '"').replace("&apos;", "'")


# Escapes syntax in code highlighting markdown.

ESCAPE_T = {
    "[": "⦍",
    "]": "⦎",
    "@": "＠",
    "`": "",
    ";": ";",
}
__emap = "".maketrans(ESCAPE_T)

ESCAPE_T2 = {
    "@": "＠",
    "`": "",
    "#": "♯",
    ";": ";",
}
__emap2 = "".maketrans(ESCAPE_T2)

__sptrans = re.compile("  +")

noHighlight = lambda s: str(s).translate(__emap)
clrHighlight = lambda s: str(s).translate(__emap2)
sbHighlight = lambda s: "[" + noHighlight(s) + "]"
singleSpace = lambda s: re.sub(__sptrans, " ", s)


# Counts the number of lines in a file.
def getLineCount(fn):
    with open(fn, "rb") as f:
        count = 1
        size = 0
        while True:
            try:
                i = f.read(8192)
                if not i:
                    raise EOFError
                size += len(i)
                count += i.count(b"\n")
            except EOFError:
                return hlist((size, count))


# Checks if a file is a python code file using its filename extension.
iscode = lambda fn: str(fn).endswith(".py") or str(fn).endswith(".pyw")


# Checks if an object can be used in "await" operations.
awaitable = lambda obj: hasattr(obj, "__await__") or issubclass(type(obj), asyncio.Future) or issubclass(type(obj), asyncio.Task) or inspect.isawaitable(obj)

# Async function that waits for a given time interval if the result of the input coroutine is None.
async def waitOnNone(coro, seconds=0.5):
    resp = await coro
    if resp is None:
        await asyncio.sleep(seconds)
    return resp

# Mutable object storing return values of a function.
class returns:

    def __init__(self, data=None):
        self.data = data

    __call__ = lambda self: self.data
    __bool__ = lambda self: self.data is not None

async def parasync(coro, rets):
    try:
        resp = await coro
        rets.data = returns(resp)
    except Exception as ex:
        rets.data = repr(ex)
    return returns()

# Recursively iterates through an iterable finding coroutines and executing them.
async def recursiveCoro(item):
    rets = hlist()
    try:
        len(item)
    except TypeError:
        item = hlist(item)
    for i, obj in enumerate(item):
        try:
            if type(obj) in (str, bytes):
                raise TypeError
            if issubclass(type(obj), collections.abc.Mapping) or issubclass(type(obj), io.IOBase):
                raise TypeError
            if awaitable(obj):
                raise TypeError
            obj = tuple(obj)
        except TypeError:
            pass
        if type(obj) is tuple:
            rets.append(returns())
            create_task(parasync(recursiveCoro(obj), rets[-1]))
        elif awaitable(obj):
            rets.append(returns())
            create_task(parasync(obj, rets[-1]))
        else:
            rets.append(returns(obj))
    full = False
    while not full:
        full = True
        for i in rets:
            if not i:
                full = False
        await asyncio.sleep(0.2)
    output = hlist()
    for i in rets:
        while isinstance(i, returns):
            i = i()
        output.append(i)
    return output


# Sends a message to a channel, then adds reactions accordingly.
async def sendReact(channel, *args, reacts=(), **kwargs):
    try:
        sent = await channel.send(*args, **kwargs)
        for react in reacts:
            await sent.add_reaction(react)
    except:
        print(traceback.format_exc())

# Sends a message to a channel, then edits to add links to all attached files.
async def sendFile(channel, msg, file, filename=None, best=False):
    try:
        message = await channel.send(msg, file=file)
        if filename is not None:
            create_future_ex(os.remove, filename)
    except:
        if filename is not None:
            create_future_ex(os.remove, filename)
        raise
    if message.attachments:
        await message.edit(content=message.content + ("" if message.content.endswith("```") else "\n") + ("\n".join("<" + bestURL(a) + ">" for a in message.attachments) if best else "\n".join("<" + a.url + ">" for a in message.attachments)))


# Finds the best URL for a discord object's icon.
bestURL = lambda obj: obj if type(obj) is str else (strURL(obj.avatar_url) if getattr(obj, "avatar_url", None) else (obj.proxy_url if obj.proxy_url else obj.url))


# Finds emojis and user mentions in a string.
emojiFind = re.compile("<.?:[^<>:]+:[0-9]+>")
findEmojis = lambda s: re.findall(emojiFind, s)
userFind = re.compile("<@!?[0-9]+>")
findUsers = lambda s: re.findall(userFind, s)


# Returns a string representation of a message object.
def strMessage(message, limit=1024, username=False):
    c = message.content
    s = getattr(message, "system_content", None)
    if s and len(s) > len(c):
        c = s
    if username:
        c = "<@" + str(message.author.id) + ">:\n" + c
    data = limStr(c, limit)
    if message.attachments:
        data += "\n[" + ", ".join(i.url for i in message.attachments) + "]"
    if message.embeds:
        data += "\n⟨" + ", ".join(str(i.to_dict()) for i in message.embeds) + "⟩"
    if message.reactions:
        data += "\n{" + ", ".join(str(i) for i in message.reactions) + "}"
    try:
        t = message.created_at
        if message.edited_at:
            t = message.edited_at
        data += "\n`(" + str(t) + ")`"
    except AttributeError:
        pass
    if not data:
        data = "```css\n" + uniStr("[EMPTY MESSAGE]") + "```"
    return limStr(data, limit)

# Returns a string representation of an activity object.
def strActivity(activity):
    if hasattr(activity, "type") and activity.type != discord.ActivityType.custom:
        t = activity.type.name
        return t[0].upper() + t[1:] + " " + activity.name
    return str(activity)


# Alphanumeric string regular expression.
atrans = re.compile("[^a-z 0-9]", re.I)
ntrans = re.compile("[0-9]", re.I)
is_alphanumeric = lambda string: not re.search(atrans, string)
to_alphanumeric = lambda string: singleSpace(re.sub(atrans, " ", reconstitute(string)))
is_numeric = lambda string: re.search(ntrans, string)


# Strips code box from the start and end of a message.
def noCodeBox(s):
    if s.startswith("```") and s.endswith("```"):
        s = s[s.index("\n") + 1:-3]
    return s


# A string lookup operation with an iterable, multiple attempts, and sorts by priority.
async def strLookup(it, query, ikey=lambda x: [str(x)], qkey=lambda x: [str(x)], loose=True):
    queries = qkey(query)
    qlist = [q for q in queries if q]
    if not qlist:
        qlist = queries
    cache = [[[inf, None], [inf, None]] for _ in qlist]
    for x, i in enumerate(shuffle(it), 1):
        for c in ikey(i):
            if not c and i:
                continue
            for a, b in enumerate(qkey(c)):
                if b == qlist[a]:
                    return i
                elif b.startswith(qlist[a]):
                    if len(b) < cache[a][0][0]:
                        cache[a][0] = [len(b), i]
                elif loose and qlist[a] in b:
                    if len(b) < cache[a][1][0]:
                        cache[a][1] = [len(b), i]
        if not x & 1023:
            await asyncio.sleep(0.1)
    for c in cache:
        if c[0][0] < inf:
            return c[0][1]
    if loose:
        for c in cache:
            if c[1][0] < inf:
                return c[1][1]
    raise LookupError("No results for " + str(query) + ".")


# Generates a random colour across the spectrum, in intervals of 128.
randColour = lambda: colour2Raw(colourCalculation(xrand(12) * 128))


# Gets the string representation of a url object with the maximum allowed image size for discord, replacing webp with png format when possible.
def strURL(url):
    if type(url) is not str:
        url = str(url)
    if url.endswith("?size=1024"):
        url = url[:-10] + "?size=4096"
    return url.replace(".webp", ".png")


# A translator to stip all characters from mentions.
__imap = {
    "#": "",
    "<": "",
    ">": "",
    "@": "",
    "!": "",
    "&": "",
}
__itrans = "".maketrans(__imap)

def verifyID(value):
    try:
        return int(str(value).translate(__itrans))
    except ValueError:
        return value


# Strips <> characters from URLs.
def stripAcc(url):
    if url.startswith("<") and url[-1] == ">":
        s = url[1:-1]
        if isURL(s):
            return s
    return url
__smap = {"|": "", "*": ""}
__strans = "".maketrans(__smap)
verifySearch = lambda f: stripAcc(singleSpace(f.strip().translate(__strans)))
urlFind = re.compile("(?:http|hxxp|ftp|fxp)s?:\\/\\/[^\\s<>`|\"']+")
urlIs = re.compile("^(?:http|hxxp|ftp|fxp)s?:\\/\\/[^\\s<>`|\"']+$")
findURLs = lambda url: re.findall(urlFind, url)
isURL = lambda url: re.search(urlIs, url)
verifyURL = lambda url: url if isURL(url) else urllib.parse.quote(url)


# Checks if a URL contains a valid image extension, and removes it if possible.
IMAGE_FORMS = {
    ".gif": True,
    ".png": True,
    ".bmp": False,
    ".jpg": True,
    ".jpeg": True,
    ".tiff": False,
    ".webp": True,
}
def is_image(url):
    if "." in url:
        url = url[url.rindex("."):]
    url = url.lower()
    return IMAGE_FORMS.get(url)


# Subprocess pool for resource-consuming operations.
SUBS = cdict(math=cdict(procs=hlist(), busy=cdict()), image=cdict(procs=hlist(), busy=cdict()))

# Gets amount of processes running in pool.
subCount = lambda: sum(1 for ptype in SUBS.values() for proc in ptype.procs if proc.is_running())

def forceKill(proc):
    for child in proc.children(recursive=True):
        try:
            child.kill()
        except:
            pass
        else:
            print(child, "killed.")
    print(proc, "killed.")
    return proc.kill()

# Kills all subprocesses in the pool, then restarts it.
def subKill():
    for ptype in SUBS.values():
        for proc in ptype.procs:
            try:
                forceKill(proc)
            except psutil.NoSuchProcess:
                pass
        ptype.procs.clear()
        ptype.busy.clear()
    procUpdate()

# Updates process pool by killing off processes when not necessary, and spawning new ones when required.
def procUpdate():
    for pname, ptype in SUBS.items():
        procs = ptype.procs
        b = len(ptype.busy)
        count = sum(1 for proc in procs if utc() > proc.busy)
        if count > 16:
            return
        if b + 1 > count:
            if pname == "math":
                proc = psutil.Popen(
                    [python, "misc/math.py"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            elif pname == "image":
                proc = psutil.Popen(
                    [python, "misc/image.py"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            else:
                raise TypeError("invalid subpool " + pname)
            proc.busy = nan
            x = bytes(random.randint(0, 255) for _ in loop(32))
            if random.randint(0, 1):
                x = hashlib.sha256(x).digest()
            x = base64.b64encode(x)
            proc.stdin.write(bytes(repr(x) + "\n", "utf-8"))
            proc.key = x.decode("utf-8", "replace")
            proc.busy = utc()
            print(proc, "initialized with key", proc.key)
            procs.append(proc)
        att = 0
        while count > b + 2:
            found = False
            for p, proc in enumerate(procs):
                # Busy variable indicates when the last operation finished;
                # processes that are idle longer than 1 hour are automatically terminated
                if utc() - proc.busy > 3600:
                    forceKill(proc)
                    procs.pop(p)
                    found = True
                    count -= 1
                    break
            att += 1
            if att >= 16 or not found:
                break

# Sends an operation to the math subprocess pool.
async def mathProc(expr, prec=64, rat=False, key=-1, timeout=12, authorize=False):
    if type(key) is not int:
        try:
            key = int(key)
        except (TypeError, ValueError):
            key = key.id
    procs, busy = SUBS.math.procs, SUBS.math.busy
    while utc() - busy.get(key, 0) < 60:
        await asyncio.sleep(0.5)
    try:
        while True:
            for p in range(len(procs)):
                if p < len(procs):
                    proc = procs[p]
                    if utc() > proc.busy:
                        raise StopIteration
                else:
                    break
            await create_future(procUpdate)
            await asyncio.sleep(0.5)
    except StopIteration:
        pass
    if authorize:
        args = (expr, prec, rat, proc.key)
    else:
        args = (expr, prec, rat)
    d = repr(bytes("`".join(i if type(i) is str else str(i) for i in args), "utf-8")).encode("utf-8") + b"\n"
    try:
        proc.busy = inf
        busy[key] = utc()
        await create_future(procUpdate)
        await create_future(proc.stdin.write, d)
        await create_future(proc.stdin.flush)
        resp = await asyncio.wait_for(create_future(proc.stdout.readline), timeout=timeout)
        proc.busy = utc()
    except (TimeoutError, asyncio.exceptions.TimeoutError):
        create_future_ex(forceKill, proc)
        try:
            procs.pop(p)
        except LookupError:
            pass
        try:
            busy.pop(key)
        except KeyError:
            pass
        create_future_ex(procUpdate)
        raise
    try:
        busy.pop(key)
    except KeyError:
        pass
    output = evalEX(evalEX(resp))
    return output

# Sends an operation to the image subprocess pool.
async def imageProc(image, operation, args, key=-1, timeout=24):
    if type(key) is not int:
        try:
            key = int(key)
        except (TypeError, ValueError):
            key = key.id
    procs, busy = SUBS.image.procs, SUBS.image.busy
    while utc() - busy.get(key, 0) < 60:
        await asyncio.sleep(0.5)
    try:
        while True:
            for p in range(len(procs)):
                if p < len(procs):
                    proc = procs[p]
                    if utc() > proc.busy:
                        raise StopIteration
                else:
                    break
            await create_future(procUpdate)
            await asyncio.sleep(0.5)
    except StopIteration:
        pass
    d = repr(bytes("`".join(str(i) for i in (image, operation, args)), "utf-8")).encode("utf-8") + b"\n"
    try:
        proc.busy = inf
        busy[key] = utc()
        await create_future(procUpdate)
        await create_future(proc.stdin.write, d)
        await create_future(proc.stdin.flush)
        resp = await asyncio.wait_for(create_future(proc.stdout.readline), timeout=timeout)
        proc.busy = utc()
    except (TimeoutError, asyncio.exceptions.TimeoutError):
        create_future_ex(forceKill, proc)
        try:
            procs.pop(p)
        except LookupError:
            pass
        try:
            busy.pop(key)
        except KeyError:
            pass
        create_future_ex(procUpdate)
        raise
    try:
        busy.pop(key)
    except KeyError:
        pass
    output = evalEX(evalEX(resp))
    return output


# Evaluates an an expression, raising it if it is an exception.
def evalEX(exc):
    try:
        ex = eval(exc)
    except NameError:
        if type(exc) is bytes:
            exc = exc.decode("utf-8", "replace")
        s = exc[exc.index("(") + 1:exc.index(")")]
        try:
            s = ast.literal_eval(s)
        except:
            pass
        ex = RuntimeError(s)
    except:
        print(exc)
        raise
    if issubclass(type(ex), Exception):
        raise ex
    return ex


# Calls a function, but printing exceptions when they occur.
def funcSafe(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except:
        print(func, args, kwargs)
        print(traceback.format_exc())
        raise

# Awaits a coroutine, but does not raise exceptions that occur.
async def safeCoro(coro):
    try:
        return await coro
    except:
        print(traceback.format_exc())

# Forces the operation to be a coroutine regardless of whether it is or not.
async def forceCoro(coro):
    if awaitable(coro):
        return await coro
    return coro


# Main event loop for all asyncio operations.
eloop = asyncio.new_event_loop()
__setloop__ = lambda: asyncio.set_event_loop(eloop)


# Thread pool manager for multithreaded operations.
class MultiThreadPool(collections.abc.Sized, concurrent.futures.Executor):

    def __init__(self, pool_count=3, thread_count=64, initializer=None):
        self.pools = hlist()
        self.pool_count = max(1, pool_count)
        self.thread_count = max(1, thread_count)
        self.initializer = initializer
        self.position = -1
        self.update()

    __len__ = lambda self: sum(len(pool._threads) for pool in self.pools)

    # Adjusts pool count if necessary
    def _update(self):
        if self.pool_count != len(self.pools):
            self.pool_count = max(1, self.pool_count)
            self.thread_count = max(1, self.thread_count)
            while self.pool_count > len(self.pools):
                self.pools.append(concurrent.futures.ThreadPoolExecutor(max_workers=self.thread_count, initializer=self.initializer))
            while self.pool_count < len(self.pools):
                func = self.pools.popright().shutdown
                self.pools[-1].submit(func, wait=True)

    def update(self):
        if not self.pools:
            self._update()
        self.position = (self.position + 1) & len(self.pools) - 1
        random.choice(self.pools).submit(self._update)

    def map(self, func, *args, **kwargs):
        self.update()
        return self.pools[self.position].map(func, *args, **kwargs)

    def submit(self, func, *args, **kwargs):
        self.update()
        return self.pools[self.position].submit(func, *args, **kwargs)

    shutdown = lambda self, wait=True: [exc.shutdown(wait) for exc in self.pools].extend(self.pools.clear())

pthreads = MultiThreadPool(thread_count=48, initializer=__setloop__)
athreads = MultiThreadPool(thread_count=64, initializer=__setloop__)
__setloop__()

# Creates an asyncio Future that waits on a multithreaded one.
def wrap_future(fut, loop=None):
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = eloop
    new_fut = loop.create_future()

    def on_done(*void):
        try:
            result = fut.result()
        except Exception as ex:
            loop.call_soon_threadsafe(new_fut.set_exception, ex)
        else:
            loop.call_soon_threadsafe(new_fut.set_result, result)

    fut.add_done_callback(on_done)
    return new_fut

# Runs a function call in a parallel thread, returning a future object waiting on the output.
create_future = lambda func, *args, loop=None, priority=False, **kwargs: wrap_future((athreads, pthreads)[priority].submit(func, *args, **kwargs), loop=loop)
create_future_ex = lambda func, *args, priority=False, **kwargs: (athreads, pthreads)[priority].submit(func, *args, **kwargs)

# Creates an asyncio Task object from an awaitable object.
def create_task(fut, *args, loop=None, **kwargs):
    if loop is None:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = eloop
    return asyncio.ensure_future(fut, *args, loop=loop, **kwargs)

# A dummy coroutine that returns None.
async def retNone(*args, **kwargs):
    return

# A function that takes a coroutine, and calls a second function if it takes longer than the specified delay.
async def delayed_callback(fut, delay, func, *args, exc=False, **kwargs):
    await asyncio.sleep(delay)
    try:
        return fut.result()
    except asyncio.exceptions.InvalidStateError:
        res = func(*args, **kwargs)
        if awaitable(res):
            await res
        try:
            return await fut
        except:
            if exc:
                raise
    except:
        if exc:
            raise


create_future_ex(procUpdate, priority=True)


# Manages both sync and async get requests.
class AutoRequest:

    async def _init_(self):
        self.session = aiohttp.ClientSession()
        self.semaphore = asyncio.Semaphore(512)

    async def aio_call(self, url, headers, data, decode):
        async with self.semaphore:
            async with self.session.get(url, headers=headers, data=data) as resp:
                if resp.status >= 400:
                    text = await resp.read()
                    raise ConnectionError("Error " + str(resp.status) + ": " + text.decode("utf-8", "replace"))
                data = await resp.read()
                if decode:
                    data = data.decode("utf-8", "replace")
                return data

    def __call__(self, url, headers={}, data=None, raw=False, timeout=8, bypass=True, decode=False, aio=False):
        if bypass and "user-agent" not in headers:
            headers["user-agent"] = "Mozilla/5." + str(xrand(1, 10))
        if aio:
            return create_task(asyncio.wait_for(self.aio_call(url, headers, data, decode), timeout=timeout))
        with requests.get(url, headers=headers, data=data, stream=True, timeout=timeout) as resp:
            if resp.status_code >= 400:
                raise ConnectionError("Error " + str(resp.status_code) + ": " + resp.text)
            if raw:
                data = resp.raw.read()
            else:
                data = resp.content
            if decode:
                data = data.decode("utf-8", "replace")
            return data

Request = AutoRequest()
create_task(Request._init_())


# Stores and manages timezones information.
TIMEZONES = cdict()

def load_timezones():
    with open("misc/timezones.txt", "rb") as f:
        data = f.read().decode("utf-8", "replace")
        for line in data.split("\n"):
            info = line.split("\t")
            abb = info[0].lower()
            if len(abb) >= 3 and abb not in TIMEZONES:
                temp = info[-1].replace("\\", "/")
                curr = sorted([round((1 - (i[3] == "−") * 2) * (rdhms(i[4:]) if ":" in i else float(i[4:]) * 60) * 60) for i in temp.split("/") if i.startswith("UTC")])
                if len(curr) == 1:
                    curr = curr[0]
                TIMEZONES[abb] = curr

def is_dst(dt=None, timezone="UTC"):
    if dt is None:
        dt = utc_dt()
    timezone = pytz.timezone(timezone)
    timezone_aware_date = timezone.localize(dt, is_dst=None)
    return timezone_aware_date.tzinfo._dst.seconds != 0

def get_timezone(tz):
    s = TIMEZONES[tz]
    if issubclass(type(s), collections.abc.Sequence):
        return s[is_dst(timezone=tz.upper())]
    return s

create_future_ex(load_timezones)

# Parses a time expression, with an optional timezone input at the end.
def tzparse(expr):
    if " " in expr:
        t = 0
        try:
            args = shlex.split(expr)
        except ValueError:
            args = expr.split()
        for a in (args[0], args[-1]):
            tz = a.lower()
            if tz in TIMEZONES:
                t = get_timezone(tz)
                expr = expr.replace(a, "")
                break
        return tparser.parse(expr) - datetime.timedelta(seconds=t)
    return tparser.parse(expr)


# Basic inheritable class for all bot commands.
class Command(collections.abc.Hashable, collections.abc.Callable):
    min_level = -inf
    rate_limit = 0
    description = ""
    usage = ""

    def permError(self, perm, req=None, reason=None):
        if req is None:
            req = self.min_level
        if reason is None:
            reason = "for command " + self.name[-1]
        return PermissionError(
            "Insufficient priviliges " + str(reason)
            + ". Required level: " + str(req)
            + ", Current level: " + str(perm) + "."
        )

    def __init__(self, bot, catg):
        self.used = {}
        if not hasattr(self, "data"):
            self.data = cdict()
        if not hasattr(self, "name"):
            self.name = []
        self.__name__ = self.__class__.__name__
        if not hasattr(self, "alias"):
            self.alias = self.name
        else:
            self.alias.append(self.__name__)
        self.name.append(self.__name__)
        if not hasattr(self, "min_display"):
            self.min_display = self.min_level
        for a in self.alias:
            b = a.replace("*", "").replace("_", "").replace("||", "")
            if b:
                a = b
            a = a.lower()
            if a in bot.commands:
                bot.commands[a].append(self)
            else:
                bot.commands[a] = hlist([self])
        self.catg = catg
        self.bot = bot
        self._globals = bot._globals
        f = getattr(self, "__load__", None)
        if callable(f):
            try:
                f()
            except:
                print(traceback.format_exc())
                self.data.clear()
                f()

    __hash__ = lambda self: hash(self.__name__)
    __str__ = lambda self: self.__name__
    
    async def __call__(self, **void):
        pass


# Basic inheritable class for all bot databases.
class Database(collections.abc.Hashable, collections.abc.Callable):
    bot = None
    rate_limit = 3
    name = "data"

    def __init__(self, bot, catg):
        self.used = utc()
        name = self.name
        self.__name__ = self.__class__.__name__
        if not getattr(self, "no_file", False):
            self.file = "saves/" + name + ".json"
            self.updated = False
            try:
                f = open(self.file, "rb")
                s = f.read()
                f.close()
                if not s:
                    raise FileNotFoundError
                data = None
                try:
                    data = pickle.loads(s)
                except pickle.UnpicklingError:
                    pass
                if type(data) in (str, bytes):
                    data = eval(data)
                if data is None:
                    try:
                        data = eval(s)
                    except:
                        print(self.file)
                        print(traceback.format_exc())
                        raise FileNotFoundError
                bot.data[name] = self.data = data
            except FileNotFoundError:
                data = None
        else:
            data = None
        if not data:
            bot.data[name] = self.data = cdict()
        bot.database[name] = self
        self.catg = catg
        self.bot = bot
        self.busy = self.checking = False
        self._globals = globals()
        f = getattr(self, "__load__", None)
        if callable(f):
            try:
                f()
            except:
                print(traceback.format_exc())
                self.data.clear()
                f()

    __hash__ = lambda self: hash(self.__name__)
    __str__ = lambda self: self.__name__

    async def __call__(self, **void):
        pass

    def update(self, force=False):
        if not hasattr(self, "updated"):
            self.updated = False
        if force:
            name = getattr(self, "name", None)
            if name:
                if self.updated:
                    self.updated = False
                    s = str(self.data)
                    if len(s) > 262144:
                        # print("Pickling " + name + "...")
                        s = pickle.dumps(self.data)
                    else:
                        s = s.encode("utf-8")
                    f = open(self.file, "wb")
                    f.write(s)
                    f.close()
                    return True
        else:
            self.updated = True
        return False


# Redirects all print operations to target files, limiting the amount of operations that can occur in any given amount of time for efficiency.
class __logPrinter:

    def __init__(self, file=None):
        self.exec = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.data = {}
        self.funcs = hlist()
        self.file = file
        self.future = self.exec.submit(self.updatePrint)
        self.closed = False

    def filePrint(self, fn, b):
        try:
            if type(fn) not in (str, bytes):
                f = fn
            if type(b) in (bytes, bytearray):
                f = open(fn, "ab")
            elif type(b) is str:
                f = open(fn, "a", encoding="utf-8")
            else:
                f = fn
            f.write(b)
            f.close()
        except:
            sys.__stdout__.write(traceback.format_exc())
    
    def updatePrint(self):
        if self.file is None:
            outfunc = sys.__stdout__.write
            enc = lambda x: x
        else:
            outfunc = lambda s: self.filePrint(self.file, s)
            enc = lambda x: bytes(x, "utf-8")
        outfunc(enc("Logging started.\n"))
        while True:
            try:
                for f in tuple(self.data):
                    if not self.data[f]:
                        self.data.pop(f)
                        continue
                    out = limStr(self.data[f], 8192)
                    self.data[f] = ""
                    data = enc(out)
                    if self.funcs:
                        [func(out) for func in self.funcs]
                    if f == self.file:
                        outfunc(data)
                    else:
                        self.filePrint(f, data)
            except:
                print(traceback.format_exc())
            time.sleep(1)
            while "common.py" not in os.listdir() or self.closed:
                time.sleep(0.5)

    def __call__(self, *args, sep=" ", end="\n", prefix="", file=None, **void):
        if file is None:
            file = self.file
        if file not in self.data:
            self.data[file] = ""
        self.data[file] += str(sep).join(i if type(i) is str else str(i) for i in args) + str(end) + str(prefix)

    read = lambda self, *args, **kwargs: bytes()
    write = lambda self, *args, end="", **kwargs: self.__call__(*args, end, **kwargs)
    flush = open = lambda self: (self, self.__setattr__("closed", False))[0]
    close = lambda self: self.__setattr__("closed", True)
    isatty = lambda self: False


# Sets all instances of print to the custom print implementation.
print = __p = __logPrinter("log.txt")
sys.stdout = sys.stderr = print
getattr(discord, "__builtins__", {})["print"] = print
getattr(concurrent.futures, "__builtins__", {})["print"] = print
getattr(asyncio.futures, "__builtins__", {})["print"] = print
getattr(asyncio, "__builtins__", {})["print"] = print
getattr(psutil, "__builtins__", {})["print"] = print
getattr(subprocess, "__builtins__", {})["print"] = print