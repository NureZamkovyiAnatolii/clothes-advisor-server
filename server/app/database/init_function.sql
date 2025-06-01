use clothes_advisor;
-- source D:/Study/4 course/diploma/clothes-advisor-server/server/app/database/init_function.sql;
DELIMITER $$

CREATE PROCEDURE IF NOT EXISTS get_category_stats_by_owner(IN input_owner_id INT)
BEGIN
    SELECT category, COUNT(*) AS item_count
    FROM CLOTHING_ITEMS
    WHERE owner_id = input_owner_id
    GROUP BY category;
END $$

CREATE PROCEDURE IF NOT EXISTS get_average_item_age_by_owner(IN input_owner_id INT)
BEGIN
    SELECT 
        category,
        ROUND(AVG(DATEDIFF(CURDATE(), purchase_date)), 1) AS average_age_days
    FROM CLOTHING_ITEMS
    WHERE owner_id = input_owner_id
      AND purchase_date IS NOT NULL
    GROUP BY category;
END $$

CREATE PROCEDURE IF NOT EXISTS get_season_stats_by_owner(IN input_owner_id INT)
BEGIN
    SELECT season, COUNT(*) AS item_count
    FROM CLOTHING_ITEMS
    WHERE owner_id = input_owner_id
    GROUP BY season;
END $$

CREATE PROCEDURE IF NOT EXISTS get_material_stats_by_owner(IN input_owner_id INT)
BEGIN
    SELECT material, COUNT(*) AS item_count
    FROM CLOTHING_ITEMS
    WHERE owner_id = input_owner_id
    GROUP BY material;
END $$

DELIMITER ;
