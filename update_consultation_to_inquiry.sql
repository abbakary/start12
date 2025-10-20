-- Update existing consultation orders to inquiry
UPDATE tracker_order SET type = 'inquiry' WHERE type = 'consultation';