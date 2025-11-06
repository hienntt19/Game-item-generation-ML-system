-- CREATE DATABASE image_requests;

-- \c image_requests;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS generation_requests (
    request_id UUID PRIMARY KEY,
    prompt TEXT NOT NULL,
    negative_prompt TEXT,
    num_inference_steps INTEGER,
    guidance_scale REAL,
    seed BIGINT,
    status VARCHAR(20) NOT NULL DEFAULT 'Pending',
    image_url TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (now() AT TIME ZONE 'utc')
);

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
   NEW.updated_at = (now() AT TIME ZONE 'utc');
   RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_generation_requests_updated_at
BEFORE UPDATE ON generation_requests
FOR EACH ROW
EXECUTE PROCEDURE update_updated_at_column();

COMMENT ON TABLE generation_requests IS 'Stores image generation requests and their statuses.';