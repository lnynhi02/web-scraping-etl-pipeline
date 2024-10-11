-- Clean the 'salary' field
UPDATE jobs_table
SET salary = NULL
WHERE salary = 'Thỏa thuận';

ALTER TABLE jobs_table
ALTER COLUMN salary TYPE numeric USING salary::numeric;

UPDATE jobs_table
SET salary = ROUND(salary);

-- Create a stored procedure to update the 'deadline' field.
CREATE OR REPLACE PROCEDURE update_deadline()
LANGUAGE plpgsql
AS $$
DECALRE
    job_record RECORD,
    time_remaining INTERVAL;
BEGIN
    FOR job_record IN SELECT * FROM jobs_table LOOP
        time_remaining = jobs_table.deadline_date - CURRENT_TIMESTAMP;
        
        IF time_remaining > INTERVAL '0 seconds' THEN 
            IF time_remaining < INTERVAL '1 minutes' THEN
                UPDATE jobs_table
                SET deadline = 'Còn ' || EXTRACT(SECOND FROM time_remaining) || ' giây để ứng tuyển'
                WHERE link = job_record.link;
            ELSEIF time_remaining < INTERVAL '1 hour' THEN
                UPDATE jobs_table
                SET deadline = 'Còn ' || EXTRACT(MINUTE FROM time_remaining) || ' phút để ứng tuyển'
                WHERE link = job_record.link;
            ELSEIF time_remaining < INTERVAL '1 day' THEN 
                UPDATE jobs_table
                SET deadline = 'Còn ' || EXTRACT(HOUR FROM time_remaining) || ' giờ để ứng tuyển'
                WHERE link = job_record.link;
            ELSE
                UPDATE jobs_table
                SET deadline = 'Còn ' || EXTRACT(DAY FROM time_remaining) || ' ngày để ứng tuyển'
                WHERE link = job_record.link;
            END IF;
        
        ELSE
            UPDATE jobs_table
            SET deadline = 'Đã hết thời gian ứng tuyển'
            WHERE link = job_record.link;
        END IF;
    END LOOP;
END;
$$;