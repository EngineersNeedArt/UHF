#!/usr/bin/python3
import datetime
import json
import logging
import logging.handlers
from mpv_player import *
from list_program_provider import *
from schedule_program_provider import *
from time import sleep
from title_card import *
from typing import Dict, List, Union


# Configure logging.
logger = logging.getLogger()
logger.setLevel(logging.INFO)
file_handler = logging.handlers.TimedRotatingFileHandler('uhf_log', when='midnight', interval=1)
file_handler.setLevel(logging.INFO)
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s.%(message)s')
file_handler.setFormatter(formatter)
console_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.addHandler(console_handler)


DEBUG = False

DEBUG_SCREEN_X = 0
DEBUG_SCREEN_Y = 40
DEBUG_SCREEN_WIDE = 480
DEBUG_SCREEN_TALL = 270

SCREEN_X = 0
SCREEN_Y = 0
SCREEN_WIDE = 1920
SCREEN_TALL = 1080

SEEKING_PROGRAM_STATE = 0
WAITING_FOR_START_STATE = 1
PLAYING_PROGRAM_STATE = 2
END_BROADCAST_STATE = 3

MINIMUM_TITLE_CARD_DURATION = 30
MINIMUM_DEAD_TIME_TO_FILL = 210

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
# CHANNEL_FILE_PATH = os.path.join('/media/pi/UHF/_schedules/manifest.json')
CHANNEL_FILE_PATH = os.path.join('/media/calhoun/UHF/_schedules/manifest.json')
# CHANNEL_FILE_PATH = os.path.join('/media/pi/UHF/_schedules/list_music.json')


# Global variables
screen_x = SCREEN_X
screen_y = SCREEN_Y
screen_wide = SCREEN_WIDE
screen_tall = SCREEN_TALL
channel_dir = None
channel_manifest = None


# --------------------------------------------------------------------
# May return None in case of error.

def load_channel_manifest(path):
    try:
        with open(path, 'r') as manifest_data:
            return json.load(manifest_data)
    except IOError:
        logger.error('load_channel_manifest(); IOError for file: ' + path)
        return None
    

# --------------------------------------------------------------------

def resource_adjusted_duration(resource):
    duration = resource.get('duration', 0)
    if duration > 0:
        duration = duration - resource.get('start_offset', 0)
    return duration
    

# --------------------------------------------------------------------

def show_title_card(player, title, description, time_string, series_title, artwork_path):
    global screen_wide
    global screen_tall
    card_url = set_title_card(screen_wide, screen_tall, "TITLE_CARD.bmp", title,
            description, time_string, series_title, artwork_path, DEBUG is False)
    player.show_image(card_url)
    

# --------------------------------------------------------------------

def clear_title_card(player):
    global screen_wide
    global screen_tall
    card_url = set_black_background(screen_wide, screen_tall, 'BLACK_SCREEN.bmp', DEBUG is False)
    player.show_image(card_url)
    

# --------------------------------------------------------------------

def show_technical_difficulties_card(player, title, start_date, screen_wide, screen_tall):
    description = 'The scheduled program cannot be shown. Enjoy instead this short, \"' + title + '\", until the next scheduled program begins.'
    series_title = 'We Are Having Technical Difficulties'
    artwork_path = os.path.join(CURRENT_DIR, 'tv_color_bars.jpg')
    time_string = ""
    if start_date is not None:
        time_string = "Short begins at " + start_date.strftime('%-I:%M %p')
    
    card_url = set_title_card (screen_wide, screen_tall, 'TITLE_CARD.bmp', 'Please Stand By...', description,
            time_string, series_title, artwork_path,DEBUG is False)
    player.show_image(card_url)
    

# --------------------------------------------------------------------

def show_eobd_card(player, date, screen_wide, screen_tall):
    card_url = set_title_card(screen_wide, screen_tall,
            "TITLE_CARD.bmp",
            'End of the Day\'s Schedule',
            'Our schedule of programs will resume broadcast at ' + date.strftime("%-I:%M %p") + '.',
            'Goodnight!', 
            '', 
            os.path.join(CURRENT_DIR, 'end_of_programming.jpg'),
            DEBUG is False)
    player.show_image (card_url)
    

# --------------------------------------------------------------------

def get_filler(provider, current_end_date):
    now = datetime.datetime.now()
    next_program = provider.next_scheduled_program_to_show(now)
    logger.info('get_filler(); next_scheduled_program_to_show: ' + str(next_program) + '.')

    # How many seconds do we have between now and either the end of the broadcast day or
    # when the next program is to begin?
    if next_program['eobd']:
        duration = (current_end_date - now).total_seconds()
    else:
        duration = (next_program['start_date'] - now).total_seconds()

    # Allow for time to show the title card - both for the filler and the broadcast to follow.
    duration = math.floor(duration - (MINIMUM_TITLE_CARD_DURATION * 2))

    # See if there is an excess of dead-time. We will find some filler to play in the mean time.
    if duration > MINIMUM_DEAD_TIME_TO_FILL:
        logger.info('get_filler(); for technical difficulties, requesting filler, seconds=' + str(duration))
        program = provider.filler_to_show(now, duration)
        logger.info('get_filler(); filler_to_show: ' + str(program) + '.')
    else:
        program = None
    
    return {'program': program, 'eobd': next_program['eobd']}
    

# --------------------------------------------------------------------

def run_broadcast(provider, bobd_time, screen_x, screen_y, screen_wide, screen_tall):
    state = SEEKING_PROGRAM_STATE
    
    # Create a player.
    player = film_player()
    clear_title_card(player)
    
    while True:
        sleep(1)
        
        now = datetime.datetime.now()
#       now = datetime.datetime.strptime('Sep 27 2022  6:00AM', '%b %d %Y %I:%M%p')
        
        if state == SEEKING_PROGRAM_STATE:
            program = provider.program_to_show(now)
            logger.debug('run_broadcast(); program_to_show: ' + str(program) + '.')
			
            # See if "not-a-program" was returned.
            if provider.is_no_program(program):
                # See if it is the end of the broadcast day (eobd).
                eobd = program.get('eobd', False)
                if eobd:
                    show_eobd_card(player, bobd_time, screen_wide, screen_tall)
                else:
                    logger.info('run_broadcast(); no more programs scheduled for broadcast, exiting.')
                    break
            else:
                # We have a program to show.
                start_date = program.get('start_date', None)
                end_date = program.get('end_date', None)
                filler = program.get('filler', False)

                if start_date.time() > now.time():
                    # If the start date-time is in the future, put up a title card.
                    # We will wait until it is time to begin the program.
                    # Clear EOBD card, display title card, wait for program to start.
                    clear_title_card(player)
                    
                    title = program.get('title', "No Title")
                    description = program.get('description', "No description.")
                    year = program.get('year', None)
                    if year is not None:
                        description = description + ' (' + str(year) + ')'
                    time_string = "Show begins at " + start_date.strftime('%-I:%M %p')
                    artwork_path = program.get('artwork_path', None)
                    if artwork_path is not None:
                        artwork_path = os.path.join(channel_dir, artwork_path)
                    show_title_card(player, title, description, time_string, None, artwork_path)
                    state = WAITING_FOR_START_STATE
                else:
                    # Program has already begun, we will show the program - in progress.
                    # Clear title card.
                    clear_title_card(player)
                    path = program.get('path', None)
                    path = os.path.join(channel_dir, path)
                    title = program.get('title', "No Title")
                    logger.info('run_broadcast(); resuming program : ' + title + '.')
                    position = program.get('start_offset', 0)
                    success = player.show_film(path, position, screen_x, screen_y, screen_wide, screen_tall)
                    if success:
                        end_date = program.get('end_date', None)
                        state = PLAYING_PROGRAM_STATE
                    else:
                        logger.error('run_broadcast(); failed to play program, duration seconds=' + str(program.get('duration', 0)) + '.')
                        # Problem, show_film failed. It's probably a bad (or missing?) file.
                        # Get some filler to show until enough time has elapsed to get to the next program.
                        filler_dict = get_filler(provider, end_date)
                        program = filler_dict.get('program', None)
#                         next_program = provider.next_scheduled_program_to_show(now)
#                         logger.info('run_broadcast(); next_scheduled_program_to_show: ' + str(next_program) + '.')
#                         if next_program['eobd']:
#                             duration = (end_date - now).total_seconds()
#                         else:
#                             duration = (next_program['start_date'] - now).total_seconds()
#                         # Allow for time to show the title card - both for the filler and the broadcast to follow.
#                         duration = math.floor(duration - (MINIMUM_TITLE_CARD_DURATION * 2))
#                         if duration > MINIMUM_DEAD_TIME_TO_FILL:
#                             logger.info('run_broadcast(); for technical difficulties, requesting filler, seconds=' + str(duration))
#                             program = provider.filler_to_show(now, duration)
#                             logger.info('run_broadcast(); filler_to_show: ' + str(program) + '.')
#                         else:
#                             program = None
                        if program is not None:
                            title = program.get('title', "No Title")
                            start_date = program.get('start_date', None) #Not sure why 'start_date' was missing but it was.
                            show_technical_difficulties_card(player, title, start_date, screen_wide, screen_tall)
                            state = WAITING_FOR_START_STATE
                        elif filler_dict.get('eobd', False):
                            show_eobd_card(player, bobd_time, screen_wide, screen_tall)
        elif state == WAITING_FOR_START_STATE:
            # BOGUS: start_date is sometimes NoneType, see why (fix), error is:
            # "TypeError: '>=' not supported between instances of 'datetime.datetime' and 'NoneType'"
            if start_date is None: # BOGUS, added this line and next to work around error mentioned.
                logger.error('run_broadcast(); error, start_date is NONE.')
            elif datetime.datetime.now() >= start_date:
                # Clear title card, show film in progress.
                clear_title_card(player)
                path = program['path']
                path = os.path.join(channel_dir, path)
                title = program.get('title', 'No Title')
                if program.get('filler', False):
                    logger.info('run_broadcast(); broadcasting filler : ' + title + '.')
                else:
                    logger.info('run_broadcast(); broadcasting program : ' + title + '.')
                position = program.get('start_offset', 0)
                success = player.show_film(path, position, screen_x, screen_y, screen_wide, screen_tall)
                if not success:
                    logger.error('run_broadcast(); failed to play program, duration seconds=' + str(program.get('duration', 0)) + '.')
                    
                    # Try to find a filler program for now.
                    filler_dict = get_filler(provider, end_date)
                    program = filler_dict.get('program', None)
                    if (program is not None) and (not provider.is_no_program(program)):
                        title = program.get('title', "No Title")
                        start_date = program['start_date']
                        end_date = program['end_date']
                        show_technical_difficulties_card(player, title, start_date, screen_wide, screen_tall)
                        state = WAITING_FOR_START_STATE
                    else:
                        end_date = datetime.datetime.now()
                        state = SEEKING_PROGRAM_STATE
#                         if filler_dict.get('eobd', False):
#                                 show_eobd_card(player, bobd_time, screen_wide, screen_tall)
#                                 sleep(duration)
                else:
                    state = PLAYING_PROGRAM_STATE
        elif state == PLAYING_PROGRAM_STATE:
                if datetime.datetime.now() > end_date:
                    player.stop_film()
                    state = SEEKING_PROGRAM_STATE
    
    clear_title_card(player)
    

# --------------------------------------------------------------------
# This is the outer function/loop when displaying content from a "schedule".
# It loops once every day, calls the schedule state-machine in run_broadcast_day()
# above. It runs until it cannot find a schedule for the current day.

def run_uhf_schedule():
    global screen_x
    global screen_y
    global screen_wide
    global screen_tall
    global channel_dir
    global channel_manifest
    
    # Create a program provider for the schedule.
    schedule_descriptors = channel_manifest.get('schedules', None)
    list_schedule = channel_manifest.get('dotw_list_schedule', None)
    series_table = channel_manifest.get('series', None)
    list_table = channel_manifest.get('lists', None)
    bobd = channel_manifest.get('beginning_of_broadcast_day', '05:50')
    bobd_time = datetime.datetime.strptime (bobd, '%H:%M').time()
    provider = schedule_program_provider(channel_dir, schedule_descriptors, list_schedule, series_table, list_table, bobd_time, MINIMUM_TITLE_CARD_DURATION, MINIMUM_DEAD_TIME_TO_FILL)
    
    # Show programs until the schedule is exhausted.
    run_broadcast(provider, bobd_time, screen_x, screen_y, screen_wide, screen_tall)
    

# --------------------------------------------------------------------
# This is the primary function/loop when displaying content from a "list"
# (basically a playlist in JSON format). It shuffles the resource list
# and plays through all the content, then re-shuffles and repeats forever.

def run_uhf_list(path):
    global channel_dir
    global screen_x
    global screen_y
    global screen_wide
    global screen_tall
    
    # Create a film provider, in this case for a list of films.
    film_provider = list_program_provider(path)
    
    # Create a player.
    player = film_player()
    
    state = SEEKING_PROGRAM_STATE
    
    while True:
        sleep(1)
        
        if state == SEEKING_PROGRAM_STATE:
            program_dict = film_provider.program_to_show(None)
            if program_dict is None:
                logger.error('run_uhf_list(); no program to show, exiting.')
                break
            else:
                start_date = datetime.datetime.now() + datetime.timedelta(seconds=30)
                end_date = start_date + datetime.timedelta(seconds=program_dict.get('duration', 0))
                
                # Display title card, wait for program to start.
                title = program_dict.get('title', "No Title")
                description = program_dict.get('description', "No description.")
                year = program_dict.get('year', None)
                if year is not None:
                    description = description + ' (' + str(year) + ')'
                time_string = "Show begins at " + start_date.strftime('%-I:%M %p')
                artwork_path = program_dict.get('artwork_path', None)
                if artwork_path is not None:
                    artwork_path = os.path.join(channel_dir, artwork_path)
                show_title_card(player, title, description, time_string, None, artwork_path)
                
                # Wait for program to start.
                state = WAITING_FOR_START_STATE
        elif state == WAITING_FOR_START_STATE:
            if datetime.datetime.now() >= start_date:
                # Clear title card, show film.
                clear_title_card(player)
                path = program_dict.get('path', None)
                if path is None:
                    logger.error('run_uhf_list(); program missing path, exiting.')
                    break
                path = os.path.join(channel_dir, path)
                title = program_dict.get('title', "No Title")
                logger.info('run_uhf_list(); showing program : ' + title + '.')
                position = program_dict.get('start_offset', 0)
                success = player.show_film(path, position, screen_x, screen_y, screen_wide, screen_tall)
                if not success:
                    end_date = datetime.datetime.now()
                    state = SEEKING_PROGRAM_STATE
                else:
                    state = PLAYING_PROGRAM_STATE
        elif state == PLAYING_PROGRAM_STATE:
                if datetime.datetime.now() > end_date:
                    player.stop_film()
                    state = SEEKING_PROGRAM_STATE
        
    # Exiting.
    clear_title_card(player)
    

# --------------------------------------------------------------------

def main():
    global screen_x
    global screen_y
    global screen_wide
    global screen_tall
    global channel_dir
    global channel_manifest
    
    logger.info('main(); starting.')
    
    # Screen geometry.
    if DEBUG:
        screen_x = DEBUG_SCREEN_X
        screen_y = DEBUG_SCREEN_Y
        screen_wide = DEBUG_SCREEN_WIDE
        screen_tall = DEBUG_SCREEN_TALL
    
    # Load the channel manifest. Get enclosing directory.
    channel_manifest = load_channel_manifest(CHANNEL_FILE_PATH)
    if channel_manifest is None:
        logger.error('main(); unable to open the channel manifest, exiting.')
        return
    channel_dir = os.path.dirname(CHANNEL_FILE_PATH)
    
    # Get (required) version of file. 
    version = channel_manifest.get('version', None)
    
    # If this is a schedule manifest, run the schedule.
    if version == 'UHF Channel - v1':
        run_uhf_schedule()
    elif version == 'UHF List - v1':
        run_uhf_list(CHANNEL_FILE_PATH)
    else:
        logger.error('main(); unsupported channel file, exiting.')
    

# --------------------------------------------------------------------

if __name__ == '__main__':
    main()

