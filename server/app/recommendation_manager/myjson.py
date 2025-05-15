import json
import os

def get_nested_value(filename: str, path: str):
    """
    Отримує вкладене значення з JSON-файлу за шляхом, наприклад: "tshirt.weather.sunny"

    :param filename: Назва JSON-файлу.
    :param path: Шлях до значення через крапку (наприклад: "tshirt.weather.sunny").
    :return: Значення або повідомлення про помилку.
    """
    try:
        base_path = os.path.dirname(__file__)
        full_path = os.path.join(base_path, filename)
        with open(full_path, 'r', encoding='utf-8') as file:
            
            data = json.load(file)

        keys = path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return f"Шлях '{path}' недійсний. Не знайдено ключ: '{key}'"

        return current

    except FileNotFoundError:
        return f"Файл '{filename}' не знайдено."
    except json.JSONDecodeError:
        return f"Файл '{filename}' не є валідним JSON."

print(get_nested_value("weather_recommendations.json", "tshirt.weather.sunny"))
# ➜ 1.0

print(get_nested_value("event_recommendations.json", "tshirt.event.date"))

