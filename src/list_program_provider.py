#!/usr/bin/python
import json
import logging
import os
import random


logger = logging.getLogger(__name__)


class list_program_provider:
    def __init__ (self, list_path):
        self.resource_table = None
        self.id_array = None
        self.too_long_count = 0
        self.program_index = 0
        
        # Load JSON file for list.
        list_data = self._load_list(list_path)
        if list_data == None:
            logger.error ('list_program_provider(); error: unable to load list file.')
            return
        self.resource_table = list_data.get('resources', {})
        
        # Shuffle the list of programs.
        self._reset_list()
        
    
    # --------------------------------------------------------------------
    
    # May return None in case of error.
    
    def _load_list(self, path):
        try:
            with open(path, 'r') as list_data:
                return json.load(list_data)
        except IOError:
            logger.error('_load_list(); error: IOError for file: ' + path)
            return None
        
    
    # --------------------------------------------------------------------
    
    def _reset_list(self):
        # Shuffle the resource IDs.
        self.id_array = list(self.resource_table.keys())
        random.shuffle(self.id_array)
        
        # Clear the 'shown' flags.
        for key, value in self.resource_table.items():
            value['shown'] = False
        
        # Reset 'too_long_count'
        self.too_long_count = 0
        self.program_index = 0
        
    
    # --------------------------------------------------------------------
    # Returns duration for resource allowing for optional start_offset that
    # will (naturally) shorten the normal duration of the movie.
    
    def _resource_adjusted_duration(self, resource):
        duration = resource.get('duration', 0)
        if duration > 0:
            duration = duration - resource.get('start_offset', 0)
        else:
            logger.error('_resource_adjusted_duration(); resource with 0 duration.')
        return duration
        
     
    # --------------------------------------------------------------------
    # May return None.
    
    def _get_random_program_from_list(self, list_id, max_duration):
        if max_duration <= 0:
            logger.error('_get_random_program_from_list(); param error, max_duration less than zero (' + str(max_duration) + ').')
            return None
        
        id_array = self._shuffled_ids_for_list(list_id)
        if id_array == None:
            return None
        resource_table = self.list_dict.get('resources', None)
        if resource_table == None:
            return None
        
        # Walk resources, skipping one we have already shown.
        resource_id = None
        shown_count = 0
        long_count = 0
        for one_id in id_array:
            resource = resource_table[one_id]
            if resource['shown']:
                shown_count = shown_count + 1
                continue
            duration = resource.get('duration', None)
            if duration == None:
                logger.error('_get_random_program_from_list(); missing duration for resource: ' + one_id)
                continue
            if duration < max_duration:
                resource_id = one_id
                resource['shown'] = True
                shown_count = shown_count + 1
                logger.info ('Filler from list: ' + list_id + ' that has a total of ' + str(len(id_array)) + ' programs.')
                logger.info (str(shown_count) + ' shown, ' + str(long_count) + ' too long.')
                break
            else:
                long_count = long_count + 1
        
        # If we have shown every program in the list, shuffle, clear 'shown' flags.
        if shown_count == len(id_array):
            self._reset_list(list_id)
        
        if resource_id == None:
            # Bump 'too_long_count' for this list.
            list_dict = self.list_table.get(list_id, None)
            if list_dict != None:
                too_long_count = list_dict.get('too_long_count', 0)
                if too_long_count > long_count:
                    # Lets shuffle/reset the list.
                    self._reset_list(list_id)
                else:
                    list_dict['too_long_count'] = too_long_count + 1
            logger.info('_get_random_program_from_list(); failed to find resource with duration < ' + str(max_duration) + '.')
            logger.info('_get_random_program_from_list(); shown=' + str(shown_count) + ', too long=' + str(long_count) + ', total=' + str(len(id_array)) + '.')
            
        return resource_id
        
    
    # --------------------------------------------------------------------
        
    def _get_next_program(self):
        resource_id = None
        if self.program_index >= len(self.id_array):
            # We've gone past the end of the list, re-shuffle.
            self._reset_list()
            self.program_index = 0
        
        resource_id = self.id_array[self.program_index]
        self.program_index = self.program_index + 1
        
        return resource_id
        
    
    # --------------------------------------------------------------------
    
    # May return None.
    
    def _get_next_program_with_max_duration(self, max_duration):
        resource_id = None
        shown_count = 0
        long_count = 0
        index = 0
        for one_id in self.id_array:
            resource = self.resource_table.get(one_id, None)
            if resource.get('shown', True) == True:
                # Already shown, move on to the next.
                shown_count = shown_count + 1
            elif self._resource_adjusted_duration(resource) > max_duration:
                # Too long, move on to the next.
                long_count = long_count + 1
            else:
                resource_id = one_id
                resource['shown'] = True
                break
            
        if resource_id == None:
            if self.too_long_count > long_count:
                # Lets shuffle/reset the list.
                self._reset_list()
            else:
                self.too_long_count = self.too_long_count + 1
            logger.info('_get_next_program_with_max_duration(); failed to find resource with duration < ' + str(max_duration) + '.')
            logger.info('_get_next_program_with_max_duration(); shown=' + str(shown_count) + ', too long=' + str(long_count) + ', total=' + str(len(self.id_array)) + '.')
        
        return resource_id
        
    
    # --------------------------------------------------------------------
    # May return None in case of error or if no program is found shorter
    # than max_duration.
    
    def program_to_show(self, max_duration):
        if max_duration == None:
            resource_id = self._get_next_program()
        else:
            resource_id = self._get_next_program_with_max_duration(max_duration)
        
        if resource_id != None:
            resource = self.resource_table.get(resource_id, None)
            if resource == None:
                logger.error ('program_to_show(); missing resource with ID: ' + resource_id + '.')
            else:
                program = resource.copy()
                program['duration'] = self._resource_adjusted_duration(resource)
                return program
        
        return None
        
    
    # --------------------------------------------------------------------
    
    def program_count(self):
        if self.id_array == None:
            return 0
        return len(self.id_array)
        
    
