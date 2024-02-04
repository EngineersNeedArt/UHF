#!/usr/bin/python
import os
import datetime
import json
import logging
import random
from list_program_provider import *


logger = logging.getLogger(__name__)


class schedule_program_provider:
    def __init__ (self, channel_dir, schedule_descriptors, list_schedule, series_table, list_table, bobd_time, title_card_time, min_dead_time):
        self.channel_dir = channel_dir
        self.schedule_descriptors = schedule_descriptors
        self.list_schedule = list_schedule
        self.series_table = series_table
        self.list_table = list_table
        self.list_program_providers = {}
        self.bobd_time = bobd_time
        self.minimum_title_card_time = title_card_time
        self.minimum_dead_time_to_fill = min_dead_time
        self.current_day = None
        self.day_schedule = None
        self.resource_table = None        
        
    
    # --------------------------------------------------------------------
    # May return None in case of error.
    # BOGUS - not reviewed.
    
    def _load_schedule(self, path):
        try:
            with open(path, 'r') as schedule_data:
                return json.load(schedule_data)
        except IOError:
            logger.error('_load_schedule(); error: IOError for file: ' + path)
            return None
        
    
    # --------------------------------------------------------------------
    # May return None in case of error.
    # BOGUS - not reviewed.
    
    def _load_list(self, path):
        try:
            with open(path, 'r') as list_data:
                return json.load(list_data)
        except IOError:
            logger.error('_load_list(); error: IOError for file: ' + path)
            return None
        
    
    # --------------------------------------------------------------------
    # May return None in case of error.
    # BOGUS - not reviewed.
    
    def _day_schedule_at_index(self, schedule, day_index):
        days_array = schedule.get('days', None)
        if days_array == None:
            logger.error('_day_schedule_at_index(); missing days from schedule.')
            return None
        if day_index >= len(days_array):
            logger.error('_day_schedule_at_index(); day index out of range.')
            return None        
        return days_array[day_index]
        
    
    # --------------------------------------------------------------------
    # BOGUS - not reviewed.
    
    def _fetch_day_schedule(self, date):
        success = False
        
        # Iterate over the descriptors to find the one corresponding with date.
        for one_descriptor in self.schedule_descriptors:
            # Get start date for this descriptor.
            descriptor_start = one_descriptor.get('start_date', None)
            if descriptor_start == None:
                logger.error('_fetch_day_schedule(); error: failed to get start_date.')
                return False
            start_date = datetime.datetime.strptime (descriptor_start, '%Y-%m-%d')
            
            # Open the schedule to see how many days it covers.
            path = one_descriptor.get('schedule_path', None)
            if path == None:
                logger.error('_fetch_day_schedule(); error: failed to get schedule_path.')
                return False
            schedule = self._load_schedule(os.path.join(self.channel_dir, path))
            if schedule == None:
                logger.error ('_fetch_day_schedule(); error: unable to load schedule file.')
                return False
            
            day_count = len(schedule['days'])
            end_date = start_date + datetime.timedelta(days=day_count)
            
            # If the end date is past date, we have the schedule containing programs for date.
            if end_date > date:
                index = date.toordinal() - start_date.toordinal()
                scheduled_days = schedule.get('days', None)
                if scheduled_days == None:
                    logger.error('_fetch_day_schedule(); error: malformed schedule missing days.')
                    return False
                if index >= len(scheduled_days):
                    logger.error('_fetch_day_schedule(); error: malformed schedule day index out of range.')
                    return False
                
                self.day_schedule = self._day_schedule_at_index(schedule, index)
                if self.day_schedule == None:
                    logger.error('_fetch_day_schedule(); failed to get the schedule for today.')
                    return False
                
                # Get the resource array.
                self.resource_table = schedule.get('resources', None)
                success = True
                break
            
        return success
        
    
    # --------------------------------------------------------------------
    # Assigns 'current_day' to 'date', loads schedule from disk if needed.
    
    def _validate_day_schedule(self, date):
        success = True
        fetch_schedule = False
        if self.current_day == None:
            self.current_day = date
            fetch_schedule = True
        elif date.date() != self.current_day.date():
            self.current_day = date
            fetch_schedule = True
        
        if fetch_schedule:
            self.day_schedule = None
            self.resource_table = None
            success = self._fetch_day_schedule(self.current_day)
        return success
        
    
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
    # BOGUS - not reviewed.
    
    def _resource_series(self, resource):
        series = None
        if self.series_table != None:
            series_id = resource.get('series_id', None)
            if series_id != None:
                series = self.series_table.get(series_id, None)
        return series
        
    
    # --------------------------------------------------------------------
    # Returns a datetime representing when a program will end.
    
    def _resource_end_datetime(self, resource, start_time, date):
        start_date = datetime.datetime.combine(date, start_time)
        duration = self._resource_adjusted_duration(resource)
        end_date = start_date + datetime.timedelta(seconds=duration)
        return end_date
        
    
    # --------------------------------------------------------------------
    # Returns a datetime representing when a swcheduled program will end.
    # May return None in case of error.
    
    def _scheduled_program_end_datetime(self, scheduled_program, date):
        resource_id = scheduled_program.get('resource_id', None)
        if resource_id == None:
            logger.error('_scheduled_program_end_datetime(); missing resource_id.')
            return None
        
        resource = self.resource_table.get(resource_id, None)
        if resource == None:
            logger.error('_scheduled_program_end_datetime(); missing resource.')
            return None            
        
        start_time = datetime.datetime.strptime (scheduled_program['start_time'], '%H:%M').time()
        end_date = self._resource_end_datetime(resource, start_time, date)
        
        return end_date
        
    
    # --------------------------------------------------------------------
    # Returns a program that indicates "no program" (where None for a
    # program would indicate an error).
    
    def _no_program(self):
        return {'no_program': True, 'eobd': False}
        
    
    # --------------------------------------------------------------------
    # If a program is currently being broadcast, returns a program (dictionary)
    # containing a number of keys including the start datetime for the program
    # ('start_date') as well as the end datetime ('end_date') when it concludes.
    # Returns 'no program' if there is nothing currently scheduled.
    # May return None if there is an error.
    
    def _scheduled_program_for_datetime(self, date):
        # Loop over today's program schedule. If the program is scheduled *before* date,
        # keep a pointer to it, continue to loop. When a program is found to be
        # scheduled *after* date, break from the loop. We will be left with either a
        # pointer to the last program to be scheduled before date, or None - indicating
        # that the very first program in the schedule does not begin until after date.
        
        program_descriptor = None        
        time = date.time()
        for one_program_descriptor in self.day_schedule:
            scheduled_time = datetime.datetime.strptime (one_program_descriptor['start_time'], '%H:%M').time()
            if scheduled_time > time:
                break
            else:
                program_descriptor = one_program_descriptor
        
        # We determine if the last program to be scheduled *before* date would still be
        # in progress, still be being broadcast. We check against what time it will end.
        
        if program_descriptor == None:
            return self._no_program()
        
        resource_id = program_descriptor.get('resource_id', None)
        if resource_id == None:
            logger.error('_scheduled_program_for_datetime(); missing resource_id.')
            return None
        
        resource = self._get_resource_with_id(resource_id)
        if resource == None:
            logger.error('_scheduled_program_for_datetime(); failed to get resource.')
            return None
        
        start_time = datetime.datetime.strptime (program_descriptor['start_time'], '%H:%M').time()
        start_date = datetime.datetime.combine(date, start_time)
        end_date = self._resource_end_datetime(resource, start_time, date)
        if end_date > date:
            # Program is in progress, return it.
            program = resource.copy()
            program['start_date'] = start_date
            program['end_date'] = end_date
        else:
            # Missed the program, nothing scheduled at this moment. 
            program = self._no_program().copy()
        
        return program
        
    
    # --------------------------------------------------------------------
    
    def _next_scheduled_program_for_datetime(self, date):        
        # The 'beginning of broadcast day'.
        bobd_date = datetime.datetime.combine(date, self.bobd_time)
        
        # Loop over today's program schedule. The first program scheduled to be broadcast
        # after 'date' will be the next one. Note: it is possible that there are *no*
        # programs scheduled to run after date, we'll return "no program".
        
        eobd = False
        scheduled_program = None
        for one_scheduled_program in self.day_schedule:
            scheduled_time = datetime.datetime.strptime (one_scheduled_program['start_time'], '%H:%M').time()
            if scheduled_time > date.time():
                # If the next schedule program is after bobd and date is before bobd, we
                # will indicate to the caller 'this is the end of the broadcast schedule'.
                if (scheduled_time > bobd_date.time()) and (date.time() < bobd_date.time()):
                    eobd = True
                else:
                    scheduled_program = one_scheduled_program
                break
        
        # We have no "next" program for the date, return "no program".
        if scheduled_program == None:
            program = self._no_program().copy()
            program['eobd'] = eobd
            return program
        
        # We do have a "next" program for the date, return it.
        resource_id = scheduled_program['resource_id']
        if resource_id == None:
            logger.error('_next_scheduled_program_for_datetime(); missing resource_id.')
            return None
        
        resource = self._get_resource_with_id(resource_id)
        if resource == None:
            logger.error('_next_scheduled_program_for_datetime(); failed to get resource.')
            return None
        
        program = resource.copy()
        start_time = datetime.datetime.strptime (scheduled_program['start_time'], '%H:%M').time()
        start_date = datetime.datetime.combine(date, start_time)
        end_date = self._scheduled_program_end_datetime(scheduled_program, date)
        program['start_date'] = start_date
        program['end_date'] = end_date
        program['eobd'] = eobd
        
        return program
        
    
    # --------------------------------------------------------------------
    # May return an empty list.
    # BOGUS - not reviewed.
    
    def _get_list_ids_for_date(self, date):
        if self.list_schedule == None:
            logger.error('_get_list_ids_for_date(); param error, no list_schedule.')
            return []
        
        # Day of week should be of the form Sunday=0, Monday=1, etc.
        day_index = date.isoweekday()
        if day_index == 7:
            day_index = 0;
        if day_index >= len(self.list_schedule):
            logger.info('_get_list_ids_for_date(); info; day_index out of range.')
            return []
        
        day_schedule = self.list_schedule[day_index]
        schedule = day_schedule.get('schedule', None)
        if schedule == None:
            logger.info('_get_list_ids_for_date(); info; missing schedule.')
            return []
        
        list_ids = []
        for one_bracket in schedule:
            start_time = datetime.datetime.strptime (one_bracket['start_time'], '%H:%M').time()
            if start_time > date.time():
                break
            end_time = one_bracket.get('end_time', None)
            if (end_time == None) or (datetime.datetime.strptime (end_time, '%H:%M').time() > date.time()):
                list_ids = one_bracket.get('list_ids', [])
        
        if len(list_ids) == 0:
            logger.info('_get_list_ids_for_date(); info; did not find list_ids matching request.')
        
        return list_ids
        
    
    # --------------------------------------------------------------------
    # BOGUS - not reviewed.
    
    def _lazily_allocate_list_provider(self, list_id):        
        list_descriptor = self.list_table.get(list_id, None)
        if list_descriptor == None:
            logger.error ('_lazily_populate_list_provider(); error: missing list identifier.')
            return None
        path = list_descriptor.get('list_path', None)
        if path == None:
            logger.error ('_lazily_populate_list_provider(); error: missing list_path.')
            return None
        path = os.path.join(self.channel_dir, path)
        provider = list_program_provider(path)
        return provider
    
    # --------------------------------------------------------------------
    # May return None in case of error (missing list, etc.).
    # BOGUS - not reviewed.
    
    def _list_program_provider_for_id(self, list_id):
        provider = self.list_program_providers.get(list_id, None)
        if provider == None:
            provider = self._lazily_allocate_list_provider(list_id)
            self.list_program_providers[list_id] = provider
        return provider
        
    
    # --------------------------------------------------------------------
    # May return None in case of error. Will return "no program" if there is
    # nothing shorter than max_duration.
    
    def _get_filler_program(self, max_duration, date):
        # BOGUS, call self._validate_day_schedule(date)?
        if self.list_schedule == None:
            return None
        
        filler_program = None
        list_ids = list(self._get_list_ids_for_date(date))
        
        while filler_program == None:
            # Get the total number of resources across the lists.
            total_count = 0
            for one_id in list_ids:
                provider = self._list_program_provider_for_id(one_id)
                if provider == None:
                    continue
                total_count = total_count + provider.program_count()
            if total_count == 0:
                logger.error('_get_filler_program(); no list content, max_duration=' + str(max_duration))
                program = self._no_program().copy()
                return program
            
            # Select a random index (in order to properly weight the lists based on length).
            random_index = random.randint(0, total_count-1)
            for list_index, one_id in enumerate(list_ids):
                provider = self._list_program_provider_for_id(one_id)
                if provider == None:
                    continue
                random_index = random_index - provider.program_count()
                if random_index <= 0:
                    filler_program = provider.program_to_show(max_duration)
                    if filler_program == None:
                        # No short, remove from list and try again.
                        del list_ids[list_index]
                    else:
                        break
        
        if filler_program == None:
            program = self._no_program().copy()
            logger.info('_get_filler_program(); failed to get a program.')
        else:
            program = filler_program
        
        return program
        
    
    # --------------------------------------------------------------------
    # May return None.
    # BOGUS - not reviewed.
    
    def _get_resource_with_id(self, resource_id):
        # Param check.
        if resource_id == None:
            logger.error('_get_resource_with_id(); param error, resource_id is None.')
            return None
        
        # First try our resource table.
        resource = self.resource_table.get(resource_id, None)
        if resource == None:
            logger.error('_get_resource_with_id(); missing resource_id: ' + resource_id)
        else:
            adjusted_duration = self._resource_adjusted_duration(resource)
            resource['duration'] = adjusted_duration
        
        return resource
        
    
    # --------------------------------------------------------------------
    # BOGUS - not reviewed.
    
    def _append_series_info(self, program):
        series = self._resource_series(program)
        if series != None:
            program['series_title'] = series.get('title', None)
            program['artwork_path'] = series.get('logo_path', None)        
        
    
    # --------------------------------------------------------------------
    # Function indicates whether a program represents "no program". 
    
    def is_no_program(self, program):
        return program.get('no_program', False)
        
    
    # --------------------------------------------------------------------
    # BOGUS - not reviewed.
    
    def program_to_show(self, date):
        success = self._validate_day_schedule(date)
        if success == False:
            return None
        
        # First, determine if there is already a program scheduled to be broadcast now.
        program = self._scheduled_program_for_datetime(date)
        if program == None:
            return None
        
        if self.is_no_program(program):
            # No program is currently scheduled to be broadcast now.
            # Find the *next* program scheduled to be broadcast.
            eobd = False
            adjustedDate = date
            while (self.is_no_program(program)) and (eobd == False):
                program = self._next_scheduled_program_for_datetime(date)
                eobd = program.get('eobd', False)
                if (self.is_no_program(program)) and (eobd == False):
                    # We're reached the end of the schedule and came up empty,
                    # advance to the next day.
                    adjustedDate = adjustedDate + datetime.timedelta(days=1)
                    adjustedDate = adjustedDate.replace(hour=0, minute=0, second=0, microsecond=0)
                    success = self._validate_day_schedule(adjustedDate)
                    if success == False:
                        return None
                    
                    program = self._next_scheduled_program_for_datetime(adjustedDate)
                    eobd = program.get('eobd', False)
            
            # If it is the end-of-broadcast-day, return program indicating as much.
            if eobd == True:
                return program
            
            # BOGUS: will _next_scheduled_program_for_datetime() return start_date, end_date for no_program?
            # Or will that scenario never happen (will always be eobd and we will have returned above).
            start_date = program.get('start_date', None)
            end_date = program.get('end_date', None)
            start_offset = 0
            
            # See how much dead-time we have before the next show.
            if (start_date != None) and (eobd == False):
                dead_time = (start_date - date).seconds
                # Subtract the minimum time we want for title cards to be shown (for filler and for next broadcast).
                dead_time = dead_time - (self.minimum_title_card_time * 2)
                if dead_time > self.minimum_dead_time_to_fill:
                    filler_program = self.filler_to_show(date, dead_time)
                    if (filler_program != None) and (self.is_no_program(filler_program) == False):
                        return filler_program
            
            # BOGUS: will this ever be true? Feels like only if "eobd" and that was returned earlier.
            if self.is_no_program(program):
                return program
            
#             program = resource.copy()
            program['start_date'] = start_date
            program['end_date'] = end_date
            program['eobd'] = eobd
            program['filler'] = False
            series = self._resource_series(program)
            if series != None:
                program['series_title'] = series.get('title', None)
                program['artwork_path'] = series.get('logo_path', None)
            return program
        else:
            # We have a program in progress.
            start_date = program['start_date']
            start_adjustment = round((date - start_date).total_seconds())
            start_offset = program.get('start_offset', 0)
            program['start_offset'] = start_offset + start_adjustment
            program['eobd'] = False
            program['filler'] = False
            series = self._resource_series(program)
            if series != None:
                program['series_title'] = series.get('title', None)
                program['artwork_path'] = series.get('logo_path', None)
            return program
        
        return None
        
    
    # --------------------------------------------------------------------
    # BOGUS: should refactor program_to_show() to call next_scheduled_program_to_show().
    # BOGUS - not reviewed.
    
    def next_scheduled_program_to_show(self, date):
        success = self._validate_day_schedule(date)
        if success == False:
            return None
        
        # Find the *next* program scheduled to be broadcast.
        adjustedDate = date
        program = None
        eobd = False
        while (program == None) and (eobd == False):
            program = self._next_scheduled_program_for_datetime(date)
            eobd = program.get('eobd', False)
            if (self.is_no_program(program)) and (eobd == False):
                # We're reached the end of the schedule and came up empty,
                # advance to the next day.
                adjustedDate = adjustedDate + datetime.timedelta(days=1)
                adjustedDate = adjustedDate.replace(hour=0, minute=0, second=0, microsecond=0)
                success = self._validate_day_schedule(adjustedDate)
                if success == False:
                    return None
                program = self._next_scheduled_program_for_datetime(adjustedDate)
        
        if program == None:
            return None
        
        program['filler'] = False
        series = self._resource_series(program)
        if series != None:
            program['series_title'] = series.get('title', None)
            program['artwork_path'] = series.get('logo_path', None)
        
        return program
        
    
    # --------------------------------------------------------------------
    # Caller should pass a dead_time that allows additional time to show
    # the title card as well.
    # May return None if no filler can be found with a duration shorter
    # than dead_time or in case of errors (like no lists, filler).
    
    def filler_to_show(self, date, dead_time):
        # Will return either a program (success) or None if error or no filler of specified length.
        program = self._get_filler_program(dead_time, date)
        if program == None:
            return None
        if self.is_no_program(program):
            program = self._no_program().copy()
            return program
        
        start_date = date + datetime.timedelta(seconds=self.minimum_title_card_time)
        program['start_date'] = start_date
        adjusted_duration = program.get ('duration', 0)
        if adjusted_duration == 0:
            logger.error('filler_to_show(); adjusted_duration is 0')
        program['end_date'] = start_date + datetime.timedelta(seconds=adjusted_duration)            
        program['eobd'] = False
        program['filler'] = True
        
        return program
        
    