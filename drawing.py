import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
import asyncio
import textwrap
import os
import math
import aiohttp
from copy import copy
try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor
    pil_available = True
except:
    pil_available = False


class Drawing:
    """Draw images and text"""

    def __init__(self, bot):
        self.bot = bot
        self.drawing_settings = fileIO("data/drawing/settings.json", "load")

        # check for settings migrations
        # clear prev settings   
        if "background" in self.drawing_settings.keys():
            self.drawing_settings.pop("background", None)

        # build new ones    
        if "userbar" not in self.drawing_settings.keys():
            self.drawing_settings["userbar"] = {}
            for server in self.bot.servers:
                self.drawing_settings["userbar"][server.id] = {
                    "background" : "data/drawing/bg.png"
                }
            self.drawing_settings.pop("background", None)
            fileIO("data/drawing/settings.json", "save", self.drawing_settings)

        # clear prev settings   
        if "bot_sign" in self.drawing_settings.keys():
            self.drawing_settings.pop("bot_sign", None)

        # build new ones
        if "text" not in self.drawing_settings.keys():
            self.drawing_settings["text"] = {}
            for server in self.bot.servers:
                self.drawing_settings["text"][server.id] = {
                    "bot_sign" : "Tarik"
                }
            
            fileIO("data/drawing/settings.json", "save", self.drawing_settings)

        # clear prev settings
        if "build" in self.drawing_settings.keys() and "youtube" in self.drawing_settings["build"].keys():
            self.drawing_settings.pop("build", None)

        # build new ones
        if "build" not in self.drawing_settings.keys():
            self.drawing_settings["build"] = {}
            for server in self.bot.servers:
                self.drawing_settings["build"][server.id] = {
                    "youtube" : {
                        "frame" : "white",
                        "small" : False
                    }
                }
            fileIO("data/drawing/settings.json", "save", self.drawing_settings)
                
        self.version = "1.4.2"
        self.update_type = "fix"
        self.patchnote = """
**Per-server settings are here!**

Now all the settings are controlled on a per-server basis, no need to worry about having the same userbar background for all the servers.

**IMPORTANT** you will need to set background and bot_sign once again with `[p]drawing setsign` and `[p]drawing setbg` commands.

Due to the latest updates to `downloader` settings won't be wiped anymore after the cog update. **YOU WILL NEED TO UPDATE THE BOT** to get this fix.

**Now all the users wigh `manage server` permission can change bot settings for their server**

Hope you like this little new addition!

More to come!
"""

    @commands.group(pass_context = True)
    async def drawing(self, ctx):
        """Returns info about the cog"""

        if ctx.invoked_subcommand is None:
            await self.bot.say("Type help drawing for info.")

    @drawing.command()
    async def info(self):
        """Returns the current version and patchnotes"""
        
        message = "Current cog version: **" + self.version + "**\n"
        message += "Patchnotes:"
        message += self.patchnote

        await self.bot.say(message)

    @drawing.command()
    async def ver(self):
        """Returns the current version"""

        message = "Current cog version: **" + self.version + "** (" + self.update_type + ")\n"
        message += "For patchnotes use `" + self.bot.command_prefix[0] + "drawing info`"
        await self.bot.say(message)

    @drawing.command(pass_context = True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def setsign(self, ctx, *, sign):
        """Sets the name which would be displayed on images generated by [p]text
        If set to 'username' will use username of a person using the command"""

        # check the length
        if len(sign.strip()) <= 40:
            self.drawing_settings["text"][ctx.message.server.id]["bot_sign"] = sign.strip()
            fileIO("data/drawing/settings.json", "save", self.drawing_settings)
            await self.bot.say("I will now use " + sign.strip() + " as a sign")
        else:
            await self.bot.say("Please choose a shorter sign")

    @drawing.command(pass_context = True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def setbg(self, ctx, default = None):
        """Sets the background for [p]text and [p] userbar"""

        # check if we want to reset
        if default is not None:
            self.drawing_settings["userbar"][ctx.message.server.id]["background"] = "data/drawing/bg.png"
            fileIO("data/drawing/settings.json", "save", self.drawing_settings)
            await self.bot.say("I will now use default image as a background")

        else:

            # request image from user
            await self.bot.say("Please send the background. It should be 400x100")
            answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)

            # get the image from message
            try:        
                bg_url = answer.attachments[0]["url"]
                success = True
            except Exception as e:
                success = False
                print(e)

            bg_image = Image

            if success:

                # download the image
                try:
                    async with aiohttp.get(bg_url) as r:
                        image = await r.content.read()
                        if not os.path.exists("data/drawing/" + ctx.message.server.id):
                            os.makedirs("data/drawing/" + ctx.message.server.id)
                    with open('data/drawing/' + ctx.message.server.id + '/custom_bg','wb') as f:
                        f.write(image)
                        bg_image = Image.open('data/drawing/' + ctx.message.server.id + '/custom_bg').convert('RGBA')
                        success = True

                except Exception as e:
                    success = False
                    print(e)

                if success:

                    # check dimensions
                    if bg_image.size == (400,100):
                        self.drawing_settings["userbar"][ctx.message.server.id]["background"] = "data/drawing/" + ctx.message.server.id + "/custom_bg"
                        fileIO("data/drawing/settings.json", "save", self.drawing_settings)
                        await self.bot.say("I will now use this image as a background")
                    else:
                        await self.bot.say("Image has wrong dimension, please provide 400x100 image")
                else:
                    await self.bot.say("Couldn't get the image from Discord")
            else:
                await self.bot.say("Couldn't get the image")

    @commands.command(pass_context = True)
    async def text(self, ctx, *, text):
        """Draws text on a background"""

        # check text length

        if len(text) > 24:
            await self.bot.say("Too big for me")
        else:

            result = Image.open(self.drawing_settings["userbar"][ctx.message.server.id]["background"]).convert('RGBA')

            process = Image.new('RGBA', (400,100), (0,0,0))

            # get a font
            fnt = ImageFont.truetype('data/drawing/font.ttf', 37)
            fnt_sm = ImageFont.truetype('data/drawing/font.ttf', 20)

            # get a drawing context
            d = ImageDraw.Draw(process)

            # get sign
            sign = self.drawing_settings["text"][ctx.message.server.id]["bot_sign"]
            if sign == "username":
                sign = ctx.message.author.name

            # calculate text position
            author_width = fnt_sm.getsize("— " + sign)[0]

            # draw text, half opacity
            d.rectangle([(0,0),(400,100)], fill=(0,0,0,160))
            d.text((25,25), "«" + text + "»", font=fnt, fill=(255,255,255,255))
            d.text((400 - author_width - 25, 65), "— " + sign, font=fnt_sm, fill=(255,255,255,128))
            d.rectangle([(10,10),(390,90)], fill=None, outline=(200,200,200,128))

            result = Image.alpha_composite(result, process)

            result.save('data/drawing/temp.jpg','JPEG', quality=100)

            await self.bot.send_file(ctx.message.channel, 'data/drawing/temp.jpg')

            os.remove('data/drawing/temp.jpg')

    @commands.group(pass_context = True)
    async def build(self, ctx):
        """Generates fancy images"""

        if ctx.invoked_subcommand is None:
            await self.bot.say("Type help build for info.")

    @build.command(pass_context = True)
    async def meme(self, ctx):
        """Meme builder."""

        await self.bot.say("Please send the background")
        answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)        
        bg_url = answer.attachments[0]["url"]
        bg_image = Image

        success = False
        try:
            async with aiohttp.get(bg_url) as r:
                image = await r.content.read()
            with open('data/drawing/temp_bg','wb') as f:
                f.write(image)
                bg_image = Image.open('data/drawing/temp_bg').convert('RGBA')
                success = True

        except Exception as e:
            success = False
            print(e)
            

        if success:
            # define vars
            title = ""
            subtitle = ""

            # get vars
            await self.bot.say("Please type first line of text")
            answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
            title = answer.content.lower().strip()

            await self.bot.say("Please type second line of text")
            answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
            subtitle = answer.content.lower().strip()

            # check text length
            if len(title) < 30 and len(subtitle) < 40:
                    
                result = bg_image

                new_width = 650
                new_height = int(math.floor((result.size[1] / result.size[0]) * new_width))


                if new_height < 366:
                    new_height = 366
                    new_width = int(math.floor((result.size[0] / result.size[1]) * new_height))

                half_width = int(math.floor(new_width / 2))
                half_height = int(math.floor(new_height /2))

                result = result.resize(size=(new_width, new_height), resample=Image.LANCZOS)
                print("Feature dimensions", new_width, "by", new_height)

                process = Image.new('RGBA', (new_width,new_height), (0,0,0))
                print("Overlay dimensions", process.size)
                print("Modes are", result.mode, "and", process.mode)

                # get a font
                fnt_meme = ImageFont.truetype('data/drawing/font_bold.ttf', 55)
                # get a drawing context
                d = ImageDraw.Draw(process)

                # haax
                d.rectangle([(0,0),(new_width,new_height)], fill=(0,0,0,0))

                # calculate text positions
                title_pos = int(math.floor(fnt_meme.getsize(title)[0] / 2))
                subtitle_pos = int(math.floor(fnt_meme.getsize(subtitle)[0] / 2))

                # dark bgs
                d.rectangle([(10,10),(new_width - 10,80)], fill=(0,0,0,160))
                d.rectangle([(10, new_height - 80),(new_width - 10, new_height - 10)], fill=(0,0,0,160))
                
                # text
                d.text((half_width - title_pos, 25), title, font=fnt_meme, fill=(255,255,255,255))
                d.text((half_width - subtitle_pos, new_height - 65), subtitle, font=fnt_meme, fill=(255,255,255,255))

                # blend bg and text
                result = Image.alpha_composite(result, process)

                # save and send
                result.save('data/drawing/temp.jpg','JPEG', quality=100)
                await self.bot.send_file(ctx.message.channel, 'data/drawing/temp.jpg')

                # cleanup
                os.remove('data/drawing/temp.jpg')
                os.remove('data/drawing/temp_bg')

            else:
                # pun intended
                await self.bot.say("Too big for me")

        else:
            await self.bot.say("Error getting image")

    @build.command(pass_context = True)
    async def feature(self, ctx):
        """Fancy features builder"""

        await self.bot.say("Please send the bg image")
        answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)        
        bg_url = answer.attachments[0]["url"]
        bg_image = Image

        success = False
        try:
            async with aiohttp.get(bg_url) as r:
                image = await r.content.read()
            with open('data/drawing/temp_bg','wb') as f:
                f.write(image)
                bg_image = Image.open('data/drawing/temp_bg').convert('RGBA')
                success = True

        except Exception as e:
            success = False
            print(e)
            

        if success:
            # define vars
            title = ""
            subtitle = ""

            # get vars
            await self.bot.say("Please type title")
            answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
            title = answer.content.lower().strip()

            await self.bot.say("Please type subtitle")
            answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
            subtitle = answer.content.lower().strip()

            # check text length
            if len(title) < 30 and len(subtitle) < 40:
                    
                result = bg_image

                new_width = 650
                new_height = int(math.floor((result.size[1] / result.size[0]) * new_width))


                if new_height < 366:
                    new_height = 366
                    new_width = int(math.floor((result.size[0] / result.size[1]) * new_height))

                half_width = int(math.floor(new_width / 2))
                half_height = int(math.floor(new_height /2))

                result = result.resize(size=(new_width, new_height))
                print("Feature dimensions", new_width, "by", new_height)

                process = Image.new('RGBA', (new_width,new_height), (0,0,0))
                print("Overlay dimensions", process.size)
                print("Modes are", result.mode, "and", process.mode)

                # get a font
                fnt = ImageFont.truetype('data/drawing/font.ttf', 70)
                fnt_sm = ImageFont.truetype('data/drawing/font.ttf', 40)
                fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 70)
                fnt_meme = ImageFont.truetype('data/drawing/font_bold.ttf', 55)
                # get a drawing context
                d = ImageDraw.Draw(process)

                # calculate text sizes and positions
                author_pos = int(math.floor(fnt_sm.getsize(ctx.message.author.name)[0] / 2))
                title_pos = int(math.floor(fnt_b.getsize(title)[0] / 2))
                subtitle_pos = int(math.floor(fnt_sm.getsize(subtitle)[0] / 2))

                # dark filter
                d.rectangle([(0,0),(new_width,new_height)], fill=(0,0,0,140))

                # darker inner
                d.rectangle([(20,20),(new_width - 20, new_height - 20)], fill=(0,0,0,180), outline=(200,200,200,128))

                # text
                d.text((half_width - author_pos, half_height - 60), ctx.message.author.name, font=fnt_sm, fill=(255,255,255,255))
                d.text((half_width - title_pos, half_height - 20), title, font=fnt_b, fill=(255,255,255,255))
                d.text((half_width - subtitle_pos, half_height + 40), subtitle, font=fnt_sm, fill=(255,255,255,255))

                result = Image.alpha_composite(result, process)

                # save and send
                result.save('data/drawing/temp.jpg','JPEG', quality=100)
                await self.bot.send_file(ctx.message.channel, 'data/drawing/temp.jpg')

                # cleanup
                os.remove('data/drawing/temp.jpg')
                os.remove('data/drawing/temp_bg')

            else:
                # pun intended
                await self.bot.say("Too big for me")

        else:
            await self.bot.say("Error getting image")

    @build.command(pass_context = True)
    async def screen(self, ctx, game = None, cut_window = None):
        """Personalized image branding with widow borders as an option"""

        await self.bot.say("Please send the screenshot")
        answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)        
        bg_url = answer.attachments[0]["url"]
        bg_image = Image

        success = False
        try:
            async with aiohttp.get(bg_url) as r:
                image = await r.content.read()
            with open('data/drawing/temp_bg','wb') as f:
                f.write(image)
                bg_image = Image.open('data/drawing/temp_bg').convert('RGBA')
                success = True

        except Exception as e:
            success = False
            print(e)
            

        if success:
                    
            # will draw on source
            result = bg_image

            half_width = int(math.floor(result.size[0] / 2))
            half_height = int(math.floor(result.size[1] /2))

            # if need to cut window borders - do so
            if cut_window is not None:
                result = result.crop((1,31,result.size[0] - 1, result.size[1] - 1))

            width = result.size[0]
            height = result.size[1]

            # create a new canvas
            process = Image.new('RGBA', (width, height), (0,0,0))

            # get fonts
            fnt = ImageFont.truetype('data/drawing/font.ttf', 30)
            fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 40)

            # get a drawing context
            d = ImageDraw.Draw(process)

            #haax
            d.rectangle([(0,0),(width, height)], fill=(0,0,0,0))

            # calculate text sizes and positions
            author_width = fnt_b.getsize(ctx.message.author.name)[0]

            # dark overlay
            d.rectangle([(0,height - 70),(width,height)], fill=(0,0,0,140))

            # text
            d.text((20, height - 50), ctx.message.author.name, font=fnt_b, fill=(255,255,255,255))
            d.text((20 + author_width + 20, height - 47), "#" + ctx.message.author.discriminator, font=fnt, fill=(255,255,255,200))

            # if provided a game name - draw it
            if game is not None:
                game_width = fnt_b.getsize(game.strip())[0]
                d.text((width - game_width - 20, height - 50), game.strip(), font=fnt_b, fill=(255,255,255,255))

            result = Image.alpha_composite(result, process)

            # save and send
            result.save('data/drawing/temp.jpg','JPEG', quality=100)
            await self.bot.send_file(ctx.message.channel, 'data/drawing/temp.jpg')

            # cleanup
            os.remove('data/drawing/temp.jpg')
            os.remove('data/drawing/temp_bg')

        else:
            await self.bot.say("Error getting image")

    @build.command(pass_context = True)
    async def yt(self, ctx, small = "", border = "white"):
        """Builds youtube videos thumbnails
        add 'small' for making the text more compact
        you can also change frame color by adding color as the second option, e.g. [p]build yt \"\" #ff00ff
        \"\" in the example above is needed to ignore the 'small' option
        """

        await self.bot.say("Please send the background")
        answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)        
        
        # get the image from message
        try:        
            bg_url = answer.attachments[0]["url"]
            success = True
        except Exception as e:
            success = False
            print(e)

        bg_image = Image

        if success:

            # get the image from discord
            success = False
            try:
                async with aiohttp.get(bg_url) as r:
                    image = await r.content.read()
                with open('data/drawing/temp_bg','wb') as f:
                    f.write(image)
                    bg_image = Image.open('data/drawing/temp_bg').convert('RGBA')
                    success = True

            except Exception as e:
                success = False
                print(e)

            if success:

                # check image size
                if bg_image.size[0] >= 1280 and bg_image.size[1] >= 720:

                    # define vars
                    title = ""

                    # get vars
                    await self.bot.say("Please type title")
                    answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)
                    title = answer.content.lower().strip()

                    # check text length
                    if len(title) < 35:

                        # crop source for 16:9
                        cropped_height = int(math.floor((9 / 16) * bg_image.size[0]))

                        # calculate crop box
                        crop = (
                            0,
                            int(math.floor((bg_image.size[1] / 2) - (cropped_height / 2))),
                            bg_image.size[0],
                            int(math.floor((bg_image.size[1] / 2) + (cropped_height / 2)))
                        )

                        bg_image = bg_image.crop(crop)

                        # resize if needed
                        if bg_image.size[0] > 1280:
                            bg_image = bg_image.resize((1280,720), resample = Image.LANCZOS)

                        # will draw on source
                        result = bg_image

                        half_width = int(math.floor(result.size[0] / 2))
                        half_height = int(math.floor(result.size[1] /2))

                        width = result.size[0]
                        height = result.size[1]

                        # create a new canvas
                        process = Image.new('RGBA', (width, height), (0,0,0,0))

                        # get a drawing context
                        d = ImageDraw.Draw(process)

                        #filter
                        d.rectangle([(0,0),(width, height)], fill=(0,0,0,160))

                        # check if needed to be small
                        if len(small) == 0:
                            # check small-style settings
                            if "youtube" in self.drawing_settings["build"][ctx.message.server.id].keys():
                                if "small" in self.drawing_settings["build"][ctx.message.server.id]["youtube"].keys() and self.drawing_settings["build"][ctx.message.server.id]["youtube"]["small"] is True:
                                    # get fonts
                                    fnt = ImageFont.truetype('data/drawing/font_bold.ttf', 80)
                                    fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 120)
                                else:
                                    fnt = ImageFont.truetype('data/drawing/font_bold.ttf', 120)
                                    fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 190)
                            else:
                                # get fonts
                                fnt = ImageFont.truetype('data/drawing/font_bold.ttf', 120)
                                fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 190)
                        else:
                            # get fonts
                            fnt = ImageFont.truetype('data/drawing/font_bold.ttf', 80)
                            fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 120)

                        # wrap text
                        title = title.strip()
                        if d.multiline_textsize(title, font=fnt_b)[0] > 1080:
                            title = textwrap.fill(title, 18)

                        # calculate text sizes and positions
                        if d.multiline_textsize(title, font=fnt_b)[1] > 250 and len(small) == 0:
                            title_pos_x = half_width - int(math.floor(d.multiline_textsize(title, font=fnt_b)[0] / 2))
                            title_pos_y = half_height - int(math.floor(d.multiline_textsize(title, font=fnt_b)[1] / 2)) + 90
                            author_pos_x = half_width - int(math.floor(d.textsize(ctx.message.author.name, font=fnt)[0] / 2))
                            author_pos_y = half_height - int(math.floor(d.textsize(ctx.message.author.name, font=fnt)[1] / 2)) - 125
                        else:
                            title_pos_x = half_width - int(math.floor(fnt_b.getsize(title)[0] / 2))
                            title_pos_y = half_height + int(math.floor(fnt_b.getsize(title)[1] / 2)) - 100
                            author_pos_x = half_width - int(math.floor(d.textsize(ctx.message.author.name, font=fnt)[0] / 2))
                            author_pos_y = half_height - int(math.floor(d.textsize(ctx.message.author.name, font=fnt)[1] / 2)) - 75

                        author_width = fnt_b.getsize(ctx.message.author.name)[0]
                       

                        # check frame settings
                        if "youtube" in self.drawing_settings["build"][ctx.message.server.id].keys():
                            if "frame" in self.drawing_settings["build"][ctx.message.server.id]["youtube"].keys():
                                border = self.drawing_settings["build"][ctx.message.server.id]["youtube"]["frame"]

                        # get frame color
                        c = ImageColor.getrgb(border.strip())
                        border_color = (c[0],c[1],c[2],255)

                        # draw frame
                        d.rectangle([(20,20), (width - 20, height - 20)], fill=border_color)
                        d.rectangle([(30,30),(width - 30, height - 30)], fill=(0,0,0,160))


                        # text
                        if len(small) == 0:
                            # check small-style settings
                            if "youtube" in self.drawing_settings["build"][ctx.message.server.id].keys():
                                if "small" in self.drawing_settings["build"][ctx.message.server.id]["youtube"].keys() and self.drawing_settings["build"][ctx.message.server.id]["youtube"]["small"] is True:
                                    d.text((70, author_pos_y + 210), ctx.message.author.name, font=fnt, fill=(255,255,255,210))
                                    d.text((70, title_pos_y + 230), title, font=fnt_b, fill=(255,255,255,210))
                                else:
                                    d.text((author_pos_x, author_pos_y), ctx.message.author.name, font=fnt, fill=(255,255,255,210))
                                    d.text((title_pos_x, title_pos_y), title, font=fnt_b, fill=(255,255,255,210))
                            else:
                                d.text((author_pos_x, author_pos_y), ctx.message.author.name, font=fnt, fill=(255,255,255,210))
                                d.text((title_pos_x, title_pos_y), title, font=fnt_b, fill=(255,255,255,210))
                        else:
                            d.text((70, author_pos_y + 210), ctx.message.author.name, font=fnt, fill=(255,255,255,210))
                            d.text((70, title_pos_y + 230), title, font=fnt_b, fill=(255,255,255,210))

                        result = Image.alpha_composite(result, process)

                        # save and send
                        result.save('data/drawing/temp.jpg','JPEG', quality=100)
                        await self.bot.send_file(ctx.message.channel, 'data/drawing/temp.jpg')

                        # cleanup
                        os.remove('data/drawing/temp.jpg')
                        os.remove('data/drawing/temp_bg')

                    else:
                        await self.bot.say("Too big for me")
                else:
                    await self.bot.say("Too small for me")
            else:
                await self.bot.say("Could not get the image from discord")
        else:
            await self.bot.say("Could not get the image from message")

    @build.group(name = 'set', pass_context = True)
    @checks.serverowner_or_permissions(manage_server=True)
    async def _set(self, ctx):
        """Configure build command"""

        if ctx.invoked_subcommand is None or isinstance(ctx.invoked_subcommand, commands.Group):
            await self.bot.say("Type help build set for info.")

    @_set.command(pass_context = True)
    async def youtube(self, ctx, option, *, value):
        """Change youtube builder options
        Options available:
            small [values: True, False]
            frame [values: color hexes and names]
        """

        options = {
            "small": {"type": "bool", "values": ["True", "False"]},
            "frame": {"type": "Any"}
        }

        option = option.strip()
        value = value.strip()

        if option in options.keys():
            if ("values" in options[option].keys() and value in options[option]["values"]) or options[option]["type"] == "Any":

                # type checking
                if options[option]["type"] == "bool":
                    if value == "True": value = True
                    else: value = False

                # check if setting exists
                if "youtube" not in self.drawing_settings["build"][ctx.message.server.id].keys():
                    self.drawing_settings["build"][ctx.message.server.id]["youtube"] = {}

                self.drawing_settings["build"][ctx.message.server.id]["youtube"][option] = value
                fileIO("data/drawing/settings.json", "save", self.drawing_settings)
                await self.bot.say("Option " +  str(option) + " for subcommand \"youtube\" was set to " + str(value))
            else:
                await self.bot.say("Please check help for possible values")
        else:
            await self.bot.say("Subcommand \"youtube\" doesn't have setting " +  option) 

    @commands.command(pass_context = True)
    async def userbar(self, ctx, background = None):
        """Generates a server-based userbar, you can provide a backround color as a hex, e.g. '#ff00ff', or name, e.g. 'teal' or 'white'"""

        # get an avatar
        avatar_url = ctx.message.author.avatar_url
        avatar_image = Image

        #get server icon
        server_url = ctx.message.server.icon_url
        server_image = Image

        # get images

        try:
            async with aiohttp.get(avatar_url) as r:
                image = await r.content.read()
            with open('data/drawing/temp_avatar','wb') as f:
                f.write(image)
                success = True
        except Exception as e:
            success = False
            print(e)

        try:
            async with aiohttp.get(server_url) as r:
                image = await r.content.read()
            with open('data/drawing/temp_server','wb') as f:
                f.write(image)
                success = True
        except Exception as e:
            success = False
            print(e)

        if success:

            # load images
            # check if avatar is present
            if len(avatar_url) == 0:
                avatar_image = Image.open('data/drawing/avatar.png').convert('RGBA')
            else:
                avatar_image = Image.open('data/drawing/temp_avatar').convert('RGBA')

            server_image = Image.open('data/drawing/temp_server').convert('RGBA')

            # get a font
            fnt = ImageFont.truetype('data/drawing/font.ttf', 25)
            fnt_sm = ImageFont.truetype('data/drawing/font.ttf', 18)
            fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 25)

            # set background
            bg_color = (0,0,0,255)
            if background is not None:
                
                if background  != "custom":
                    print(background)
                    c = ImageColor.getrgb(background.strip())
                    bg_color = (c[0],c[1],c[2],255)

            # prepare canvas to work with
            result = Image.new('RGBA', (400, 100), bg_color)
            process = Image.new('RGBA', (400, 100), bg_color)

            # get a drawing context
            d = ImageDraw.Draw(process)

            # haax
            d.rectangle([(0,0), (400,100)])

            # paste background (server icon) to final image if background is not provided
            if background is None:

                # check if custom background was set by the user
                if self.drawing_settings["userbar"][ctx.message.server.id]["background"] == "data/drawing/bg.png":
                    server_image = server_image.resize(size=(100,100))               
                    result.paste(server_image, (0,0))
                else:
                    bg_image = Image.open(self.drawing_settings["userbar"][ctx.message.server.id]["background"]).convert('RGBA')
                    result.paste(bg_image, (0,0))
                    
            
            # if background should be provided by user
            elif background == "custom":
                await self.bot.say("Please send the background. It should be 400x100")
                answer = await self.bot.wait_for_message(timeout=30, author=ctx.message.author)        
                bg_url = answer.attachments[0]["url"]
                bg_image = Image

                success = False
                try:
                    async with aiohttp.get(bg_url) as r:
                        image = await r.content.read()
                    with open('data/drawing/temp_bg','wb') as f:
                        f.write(image)
                        bg_image = Image.open('data/drawing/temp_bg').convert('RGBA')
                        success = True

                except Exception as e:
                    success = False
                    print(e)

                if success:

                    #check image dimensions
                    if bg_image.size == (400,100):

                        result.paste(bg_image, (0,0))

                    else:
                        result.paste(server_image, (0,0))
                        await self.bot.say("Image dimensions incorrect, using defaults. Image has to be 400x100")

                else:
                    result.paste(server_image, (0,0))
                    await self.bot.say("Could not get the image, using defaults")


            # draw filter
            d.rectangle([(0,0),(400,100)], fill=(0,0,0,160))

            # draw overlay
            d.rectangle([(10,10),(390,90)], fill=(0,0,0,190), outline=(200,200,200,128))

             # paste avatar
            avatar_image = avatar_image.resize(size=(60,60))
            process.paste(avatar_image, (20,20))

            # get role
            roles = ctx.message.author.roles
            if len(roles) == 1:
                role = "member"
            else:
                max_role = max([r.position for r in roles])
                index = [r.position for r in roles].index(max_role)
                role = roles[index].name

            # draw text
            name_size = fnt_b.getsize(ctx.message.author.name)[0]
            d.text((110, 30), ctx.message.author.name, font=fnt_b, fill=(255,255,255,255))
            d.text((110 + name_size + 10, 33), "#" + ctx.message.author.discriminator, font=fnt_sm, fill=(255,255,255,128))
            d.text((110, 60), "A proud " + role + " of " + ctx.message.server.name, font=fnt_sm, fill=(255,255,255,180))

            result = Image.alpha_composite(result, process)

            result.save('data/drawing/temp.jpg','JPEG', quality=100)

            await self.bot.send_file(ctx.message.channel, 'data/drawing/temp.jpg')

            os.remove('data/drawing/temp.jpg')
            os.remove('data/drawing/temp_avatar')
            os.remove('data/drawing/temp_server')

        else:
            await self.bot.say("Couldn't get images")

    @commands.command(pass_context = True)
    async def rickroll(self, ctx):
        """Draws text on a background"""

        await self.bot.say("You asked for it. Prepare to sing along!")

        lyrics = [
            "Never gonna give you up",
            "Never gonna let you down",
            "Never gonna run around and desert you",
            "Never gonna make you cry",
            "Never gonna say goodbye",
            "Never gonna tell a lie and hurt you"
        ]

        def build_lyrics(source, text):
            source = copy(source)

            width = source.size[0]
            height = source.size[1]

            process = Image.new('RGBA', (width, height), (0,0,0))

            half_width = int(math.floor(width / 2))
            half_height = int(math.floor(height / 2))

            # get a font
            fnt_b = ImageFont.truetype('data/drawing/font_bold.ttf', 40)
            # get a drawing context
            d = ImageDraw.Draw(process)

            # haax
            d.rectangle([(0,0),(width,height)], fill=(0,0,0,0))

            # calculate position
            text_pos = int(math.floor(fnt_b.getsize(text)[0] / 2))

            # draw
            d.rectangle([(10, height - 70),(width - 10, height - 10)], fill=(0,0,0,160))
            d.text((half_width - text_pos, height - 55), text, font=fnt_b, fill=(255,255,255,255))

            return Image.alpha_composite(source, process)

        for line in enumerate(lyrics):
            if (line[0] + 1) % 3 == 0:
                result = Image.open('data/drawing/rr_3.jpg').convert('RGBA')
            elif (line[0] + 1) > 3:
                result = Image.open('data/drawing/rr_' + str(line[0] - 2) + '.png').convert('RGBA')
            else:
                result = Image.open('data/drawing/rr_' + str(line[0] + 1) + '.png').convert('RGBA')

            result = build_lyrics(result, line[1])

            result.save('temp.jpg','JPEG', quality=100)

            await self.bot.send_file(ctx.message.channel, 'temp.jpg')

            await asyncio.sleep(2)

            os.remove('temp.jpg')

    #TODO: add a twitch background generator
    #TODO: make per-server settings for userbars
    #TODO: refactor drawing functions, move similar code to shared functions
    #TODO: welcome.py-like function for making userbars
        
def check_files():
    f = "data/drawing/settings.json"
    if not fileIO(f, "check"):
        print("Creating settings.json...")
        fileIO(f, "save", {})

def setup(bot):
    if pil_available is False:
        raise RuntimeError("You don't have Pillow installed, run\n```pip3 install pillow```And try again")
        return
    check_files()
    bot.add_cog(Drawing(bot))
