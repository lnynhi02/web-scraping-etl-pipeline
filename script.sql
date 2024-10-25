-- Clean the 'salary' field
UPDATE jobs_table
SET salary = NULL
WHERE salary = 'Thỏa thuận';

ALTER TABLE jobs_table
ALTER COLUMN salary TYPE numeric USING salary::numeric;

UPDATE jobs_table
SET salary = ROUND(salary);

-- Create a stored procedure to update the 'remaining_time' field.
CREATE OR REPLACE PROCEDURE update_remaining_time()
LANGUAGE plpgsql
AS $$
DECALRE
    job_record RECORD,
    time_remaining INTERVAL;
BEGIN
    FOR job_record IN SELECT * FROM jobs_table LOOP
        time_remaining = jobs_table.due_date - CURRENT_TIMESTAMP;
        
        IF time_remaining > INTERVAL '0 seconds' THEN 
            IF time_remaining < INTERVAL '1 minutes' THEN
                UPDATE jobs_table
                SET remaining_time = 'Còn ' || EXTRACT(SECOND FROM time_remaining) || ' giây để ứng tuyển'
                WHERE job_link = job_record.job_link;
            ELSEIF time_remaining < INTERVAL '1 hour' THEN
                UPDATE jobs_table
                SET remaining_time = 'Còn ' || EXTRACT(MINUTE FROM time_remaining) || ' phút để ứng tuyển'
                WHERE job_link = job_record.job_link;
            ELSEIF time_remaining < INTERVAL '1 day' THEN 
                UPDATE jobs_table
                SET remaining_time = 'Còn ' || EXTRACT(HOUR FROM time_remaining) || ' giờ để ứng tuyển'
                WHERE job_link = job_record.job_link;
            ELSE
                UPDATE jobs_table
                SET remaining_time = 'Còn ' || EXTRACT(DAY FROM time_remaining) || ' ngày để ứng tuyển'
                WHERE job_link = job_record.job_link;
            END IF;
        
        ELSE
            UPDATE jobs_table
            SET remaining_time = 'Đã hết thời gian ứng tuyển'
            WHERE job_link = job_record.job_link;
        END IF;
    END LOOP;
END;
$$;

-- Get a list of jobs with application deadline within the next 10 days
SELECT job_name, job_link, salary, job_location, remaining_time, due_date
FROM jobs_table
WHERE due_date <= NOW() + INTERVAL '20 DAYS';

-- Find jobs with salary greater than 15 million VND
SELECT job_name, job_link, company_name, salary, job_location
FROM jobs_table
WHERE salary > 15;

-- Get a list of jobs in order of the most recently posted
SELECT job_name, company_name, posted_date
FROM jobs_table
ORDER BY posted_date DESC;

-- Get the total number of jobs available in Ho Chi Minh City
SELECT COUNT(*)
FROM jobs_table
WHERE job_location LIKE '%Hồ Chí Minh%';

-- Find the top 10 highest-paying jobs in Ho Chi Minh City
SELECT job_name, job_link, company_name, salary
FROM jobs_table
WHERE job_location LIKE '%Hồ Chí Minh%'
ORDER BY salary DESC
LIMIT 10;