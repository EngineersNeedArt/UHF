#!/usr/bin/python
import logging
import math
import os
from PIL import Image, ImageDraw, ImageFont
import subprocess


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FONT_DIR = os.path.join(CURRENT_DIR, 'fonts')


logger = logging.getLogger(__name__)
title_font = None
body_font = None
series_font = None


def text_wrap(text, font, writing, max_width, max_height):
    lines = [[]]
    words = text.split()
    for one_word in words:
        # try putting this word in last line then measure
        lines[-1].append(one_word)
        (w,h) = writing.multiline_textsize('\n'.join([' '.join(line) for line in lines]), font=font)
        if w > max_width: # too wide
            # take it back out, put it on the next line, then measure again
            lines.append([lines[-1].pop()])
            (w,h) = writing.multiline_textsize('\n'.join([' '.join(line) for line in lines]), font=font)
            if h > max_height: # too high now, cannot fit this word in, so take out - add ellipses
                lines.pop()
                # try adding ellipses to last word fitting (i.e. without a space)
                lines[-1][-1] += '...'
                # keep checking that this doesn't make the textbox too wide,
                # if so, cycle through previous words until the ellipses can fit
                while writing.multiline_textsize('\n'.join([' '.join(line) for line in lines]),font=font)[0] > max_width:
                    lines[-1].pop()
                    if lines[-1]:
                        lines[-1][-1] += '...'
                    else:
                        lines[-1].append('...')
                break
    return '\n'.join([' '.join(line) for line in lines])


def display_image(wide, tall, image_url, fullscreen):
    if fullscreen:
        image_ref = subprocess.Popen(["feh", "--hide-pointer", "-x", "-Z", "-F", "-g", str(wide) + "x" + str(tall), image_url])
    else:
        image_ref = subprocess.Popen(["feh", "--hide-pointer", "-x", "-g", str(wide) + "x" + str(tall), image_url])
    return image_ref


def set_black_background(wide, tall, image_url, fullscreen):
    image = Image.new(mode="RGB", size=(wide, tall), color='black')
    image.save(image_url)
    return display_image(wide, tall, image_url, fullscreen)


def set_title_card(wide, tall, image_url, title, body, start_time, series_title, thumbnail_url, fullscreen):
    global title_font
    global body_font
    global series_font
    
    # Set up fonts.
    if title_font == None:
        title_text_height = math.ceil(tall / 16)        
        title_font = ImageFont.truetype(os.path.join(FONT_DIR, 'OpenSans-SemiBold.ttf'), title_text_height)
    
    if body_font == None:
        body_text_height = math.ceil(tall / 20)
        body_font = ImageFont.truetype(os.path.join(FONT_DIR, 'OpenSans-Regular.ttf'), body_text_height)
    
    if series_font == None:
        series_text_height = math.ceil(tall / 20)        
        series_font = ImageFont.truetype(os.path.join(FONT_DIR, 'OpenSans-ExtraBold.ttf'), series_text_height)
    
    # Calculate padding.
    if thumbnail_url == None:
        leading_padding = math.ceil(wide / 6)
        trailing_padding = math.ceil(wide / 6)
    else:
        leading_padding = math.ceil(wide / 2.7)
        trailing_padding = math.ceil(wide / 16)
    
    max_width = wide - leading_padding - trailing_padding
    
    top_padding = math.ceil(tall / 12)
    bottom_padding = math.ceil(tall / 12)
    title_body_padding = math.ceil(tall / 20)
    max_height = tall - top_padding - bottom_padding
    
    # Create blank (black) image and drawing context.
    image = Image.new(mode="RGB", size=(wide, tall), color='black')    
    image_draw = ImageDraw.Draw(image)
    
    #Get text metrics.
    if series_title != None:
        series_text = text_wrap(series_title, series_font, image_draw, max_width, max_height)
        series_size = image_draw.textsize(series_text, series_font)
    
    title_text = text_wrap(title, title_font, image_draw, max_width, max_height)
    title_size = image_draw.textsize(title_text, title_font)
    
    body_text = text_wrap(body, body_font, image_draw, max_width, max_height - title_size[1])
    body_size = image_draw.textsize(body_text, body_font)
    
    time_text = text_wrap(start_time, body_font, image_draw, max_width, max_height - title_size[1] - body_size[1])
    time_size = image_draw.textsize(time_text, body_font)
    
    # Draw text.
    if series_title != None:
        banner_height = math.ceil(series_size[1] * 5 / 4)
        image_draw.rectangle(((0, 0), (wide, banner_height)), fill="grey")
        # Centering the text vertically in banner plus an offset of 10% to shift up a bit.
        text_y = round(((banner_height - series_size[1]) / 2) - (banner_height / 10))
        image_draw.text(((wide - series_size[0]) / 2, text_y), series_text, font=series_font, fill='black')
        top_padding = top_padding + banner_height
        max_height = tall - top_padding - bottom_padding
        
    text_y = top_padding
    image_draw.text((leading_padding + ((max_width - title_size[0]) / 2), text_y), title_text, font=title_font, fill='white')
    
    text_y = text_y + title_size[1] + title_body_padding
    image_draw.text((leading_padding, text_y), body_text, font=body_font, fill='white')
    
    text_y = top_padding + max_height - time_size[1]
    image_draw.text((leading_padding, text_y), time_text, font=body_font, fill='white')
    
    if thumbnail_url != None:
        try:
            thumbnail = Image.open(thumbnail_url)
            max_thumbnail_size = (wide / 4, wide / 4)
            thumbnail.thumbnail(max_thumbnail_size)
            offset = (math.ceil(wide / 16), math.ceil(tall / 8))
            image.paste(thumbnail, offset)
        except IOError:
            logger.error('set_title_card(); error: IOError for file: ' + thumbnail_url)
    
#     image_draw.rectangle([leading_padding,top_padding,leading_padding + max_width,top_padding + max_height], width = 2, outline="#0000ff")
    
    # Save image.
    image.save(image_url)
    return display_image(wide, tall, image_url, fullscreen)
    
    
if __name__ == '__main__':
    title_card_ref = set_title_card(960, 540, "Temp.png",
            "Perchance to Dream",
            "A man with a severe heart condition who has been awake for a long time tells his psychiatrist that he will die if he goes to sleep, because a vixen is trying to kill him.",
            "Show begins at 10:30", 
            "The Twilight Zone", 
            "twilight-zone-logo.png",
            False)
    
