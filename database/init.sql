CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    filename VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS copies (
    id SERIAL PRIMARY KEY,
    subject_id INTEGER REFERENCES subjects(id),
    filename VARCHAR(255) NOT NULL,
    student_name VARCHAR(255),
    upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(50) DEFAULT 'uploaded'
);

CREATE TABLE IF NOT EXISTS results (
    id SERIAL PRIMARY KEY,
    copy_id INTEGER REFERENCES copies(id),
    score DECIMAL(5,2),
    max_score DECIMAL(5,2),
    corrected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
