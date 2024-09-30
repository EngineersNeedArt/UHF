#!/usr/bin/python
import logging
import math
import os
from PIL import Image, ImageDraw, ImageFont


CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
FONT_DIR = os.path.join(CURRENT_DIR, 'fonts')


logger = logging.getLogger(__name__)
title_font = None
body_font = None
series_font = None


def _text_wrap(text, font, draw, max_width, max_height):
    lines = []
    words = text.split()
    total_width = 0
    total_height = 0
    
    # Wrap text by measuring width using textbbox.
    current_line = ""
    for word in words:
        test_line = current_line + word + " "
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        if width <= max_width:
            current_line = test_line
        else:
            if width > total_width:
                total_width = width
            total_height = total_height + height
            lines.append(current_line)
            current_line = word + " "
    if current_line:
        if width > total_width:
            total_width = width
        total_height = total_height + height
        lines.append(current_line)        
    return lines, total_width, total_height


def _display_lines_of_text(x, y, line_spacing, lines, font, draw, fill):
    y_text = y
    for line in lines:
        draw.text((x, y_text), line, font=font, fill=fill)
        bbox = draw.textbbox((0, 0), line, font=font)
        y_text += line_spacing
    

def set_black_background(wide, tall, image_url, fullscreen):
    image = Image.new(mode="RGB", size=(wide, tall), color='black')
    image.save(image_url)
    return image_url
    

def set_title_card(wide, tall, image_url, title, body, start_time, series_title, thumbnail_url, fullscreen):
    global title_font
    global body_font
    global series_font
    
    # Set up fonts.
    title_text_height = math.ceil(tall / 16)        
    if title_font == None:
        title_font = ImageFont.truetype(os.path.join(FONT_DIR, 'OpenSans-SemiBold.ttf'), title_text_height)
    
    body_text_height = math.ceil(tall / 20)
    if body_font == None:
        body_font = ImageFont.truetype(os.path.join(FONT_DIR, 'OpenSans-Regular.ttf'), body_text_height)
    
    series_text_height = math.ceil(tall / 20)        
    if series_font == None:
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
    
    # Get text metrics.
    if series_title != None:
        series_text, series_width, series_height = _text_wrap(series_title, series_font, image_draw, max_width, max_height)
    title_text, title_width, title_height = _text_wrap(title, title_font, image_draw, max_width, max_height)
    body_text, body_width, body_height = _text_wrap(body, body_font, image_draw, max_width, max_height)
    time_text, time_width, time_height = _text_wrap(start_time, body_font, image_draw, max_width, max_height)

    # Draw text.
    if series_title != None:
        banner_height = math.ceil(series_height * 5 / 4)
        image_draw.rectangle(((0, 0), (wide, banner_height)), fill="grey")
        # Centering the text vertically in banner plus an offset of 10% to shift up a bit.
        text_y = round(((banner_height - series_height) / 2) - (banner_height / 10))
        _display_lines_of_text((wide - series_width) / 2, text_y, series_text_height + 6, series_text, series_font, image_draw, 'black')
        top_padding = top_padding + banner_height
        max_height = tall - top_padding - bottom_padding
        
    text_y = top_padding
    _display_lines_of_text(leading_padding + ((max_width - title_width) / 2), text_y, title_text_height + 8, title_text, title_font, image_draw, 'white')
    
    text_y = text_y + title_height + title_body_padding
    _display_lines_of_text(leading_padding, text_y, body_text_height + 6, body_text, body_font, image_draw, 'white')
    
    text_y = top_padding + max_height - time_height
    _display_lines_of_text(leading_padding, text_y, body_text_height + 6, time_text, body_font, image_draw, 'white')
    
    if thumbnail_url != None:
        try:
            thumbnail = Image.open(thumbnail_url)
            max_thumbnail_size = (wide / 4, wide / 4)
            thumbnail.thumbnail(max_thumbnail_size)
            offset = (math.ceil(wide / 16), math.ceil(tall / 8))
            image.paste(thumbnail, offset)
        except IOError:
            logger.error('set_title_card(); error: IOError for file: ' + thumbnail_url)
    
    # Save image.
    image.save(image_url)
    return image_url
    

if __name__ == '__main__':
    title_card_ref = set_title_card(960, 540, "Temp.png",
            "Perchance to Dream",
            "A man with a severe heart condition who has been awake for a long time tells his psychiatrist that he will die if he goes to sleep, because a vixen is trying to kill him.",
            "Show begins at 10:30", 
            "The Twilight Zone", 
            "twilight-zone-logo.png",
            False)
    
