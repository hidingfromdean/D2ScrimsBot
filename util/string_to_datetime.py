import datetime as dt
from datetime import datetime

suffixes = {
    'next': 7,
    'coming': 7,
    'previous': -7,
    'last': -7,
    'today': 0,
    'tomorrow': 1,
    'yesterday': -1
}

days = {
    'monday': 0,
    'tuesday': 1,
    'wednesday': 2,
    'thursday': 3,
    'friday': 4,
    'saturday': 5,
    'sunday': 6
}

date_formats = [
    '%e/%m/%Y %H:%M', #1/01/1995 23:30
    '%e-%m-%Y %H:%M', #1-01-1995 23:30
    '%d/%m/%Y %H:%M', #01/01/1995 23:30
    '%d-%m-%Y %H:%M', #01-01-1995 23:30
    '%Y/%m/%e %H:%M', #1995/01/01 23:30
    '%Y/%m/%d %H:%M', #1995/01/1 23:30

    '%e-%b-%Y %H:%M', #1-Oct-1995 23:30
    '%e %b %Y %H:%M', #1 Oct 1995 23:30
    '%b-%e-%Y %H:%M', #Oct-1-1995 23:30
    '%b %e %Y %H:%M', #Oct 1 1995 23:30

    '%d-%b-%Y %H:%M', #01-Oct-1995 23:30
    '%d %b %Y %H:%M', #01 Oct 1995 23:30
    '%b-%d-%Y %H:%M', #Oct-01-1995 23:30
    '%b %d %Y %H:%M', #Oct 01 1995 23:30

    '%e/%m/%Y %H%M', #1/01/1995 2330
    '%e-%m-%Y %H%M', #1-01-1995 2330
    '%d/%m/%Y %H%M', #01/01/1995 2330
    '%d-%m-%Y %H%M', #01-01-1995 2330
    '%Y/%m/%e %H%M', #1995/01/01 2330
    '%Y/%m/%d %H%M', #1995/01/1 2330

    '%e-%b-%Y %H%M', #1-Oct-1995 2330
    '%e %b %Y %H%M', #1 Oct 1995 2330
    '%b-%e-%Y %H%M', #Oct-1-1995 2330
    '%b %e %Y %H%M', #Oct 1 1995 2330

    '%d-%b-%Y %H%M', #01-Oct-1995 2330
    '%d %b %Y %H%M', #01 Oct 1995 2330
    '%b-%d-%Y %H%M', #Oct-01-1995 2330
    '%b %d %Y %H%M', #Oct 01 1995 2330

]

time_formats = [
    '%H%M',
    '%H:%M',
]

def string_to_datetime(input):
    """
        Semantic datetime translator
    """
    # Check if input is in a correct datetime format
    for date_format in date_formats:
        try:
            return_date = datetime.strptime(input, date_format)
            break
        except:
            return_date = None

    # If not, try translating.
    if return_date is None:
        try:
            parsed_string = parse_string(input)
            new_date = parsed_string_to_date(parsed_string)
            return_date = new_date
        except Exception as e:
            print(e)
            raise AttributeError('Invalid date')

    return return_date


def parse_string(input):
    """
        If input is not in the correct datetime format, parse input for suffix,
        day and time items
    """
    split = input.split()
    split = [x.lower() for x in split]

    # This will only find the first suffix that matches from suffixes.keys()
    for suffix in suffixes.keys():
        if suffix in split:
            relevant_suffix = suffix
            split.remove(suffix)
            break
        else:
            relevant_suffix = None
    # This will only find the first suffix that matches from days.keys()
    for day in days.keys():
        if day in split:
            relevant_day = day
            split.remove(day)
            break
        else:
            relevant_day = None

    return {'suffix': relevant_suffix, 'day': relevant_day, 'time': split[0]}


def parsed_string_to_date(parsed_string):
    """
        Take a parsed string and compute required date
    """
    # Required date calculated relative to today.
    today = datetime.now()
    today_index = days[today.strftime('%A').lower()]

    new_date = today

    # Check if a day is present. If so, change the date to that day from present week
    if parsed_string['day'] is not None:
        set_date_index = days[parsed_string['day']]
        new_date = today - dt.timedelta(today_index - set_date_index)
        assert days[new_date.strftime('%A').lower()] == set_date_index

     # From the changed date, make the change set by parsed suffix.
    if parsed_string['suffix'] is not None:
        new_date += dt.timedelta(suffixes[parsed_string['suffix']])

    # Parse time in normal way, and set date.
    for time_format in time_formats:
        try:
            new_time = datetime.strptime(parsed_string['time'], time_format)
            new_date = new_date.replace(hour=new_time.hour, minute=new_time.minute, second=new_time.second)
            break
        except:
            new_time = None
    if new_time is None:
        raise Exception('Invalid time')

    return new_date

if __name__ == '__main__':
    date = '23:30 tomorrow'

    print(string_to_datetime(date))
