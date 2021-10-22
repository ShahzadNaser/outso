import frappe
import calendar
from datetime import datetime, date, timedelta
from outso.constants.globals import SHIFT_HOURS

def get_timestamp(date_time):

    try :
        if(isinstance(date_time, str) or isinstance(date_time, str)):
            return calendar.timegm(datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S").utctimetuple()) 
        else:
            return calendar.timegm(date_time.utctimetuple())
    except Exception as e:
        print(str(e))
        return 0

def get_time_diff(start_time, end_time, type = "secs"):

    _divider = 1

    if type == "mins":
        _divider = 60

    if type == "hours":
        _divider = 3600

    if type == "days":
        _divider = 216000

    return round( float( get_timestamp(start_time) - get_timestamp(end_time) ) / _divider, 2 )

def calculate_hours(start_time, end_time):
    todays_date = datetime.today().strftime('%Y-%m-%d')
    today_shift_start = "{0} {1}".format(todays_date, start_time)
    today_shift_end = "{0} {1}".format(todays_date, end_time)
    total_shift_hours = get_time_diff(today_shift_end, today_shift_start, "hours")
    # for shifts like 18:00:00 to 03:00:00
    if total_shift_hours < 0:
        tomorrows_date_obj = datetime.today() + timedelta(days=1)
        tomorrows_date = tomorrows_date_obj.strftime('%Y-%m-%d')
        today_shift_end = "{0} {1}".format(tomorrows_date, end_time)
        total_shift_hours = get_time_diff(today_shift_end, today_shift_start, "hours")
    return total_shift_hours