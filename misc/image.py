#!/usr/bin/python3

import os, sys, io, time, concurrent.futures, subprocess, psutil, collections, traceback, re, numpy, requests, blend_modes
import PIL
from PIL import Image, ImageChops, ImageEnhance, ImageMath, ImageStat


exc = concurrent.futures.ThreadPoolExecutor(max_workers=2)
start = time.time()
CACHE = {}
ANIM = False


# For debugging only
def filePrint(*args, sep=" ", end="\n", prefix="", file="log.txt", **void):
    with open(file, "ab") as f:
        f.write((str(sep).join((i if type(i) is str else str(i)) for i in args) + str(end) + str(prefix)).encode("utf-8"))

def logging(func):
    def call(self, *args, file="log.txt", **kwargs):
        try:
            output = func(self, *args, **kwargs)
        except:
            filePrint(traceback.format_exc(), file=file)
            raise
        return output
    return call


# Time input detector, used to read FFprobe output
def rdhms(ts):
    data = ts.split(":")
    t = 0
    mult = 1
    while len(data):
        t += float(data[-1]) * mult
        data = data[:-1]
        if mult <= 60:
            mult *= 60
        elif mult <= 3600:
            mult *= 24
        elif len(data):
            raise TypeError("Too many time arguments.")
    return t

# URL string detector
urlIs = re.compile("^(?:http|hxxp|ftp|fxp)s?:\\/\\/[^\\s<>`|\"']+$")
isURL = lambda url: re.search(urlIs, url)


from_colour = lambda colour, size=128, key=None: Image.new("RGB", (size, size), colour) #Image.fromarray(numpy.tile(numpy.array(colour, dtype=numpy.uint8), (size, size, 1)))


sizecheck = re.compile("[1-9][0-9]*x[0-9]+")

def video2img(url, maxsize, fps, out, size=None, dur=None, orig_fps=None, data=None):
    direct = any((size is None, dur is None, orig_fps is None))
    ts = round(time.time() * 1000)
    fn = "cache/" + str(ts)
    if direct:
        if data is None:
            with requests.get(url, stream=True, timeout=8) as resp:
                data = resp.content
        file = open(fn, "wb")
        try:
            file.write(data)
        except:
            file.close()
            raise
        file.close()
    try:
        if direct:
            command = ["ffprobe", "-hide_banner", fn]
            resp = bytes()
            # Up to 3 attempts to get video duration
            for _ in range(3):
                try:
                    proc = psutil.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    fut = exc.submit(proc.communicate)
                    res = fut.result(timeout=12)
                    resp = bytes().join(res)
                    break
                except:
                    try:
                        proc.kill()
                    except:
                        pass
            s = resp.decode("utf-8", "replace")
            if dur is None:
                i = s.index("Duration: ")
                d = s[i + 10:]
                i = 2147483647
                for c in ", \n\r":
                    try:
                        x = d.index(c)
                    except ValueError:
                        pass
                    else:
                        if x < i:
                            i = x
                dur = rdhms(d[:i])
            else:
                d = s
            if orig_fps is None:
                i = d.index(" fps")
                f = d[i - 5:i]
                while f[0] < "0" or f[0] > "9":
                    f = f[1:]
                orig_fps = float(f)
            if size is None:
                sfind = re.finditer(sizecheck, d)
                sizestr = next(sfind).group()
                size = [int(i) for i in sizestr.split("x")]
        # Adjust FPS if duration is too long
        fps = min(fps, 256 / dur)
        fn2 = fn + ".gif"
        f_in = fn if direct else url
        command = ["ffmpeg", "-hide_banner", "-nostdin", "-loglevel", "error", "-y", "-i", f_in, "-fs", str(8388608 - 262144), "-an", "-vf"]
        w, h = max_size(*size, maxsize)
        vf = ""
        if w != size[0]:
            vf += "scale=" + str(w) + ":-1:flags=lanczos,"
        vf += "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse"
        command.extend([vf, "-loop", "0", "-r", str(fps), out])
        subprocess.check_output(command)
        if direct:
            os.remove(fn)
    except:
        if direct:
            try:
                os.remove(fn)
            except:
                pass
        raise

def create_gif(in_type, args, delay):
    ts = round(time.time() * 1000)
    out = "cache/" + str(ts) + ".gif"
    maxsize = 512
    if in_type == "video":
        video2img(args[0], maxsize, round(1000 / delay), out, args[1], args[2], args[3])
        return "$" + out
    images = args
    maxsize = int(min(maxsize, 32768 / len(images) ** 0.5))
    # Detect if an image sequence or video is being inputted
    imgs = collections.deque()
    for url in images:
        with requests.get(url, stream=True, timeout=8) as resp:
            data = resp.content
        try:
            img = get_image(data, None)
        except (PIL.UnidentifiedImageError, OverflowError):
            if len(data) < 268435456:
                video2img(data, maxsize, round(1000 / delay), out, data=data)
                # $ symbol indicates to return directly
                return "$" + out
            else:
                raise OverflowError("Max file size to load is 256MB.")
        else:
            for f in range(2147483648):
                try:
                    img.seek(f)
                except EOFError:
                    break
                if not imgs:
                    size = max_size(img.width, img.height, maxsize)
                img = resize_to(img, *size, operation="hamming")
                if str(img.mode) != "RGBA":
                    img = img.convert("RGBA")
                imgs.append(img)
    return dict(duration=delay * len(imgs), frames=imgs)

def rainbow_gif2(image, duration):
    out = collections.deque()
    total = 0
    for f in range(2147483648):
        try:
            image.seek(f)
        except EOFError:
            break
        total += image.info.get("duration", 1 / 60)
    length = f
    loops = total / duration / 1000
    scale = 1
    while abs(loops * scale) < 1:
        scale *= 2
        if length * scale >= 64:
            loops = 1 if loops >= 0 else -1
            break
    loops = round(loops * scale) / scale
    if not loops:
        loops = 1 if loops >= 0 else -1
    maxsize = int(min(512, 32768 / (length * scale ** 0.5) ** 0.5))
    size = list(max_size(*image.size, maxsize))
    for f in range(length * scale):
        image.seek(f % length)
        if str(image.mode) != "RGBA":
            temp = image.convert("RGBA")
        else:
            temp = image
        if temp.size[0] != size[0] or temp.size[1] != size[1]:
            temp = temp.resize(size, Image.HAMMING)
        A = temp.getchannel("A")
        channels = list(temp.convert("HSV").split())
        channels[0] = channels[0].point(lambda x: int(((f / length / scale * loops + x / 256) % 1) * 256))
        temp = Image.merge("HSV", channels).convert("RGB")
        temp.putalpha(A)
        out.append(temp)
    return dict(duration=total * scale, frames=out)

def rainbow_gif(image, duration):
    try:
        image.seek(1)
    except EOFError:
        image.seek(0)
    else:
        return rainbow_gif2(image, duration)
    ts = round(time.time() * 1000)
    image = resize_max(image, 512, resample=Image.HAMMING)
    size = list(image.size)
    if duration == 0:
        fps = 0
    else:
        fps = round(32 / abs(duration))
    rate = 8
    while fps > 24 and rate < 32:
        fps >>= 1
        rate <<= 1
    if fps <= 0:
        raise ValueError("Invalid framerate value.")
    # Make sure image is in RGB/HSV format
    if str(image.mode) != "HSV":
        curr = image.convert("HSV")
        if str(image.mode) == "RGBA":
            A = image.getchannel("A")
        else:
            A = None
    else:
        curr = image
        A = None
    channels = list(curr.split())
    if duration < 0:
        rate = -rate
    out = collections.deque()
    # Repeatedly hueshift image and return copies
    func = lambda x: (x + rate) & 255
    for i in range(0, 256, abs(rate)):
        if i:
            channels[0] = channels[0].point(func)
            image = Image.merge("HSV", channels).convert("RGBA")
            if A is not None:
                image.putalpha(A)
        out.append(image)
    return dict(duration=1000 / fps * len(out), frames=out)


# def magik(image):
#     w = wand.image.Image(file=image)
#     w.format = "png"
#     w.alpha_channel = True
#     if w.size >= (2048, 2048):
#         raise OverflowError("image size too large.")
#     w.transform(resize='512x512>')
#     w.liquid_rescale(width=int(w.width * 0.5), height=int(w.height * 0.5), delta_x=1, rigidity=0)
#     w.liquid_rescale(width=int(w.width * 1.5), height=int(w.height * 1.5), delta_x=2, rigidity=0)
#     out = io.BytesIO()
#     w.save(file=out)
#     out.seek(0)
#     list_imgs.append(out)


# Autodetect max image size, keeping aspect ratio
def max_size(w, h, maxsize):
    s = w * h
    m = (maxsize * maxsize << 1) / 3
    if s > m:
        r = (m / s) ** 0.5
        w = int(w * r)
        h = int(h * r)
    return w, h

def resize_max(image, maxsize, resample=Image.LANCZOS, box=None, reducing_gap=None):
    w, h = max_size(image.width, image.height, maxsize)
    if w != image.width or h != image.height:
        if type(resample) is str:
            image = resize_to(image, w, h, resample)
        else:
            image = image.resize([w, h], resample, box, reducing_gap)
    return image

resizers = {
    "sinc": Image.LANCZOS,
    "lanczos": Image.LANCZOS,
    "cubic": Image.BICUBIC,
    "bicubic": Image.BICUBIC,
    "hamming": Image.HAMMING,
    "linear": Image.BILINEAR,
    "bilinear": Image.BILINEAR,
    "nearest": Image.NEAREST,
    "nearestneighbour": Image.NEAREST,
}

def resize_mult(image, x, y, operation):
    if x == y == 1:
        return image
    w = image.width * x
    h = image.height * y
    return resize_to(image, round(w), round(h), operation)

def resize_to(image, w, h, operation="auto"):
    if abs(w * h) > 16777216:
        raise OverflowError("Resulting image size too large.")
    if w == image.width and h == image.height:
        return image
    op = operation.lower().replace(" ", "").replace("_", "")
    if op in resizers:
        filt = resizers[op]
    elif op == "auto":
        # Choose resampling algorithm based on source/destination image sizes
        m = min(abs(w), abs(h))
        n = min(image.width, image.height)
        if n > m:
            m = n
        if m <= 64:
            filt = Image.NEAREST
        elif m <= 256:
            filt = Image.HAMMING
        elif m <= 2048:
            filt = Image.LANCZOS
        elif m <= 3072:
            filt = Image.BICUBIC
        else:
            filt = Image.BILINEAR
    else:
        raise TypeError("Invalid image operation: \"" + op + '"')
    return image.resize([w, h], filt)


channel_map = {
    "alpha": -1,
    "a": -1,
    "red": 0,
    "r": 0,
    "green": 1,
    "g": 1,
    "blue": 2,
    "b": 2,
    "cyan": 3,
    "c": 3,
    "magenta": 4,
    "m": 4,
    "yellow": 5,
    "y": 5,
    "hue": 6,
    "h": 6,
    "saturation": 7,
    "sat": 7,
    "s": 7,
    "luminance": 8,
    "lum": 8,
    "l": 8,
    "v": 8
}

def fill_channels(image, colour, *channels):
    channels = list(channels)
    ops = {}
    for c in channels:
        try:
            cid = channel_map[c]
        except KeyError:
            if len(c) <= 1:
                raise TypeError("invalid colour identifier: " + c)
            channels.extend(c)
        else:
            ops[cid] = None
    ch = Image.new("L", image.size, colour)
    if "RGB" not in str(image.mode):
        image = image.convert("RGB")
    if -1 in ops:
        image.putalpha(ch)
    mode = image.mode
    rgb = False
    for i in range(3):
        if i in ops:
            rgb = True
    if rgb:
        spl = list(image.split())
        for i in range(3):
            if i in ops:
                spl[i] = ch
        image = Image.merge(mode, spl)
    cmy = False
    for i in range(3, 6):
        if i in ops:
            cmy = True
    if cmy:
        spl = list(ImageChops.invert(image).split())
        for i in range(3, 6):
            if i in ops:
                spl[i - 3] = ch
        image = ImageChops.invert(Image.merge(mode, spl))
    hsv = False
    for i in range(6, 9):
        if i in ops:
            hsv = True
    if hsv:
        if str(image.mode) == "RGBA":
            A = image.getchannel("A")
        else:
            A = None
        spl = list(image.convert("HSV").split())
        for i in range(6, 9):
            if i in ops:
                spl[i - 6] = ch
        image = Image.merge("HSV", spl).convert("RGB")
        if A is not None:
            image.putalpha(A)
    return image


# Image blend operations (this is a bit of a mess)
blenders = {
    "normal": "blend",
    "blt": "blend",
    "blit": "blend",
    "blend": "blend",
    "replace": "blend",
    "+": "add",
    "add": "add",
    "addition": "add",
    "-": "subtract",
    "sub": "subtract",
    "subtract": "subtract",
    "subtraction": "subtract",
    "*": "multiply",
    "mul": "multiply",
    "mult": "multiply",
    "multiply": "multiply",
    "multiplication": "multiply",
    "/": blend_modes.divide,
    "div": blend_modes.divide,
    "divide": blend_modes.divide,
    "division": blend_modes.divide,
    "mod": "OP_X%Y",
    "modulo": "OP_X%Y",
    "%": "OP_X%Y",
    "and": "OP_X&Y",
    "&": "OP_X&Y",
    "or": "OP_X|Y",
    "|": "OP_X|Y",
    "xor": "OP_X^Y",
    "^": "OP_X^Y",
    "nand": "OP_255-(X&Y)",
    "~&": "OP_255-(X&Y)",
    "nor": "OP_255-(X|Y)",
    "~|": "OP_255-(X|Y)",
    "xnor": "OP_255-(X^Y)",
    "~^": "OP_255-(X^Y)",
    "xand": "OP_255-(X^Y)",
    "diff": "difference",
    "difference": "difference",
    "overlay": "overlay",
    "screen": "screen",
    "soft": "soft_light",
    "softlight": "soft_light",
    "hard": "hard_light",
    "hardlight": "hard_light",
    "lighter": "lighter",
    "lighten": "lighter",
    "darker": "darker",
    "darken": "darker",
    "extract": blend_modes.grain_extract,
    "grainextract": blend_modes.grain_extract,
    "merge": blend_modes.grain_merge,
    "grainmerge": blend_modes.grain_merge,
    "burn": "OP_255*(1-((255-Y)/X))",
    "colorburn": "OP_255*(1-((255-Y)/X))",
    "colourburn": "OP_255*(1-((255-Y)/X))",
    "linearburn": "OP_(X+Y)-255",
    "dodge": blend_modes.dodge,
    "colordodge": blend_modes.dodge,
    "colourdodge": blend_modes.dodge,
    "lineardodge": "add",
    "hue": "SP_HUE",
    "sat": "SP_SAT",
    "saturation": "SP_SAT",
    "lum": "SP_LUM",
    "luminosity": "SP_LUM",
}

def blend_op(image, url, operation, amount, recursive=True):
    op = operation.lower().replace(" ", "").replace("_", "")
    if op in blenders:
        filt = blenders[op]
    elif op == "auto":
        filt = "blend"
    else:
        raise TypeError("Invalid image operation: \"" + op + '"')
    image2 = get_image(url, url)
    if recursive:
        if not globals()["ANIM"]:
            try:
                image2.seek(1)
            except EOFError:
                image2.seek(0)
            else:
                out = collections.deque()
                for f in range(2147483648):
                    try:
                        image2.seek(f)
                    except EOFError:
                        break
                    if str(image.mode) != "RGBA":
                        temp = image.convert("RGBA")
                    else:
                        temp = image
                    out.append(blend_op(temp, image2, operation, amount, recursive=False))
                return out
        try:
            n_frames = 1
            for f in range(CURRENT_FRAME + 1):
                try:
                    image2.seek(f)
                except EOFError:
                    break
                n_frames += 1
            image2.seek(CURRENT_FRAME % n_frames)
        except EOFError:
            image2.seek(0)
    if image2.width != image.width or image2.height != image.height:
        image2 = resize_to(image2, image.width, image.height, "auto")
    if type(filt) is not str:
        if str(image.mode) != "RGBA":
            image = image.convert("RGBA")
        if str(image2.mode) != "RGBA":
            image2 = image2.convert("RGBA")
        imgA = numpy.array(image).astype(float)
        imgB = numpy.array(image2).astype(float)
        out = Image.fromarray(numpy.uint8(filt(imgA, imgB, amount)))
    else:
        # Basic blend, use second image
        if filt == "blend":
            out = image2
        # Image operation, use ImageMath.eval
        elif filt.startswith("OP_"):
            f = filt[3:]
            if str(image.mode) != str(image2.mode):
                if str(image.mode) != "RGBA":
                    image = image.convert("RGBA")
                if str(image2.mode) != "RGBA":
                    image2 = image2.convert("RGBA")
            mode = image.mode
            ch1 = image.split()
            ch2 = image2.split()
            c = len(ch1)
            ch3 = [ImageMath.eval(f, dict(X=ch1[i], Y=ch2[i])).convert("L") for i in range(3)]
            if c > 3:
                ch3.append(ImageMath.eval("max(X,Y)", dict(X=ch1[-1], Y=ch2[-1])).convert("L"))
            out = Image.merge(mode, ch3)
        # Special operation, use HSV channels
        elif filt.startswith("SP_"):
            f = filt[3:]
            if str(image.mode) == "RGBA":
                A1 = image.getchannel("A")
            else:
                A1 = None
            if str(image2.mode) == "RGBA":
                A2 = image2.getchannel("A")
            else:
                A2 = None
            if str(image.mode) != "HSV":
                image = image.convert("HSV")
            channels = list(image.split())
            if str(image2.mode) != "HSV":
                image2 = image2.convert("HSV")
            channels2 = list(image2.split())
            if f == "HUE":
                channels = [channels2[0], channels[1], channels[2]]
            elif f == "SAT":
                channels = [channels[0], channels2[1], channels[2]]
            elif f == "LUM":
                channels = [channels[0], channels[1], channels2[2]]
            out = Image.merge("HSV", channels).convert("RGB")
            if A1 or A2:
                if not A1:
                    A = A2
                elif not A2:
                    A = A1
                else:
                    A = ImageMath.eval("max(X,Y)", dict(X=A1, Y=A2)).convert("L")
                out.putalpha(A)
        # Otherwise attempt to find as ImageChops filter
        else:
            if str(image.mode) != str(image2.mode):
                if str(image.mode) != "RGBA":
                    image = image.convert("RGBA")
                if str(image2.mode) != "RGBA":
                    image2 = image2.convert("RGBA")
            filt = getattr(ImageChops, filt)
            out = filt(image, image2)
        if str(image.mode) != str(out.mode):
            if str(image.mode) != "RGBA":
                image = image.convert("RGBA")
            if str(out.mode) != "RGBA":
                out = out.convert("RGBA")
        # Blend two images
        out = ImageChops.blend(image, out, amount)
    return out

# def ColourDeficiency(image, operation, value):
#     pass

Enhance = lambda image, operation, value: getattr(ImageEnhance, operation)(image).enhance(value)

# Hueshift image using HSV channels
def hue_shift(image, value):
    if str(image.mode) == "RGBA":
        A = image.getchannel("A")
    else:
        A = None
    if str(image.mode) != "HSV":
        image = image.convert("HSV")
    channels = list(image.split())
    value *= 256
    channels[0] = channels[0].point(lambda x: (x + value) % 256)
    image = Image.merge("HSV", channels).convert("RGB")
    if A is not None:
        image.putalpha(A)
    return image


def get_image(url, out):
    if issubclass(type(url), Image.Image):
        return url
    if type(url) not in (bytes, bytearray, io.BytesIO):
        if url in CACHE:
            return CACHE[url]
        if isURL(url):
            with requests.get(url, stream=True, timeout=8) as resp:
                data = resp.content
            if len(data) > 67108864:
                raise OverflowError("Max file size to load is 64MB.")
        else:
            if os.path.getsize(url) > 67108864:
                raise OverflowError("Max file size to load is 64MB.")
            with open(url, "rb") as f:
                data = f.read()
            if out != url and out:
                try:
                    os.remove(url)
                except:
                    pass
        image = Image.open(io.BytesIO(data))
        CACHE[url] = image
    else:
        if len(url) > 67108864:
            raise OverflowError("Max file size to load is 64MB.")
        image = Image.open(io.BytesIO(url))
    return image


# Main image operation function
@logging
def evalImg(url, operation, args):
    globals()["CURRENT_FRAME"] = 0
    ts = round(time.time() * 1000)
    out = "cache/" + str(ts) + ".png"
    args = eval(args)
    if operation != "$":
        if args[-1] == "$%RAW%$":
            args.pop(-1)
            image = requests.get(url, timeout=8).content
        else:
            image = get_image(url, out)
        # $%GIF%$ is a special case where the output is always a .gif image
        if args[-1] == "$%GIF%$":
            new = eval(operation)(image, *args[:-1])
        else:
            try:
                image.seek(1)
            except EOFError:
                new = None
                globals()["ANIM"] = False
            else:
                new = dict(frames=collections.deque(), duration=0)
                globals()["ANIM"] = True
            # Attempt to perform operation on all individual frames of .gif images
            for f in range(2147483648):
                globals()["CURRENT_FRAME"] = f
                try:
                    image.seek(f)
                except EOFError:
                    break
                if str(image.mode) != "RGBA":
                    temp = image.convert("RGBA")
                else:
                    temp = image
                if new is not None:
                    new["duration"] += temp.info.get("duration", 1 / 60)
                func = getattr(temp, operation, None)
                if func is None:
                    res = eval(operation)(temp, *args)
                else:
                    res = func(*args)
                if new is None:
                    new = res
                    break
                elif issubclass(type(res), Image.Image):
                    new["frames"].append(res)
                else:
                    new["frames"].extend(res)
    else:
        new = eval(url)(*args)
    filePrint(new)
    if type(new) is dict:
        duration = new["duration"]
        new = new["frames"]
        if not new:
            raise EOFError("No image output detected.")
        elif len(new) == 1:
            new = new[0]
        else:
            size = new[0].size
            out = "cache/" + str(ts) + ".gif"
            command = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "rawvideo", "-r", str(1000 * len(new) / duration), "-pix_fmt", "rgba", "-video_size", "x".join(str(i) for i in size), "-i", "-"]
            command.extend(["-fs", str(8388608 - 262144), "-an", "-vf", "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse", "-loop", "0", out])
            proc = psutil.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            for frame in new:
                if issubclass(type(frame), Image.Image):
                    if frame.size != size:
                        frame = frame.resize(size)
                    if str(frame.mode) != "RGBA":
                        frame = frame.convert("RGBA")
                    b = frame.tobytes()
                    # arr = numpy.array(frame)
                    # b = arr.tobytes()
                elif type(frame) is io.BytesIO:
                    b = frame.read()
                else:
                    b = frame
                proc.stdin.write(b)
                time.sleep(0.02)
            proc.stdin.close()
            proc.wait()
            return repr([out])
    if issubclass(type(new), Image.Image):
        new.save(out, "png")
        return repr([out])
    elif type(new) is str and new.startswith("$"):
        return repr([new[1:]])
    return repr(str(new).encode("utf-8"))


if __name__ == "__main__":
    # SHA256 key always taken on startup
    key = eval(sys.stdin.readline()).decode("utf-8", "replace").strip()
    while True:
        try:
            args = eval(sys.stdin.readline()).decode("utf-8", "replace").strip().split("`")
            resp = evalImg(*args)
            sys.stdout.write(repr(resp.encode("utf-8")) + "\n")
            sys.stdout.flush()
        except Exception as ex:
            # Exceptions are evaluated and handled by main process
            sys.stdout.write(repr(ex) + "\n")
            sys.stdout.flush()
        time.sleep(0.01)
        if time.time() - start > 3600:
            start = time.time()
            for img in CACHE.values():
                img.close()
            CACHE.clear()
