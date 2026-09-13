CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(200) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO users (name, email)
VALUES ('张三', 'zhang@example.com')
ON CONFLICT (email) DO UPDATE SET name = EXCLUDED.name;

SELECT id, name, email, created_at FROM users;
UPDATE users SET name = '李四' WHERE email = 'zhang@example.com';
SELECT id, name, email FROM users WHERE email = 'zhang@example.com';
DELETE FROM users WHERE email = 'zhang@example.com';
SELECT COUNT(*) AS remaining_rows FROM users WHERE email = 'zhang@example.com';
