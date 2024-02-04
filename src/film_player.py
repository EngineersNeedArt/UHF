#!/usr/bin/python3
USE_VLC = True
if USE_VLC:
    import time
    import vlc
else:
    from omxplayer import OMXPlayer
import logging


logger = logging.getLogger(__name__)


class film_player:
    def __init__ (self):
        if USE_VLC:
            self.vlc_instance = None
            self.player_object = None
        else:
            self.player_object = None
        
    
    # --------------------------------------------------------------------
    
    def _offset_str_from_position(self, position):
        mod_tuple = divmod (position, 3600)
        hours_off = mod_tuple[0]
        mod_tuple = divmod(mod_tuple[1], 60)
        minutes_off = mod_tuple[0]
        seconds_off = mod_tuple[1]
        return str(hours_off).zfill(2) + ':' + str(minutes_off).zfill(2) + ':' + str(seconds_off).zfill(2)
        
    
    # --------------------------------------------------------------------
    
    def _show_film_vlc(self, path, position, screen_x, screen_y, screen_wide, screen_tall):
        self.player_object = vlc.MediaPlayer(path)
        # self.player_object.set_fullscreen(True)
        self.player_object.play()
        self.player_object.set_time(position * 1000)
        return True
        
    
    # --------------------------------------------------------------------
    
    def _show_film_omx(self, path, position, screen_x, screen_y, screen_wide, screen_tall):
        offset_arg = ''
        logger.info('show_film(); path=' + path + ', position=' + str(position) + '.')
        try:
            if self.player_object == None:
                if position == None:
                    offset_arg = '00:00:00'
                else:
                    offset_arg = self._offset_str_from_position(position)
                self.player_object = OMXPlayer(path, args=["--win", str(screen_x) + " " + str(screen_y) + " " + str(screen_wide) + " " + str(screen_tall),
                        '-l', offset_arg, 
#                         '-o', 'both',
                        '-o', 'alsa',
                        '--layer', '2',
                        '--aspect-mode', 'letterbox', 
                        '--vol', '-1500'],
                        dbus_name='org.mpris.MediaPlayer2.omxplayer1', pause=True)
            else:
                self.player_object.load(path)
                if position != None:
                    self.player_object.set_position(position)
            self.player_object.play()
            return True
        except Exception as err: 
            logger.error('show_film_omx(); OMXPlayer exception: ' + str(err))
            if len(offset_arg) > 0:
                logger.error('show_film_omx(); path=' + path + ', position=' + str(position) + ', offset_arg=' + offset_arg + '.')
            else:
                logger.error('show_film_omx(); path=' + path + ', position=' + str(position) + '.')
            return False
        
    
    # --------------------------------------------------------------------
    
    def _stop_film_vlc(self):
        logger.info('_stop_film_vlc(); NOP.')
#         if self.player_object != None:
#         if self.vlc_instance != None:
#             self.player_object.stop()
#             vlc.libvlc_release(self.vlc_instance)
#             self.vlc_instance = None
#         self.player_object = None
    
    # --------------------------------------------------------------------
    
    def _stop_film_omx(self):
        if self.player_object != None:
            try:
                if self.player_object.is_playing():
                    self.player_object.quit()
            except Exception as err: 
                logger.error('stop_film_omx(); OMXPlayer exception: ' + str(err))
            self.player_object = None
        
    
    # --------------------------------------------------------------------
    
    def show_film(self, path, position, screen_x, screen_y, screen_wide, screen_tall):
        if USE_VLC:
            return self._show_film_vlc(path, position, screen_x, screen_y, screen_wide, screen_tall)
        else:
            return self._show_film_omx(path, position, screen_x, screen_y, screen_wide, screen_tall)

    # --------------------------------------------------------------------
    
    def stop_film(self):
        if USE_VLC:
            return self._stop_film_vlc()
        else:
            return self._stop_film_omx()
        
    