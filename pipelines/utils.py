from datetime import datetime, timedelta
import re
import pendulum
import logging

logging.basicConfig(level=logging.INFO)

def clean_title(title):
    matches = re.search(r'([\w\s./-]+(?:\s*(?:\/|-)\s*[\w\s./-]*)*)', title)
    if matches:
        cleaned_title = matches.group(1).strip()
        cleaned_title = cleaned_title.split(' - ')[0].strip()
    else:
        cleaned_title = title.strip()

    return cleaned_title

def clean_salary(salary, exchange_rate=23000):
    salary = salary.lower().strip()
    matches = re.findall(r'[\d,]+', salary)

    if matches:
        if 'usd' in salary or '$' in salary:
            if '-' in salary:
                return (int(matches[0].replace(',', ''))*exchange_rate/1_000_000, int(matches[1].replace(',', ''))*exchange_rate/1_000_000)
            else:
                return (int(matches[0].replace(',', ''))*exchange_rate/1_000_000,)
        
        elif 'triệu' in salary:
            if '-' in salary:
                return (float(matches[0].replace(',', '')), float(matches[0].replace(',', '')))
            else:
                return (float(matches[0]),)
    else:
        return ('Thỏa thuận',)

def transform_salary(salary_tuple):
    if len(salary_tuple) > 1:
        return sum(salary_tuple) / len(salary_tuple)
    else:
        return salary_tuple[0]
    
def caculate_dates(update_text, deadline_text, base_time=None):
    local_tz = pendulum.timezone("Asia/Ho_Chi_Minh")
    if base_time is None:
        base_time = pendulum.now(local_tz)
    
    time_units = {
        'ngày': 86400,
        'giờ': 3600,
        'phút': 60,
        'giây': 1
    }
    def caculate_seconds(time_text):
        for unit, second in time_units.items():
            pattern = r'(\d+)\s*(' + re.escape(unit) + r')'
            matches = re.search(pattern, time_text)
            
            if matches:
                return int(matches.group(1)) * second

    update_second = caculate_seconds(update_text)
    deadline_second = caculate_seconds(deadline_text)
    update_date = base_time - timedelta(seconds=update_second)
    deadline_date = base_time + timedelta(seconds=deadline_second)

    update_date = update_date.in_timezone(local_tz)
    deadline_date = deadline_date.in_timezone(local_tz)


    return update_date, deadline_date