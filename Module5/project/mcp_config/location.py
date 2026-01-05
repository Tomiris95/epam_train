import re

def extract_location(text, memory=None):
    match = re.search(r"in\s+([a-zA-Z\s]+)", text, re.IGNORECASE)

    # 1️⃣ Город явно указан пользователем
    if match:
        city = match.group(1).strip()
        if memory:
            memory.last_location = city
            print("✅ City set from user:", city)
        return city

    # 2️⃣ Пользователь не указал, но он есть в памяти
    if memory and getattr(memory, "last_location", None):
        print("↩ Using city from memory:", memory.last_location)
        return memory.last_location

    # 3️⃣ Город неизвестен — НЕ ГАДАЕМ
    return None