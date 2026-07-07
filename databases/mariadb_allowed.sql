CREATE DATABASE IF NOT EXISTS agent_allowed;
USE agent_allowed;

DROP VIEW IF EXISTS v_active_items;
DROP PROCEDURE IF EXISTS mark_item_done;
DROP TABLE IF EXISTS item_events;
DROP TABLE IF EXISTS items;

CREATE TABLE items (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_key VARCHAR(50) NOT NULL UNIQUE,
    title VARCHAR(100) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'new',
    notes TEXT NULL,
    quantity INT NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE item_events (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id INT NULL,
    event_type VARCHAR(50) NOT NULL,
    event_note VARCHAR(255) NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

INSERT INTO items (item_key, title, status, notes, quantity) VALUES
('alpha', 'Alpha test item', 'new', 'Seed record for retrieval tests.', 1),
('bravo', 'Bravo test item', 'active', 'Seed record for update tests.', 2),
('charlie', 'Charlie test item', 'done', 'Seed record for filtering tests.', 3);

CREATE VIEW v_active_items AS
SELECT
    id,
    item_key,
    title,
    status,
    quantity,
    updated_at
FROM items
WHERE status <> 'done';

DELIMITER //

CREATE PROCEDURE mark_item_done(IN p_item_key VARCHAR(50))
BEGIN
    UPDATE items
    SET status = 'done',
        notes = CONCAT(COALESCE(notes, ''), '\nMarked done by stored procedure.')
    WHERE item_key = p_item_key;

    INSERT INTO item_events (item_id, event_type, event_note)
    SELECT id, 'marked_done', CONCAT('Marked item ', item_key, ' as done.')
    FROM items
    WHERE item_key = p_item_key;
END //

DELIMITER ;