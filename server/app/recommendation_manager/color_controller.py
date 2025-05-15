from colorsys import rgb_to_hsv

def hue_distance(h1, h2):
    """Найкоротша відстань між двома відтінками у градусах."""
    return min(abs(h1 - h2), 360 - abs(h1 - h2))

def normalize_score(diff, ideal=0.0, max_range=180.0):
    """Нормалізує різницю до значення в діапазоні [0, 1]."""
    return max(0.0, 1.0 - abs(diff - ideal) / max_range)

def get_hues(color1, color2):
    r1, g1, b1 = [x / 255.0 for x in color1]
    r2, g2, b2 = [x / 255.0 for x in color2]
    h1, _, _ = rgb_to_hsv(r1, g1, b1)
    h2, _, _ = rgb_to_hsv(r2, g2, b2)
    return h1 * 360, h2 * 360

def monochromatic_score(color1, color2):
    h1, h2 = get_hues(color1, color2)
    diff = hue_distance(h1, h2)
    return normalize_score(diff, ideal=0.0, max_range=30.0)  # 60° max для монохромних

def analogous_score(color1, color2):
    h1, h2 = get_hues(color1, color2)
    diff = hue_distance(h1, h2)
    return normalize_score(diff, ideal=0.0, max_range=60.0)  # ~30° з кожного боку

def complementary_score(color1, color2):
    h1, h2 = get_hues(color1, color2)
    diff = hue_distance(h1, h2)
    return normalize_score(diff, ideal=180.0, max_range=180.0)

def split_complementary_score(color1, color2):
    h1, h2 = get_hues(color1, color2)
    comp_hue = (h1 + 180) % 360
    split1 = (comp_hue - 30) % 360
    split2 = (comp_hue + 30) % 360
    score1 = normalize_score(hue_distance(h2, split1), ideal=0.0, max_range=60.0)
    score2 = normalize_score(hue_distance(h2, split2), ideal=0.0, max_range=60.0)
    return max(score1, score2)

def triadic_score(color1, color2):
    h1, h2 = get_hues(color1, color2)
    triad1 = (h1 + 120) % 360
    triad2 = (h1 - 120) % 360
    score1 = normalize_score(hue_distance(h2, triad1), ideal=0.0, max_range=60.0)
    score2 = normalize_score(hue_distance(h2, triad2), ideal=0.0, max_range=60.0)
    return max(score1, score2)

def rectangle_palette_score(color1, color2):
    h1, h2 = get_hues(color1, color2)
    hues = [(h1 + 60) % 360, (h1 + 180) % 360, (h1 + 240) % 360]
    scores = [normalize_score(hue_distance(h2, target), ideal=0.0, max_range=60.0) for target in hues]
    return max(scores)

def color_match_score(color1: tuple, color2: tuple, palette_type: str) -> float:
    palette_type = palette_type.lower()
    if palette_type == "monochromatic":
        return monochromatic_score(color1, color2)
    elif palette_type == "analogous":
        return analogous_score(color1, color2)
    elif palette_type == "complementary":
        return complementary_score(color1, color2)
    elif palette_type == "split_complementary":
        return split_complementary_score(color1, color2)
    elif palette_type == "triadic":
        return triadic_score(color1, color2)
    elif palette_type == "rectangle":
        return rectangle_palette_score(color1, color2)
    else:
        raise ValueError(f"❌ Unsupported palette type: '{palette_type}'")
