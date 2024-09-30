#!/usr/bin/python3
import logging
import mpv


logger = logging.getLogger(__name__)


class film_player:
    def __init__ (self):
        self.player_video = mpv.MPV(fullscreen = True);
        self.player_images = mpv.MPV(fullscreen = True, keep_open=True);
    
    # --------------------------------------------------------------------
    
    def show_image(self, path):
        logger.info('show_image(); path=' + path + '.')
        
        try:
            self.player_images.play(path)
            return True
        except Exception as err: 
            logger.error('show_image(); path=' + path + '; MPV exception: ' + str(err))
            return False
        
    
    # --------------------------------------------------------------------
    
    def show_film(self, path, position, screen_x, screen_y, screen_wide, screen_tall):
        logger.info('show_film(); path=' + path + ', position=' + str(position) + '.')
        
        try:
            logger.info('show_film(); play')
            self.player_video.play(path)
            
            if (position is not None) and (position > 0):
                self.player_video.wait_until_playing()
                self.player_video.seek(position)
            return True
        except Exception as err: 
            logger.error('show_film(); MPV exception: ' + str(err))
            if position != None:
                logger.error('show_film(); path=' + path + ', position=' + str(position) + '.')
            else:
                logger.error('show_film(); path=' + path + '.')
            return False
        
    
    # --------------------------------------------------------------------
    
    def stop_film(self):
        logger.info('stop_film().')
        # NOP
        return True
    

    