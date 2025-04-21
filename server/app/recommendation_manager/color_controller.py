from colorsys import rgb_to_hsv


def is_monochromatic(color1: tuple, color2: tuple, hue_tolerance: float = 5.0) -> bool:
    """
    Checks if two RGB colors belong to the same monochromatic palette.
    Parameters:
        color1, color2 — RGB tuples (0-255)
        hue_tolerance — allowed hue deviation in degrees (0-360)
    """
    r1, g1, b1 = [x / 255.0 for x in color1]
    r2, g2, b2 = [x / 255.0 for x in color2]

    h1, _, _ = rgb_to_hsv(r1, g1, b1)
    h2, _, _ = rgb_to_hsv(r2, g2, b2)

    hue1 = h1 * 360
    hue2 = h2 * 360

    return abs(hue1 - hue2) <= hue_tolerance


def is_analogous(color1: tuple, color2: tuple, max_hue_difference: float = 30.0) -> bool:
    """
    Checks if two RGB colors are analogous (located next to each other on the color wheel).
    Parameters:
        color1, color2 — RGB tuples (0-255)
        max_hue_difference — maximum allowed hue difference in degrees
    """
    r1, g1, b1 = [x / 255.0 for x in color1]
    r2, g2, b2 = [x / 255.0 for x in color2]

    h1, _, _ = rgb_to_hsv(r1, g1, b1)
    h2, _, _ = rgb_to_hsv(r2, g2, b2)

    hue1 = h1 * 360
    hue2 = h2 * 360

    hue_diff = abs(hue1 - hue2)
    hue_diff = min(hue_diff, 360 - hue_diff)  # account for circular hue values

    return hue_diff <= max_hue_difference


def is_complementary(color1: tuple, color2: tuple, hue_tolerance: float = 15.0) -> bool:
    """
    Checks if two RGB colors are complementary.
    Parameters:
        color1, color2 — RGB tuples (0-255)
        hue_tolerance — allowed deviation from 180 degrees in hue
    """
    r1, g1, b1 = [x / 255.0 for x in color1]
    r2, g2, b2 = [x / 255.0 for x in color2]

    h1, _, _ = rgb_to_hsv(r1, g1, b1)
    h2, _, _ = rgb_to_hsv(r2, g2, b2)

    hue1 = h1 * 360
    hue2 = h2 * 360

    hue_diff = abs(hue1 - hue2)
    hue_diff = min(hue_diff, 360 - hue_diff)  # account for the color wheel

    return abs(hue_diff - 180) <= hue_tolerance


def is_split_complementary(color1: tuple, color2: tuple, hue_tolerance: float = 15.0, split_angle: float = 30.0) -> bool:
    """
    Checks if the second color is one of the split-complementary colors of the first.
    color1 — base color
    color2 — the color to check
    """
    r1, g1, b1 = [x / 255.0 for x in color1]
    r2, g2, b2 = [x / 255.0 for x in color2]

    h1, _, _ = rgb_to_hsv(r1, g1, b1)
    h2, _, _ = rgb_to_hsv(r2, g2, b2)

    hue1 = h1 * 360
    hue2 = h2 * 360

    # Complementary hue
    comp_hue = (hue1 + 180) % 360
    # Two split-complementary hues
    split1 = (comp_hue - split_angle) % 360
    split2 = (comp_hue + split_angle) % 360

    def close(a, b):
        return abs((a - b + 180) % 360 - 180) <= hue_tolerance

    return close(hue2, split1) or close(hue2, split2)


def is_triadic(color1: tuple, color2: tuple, hue_tolerance: float = 15.0) -> bool:
    """
    Checks if the second color forms a triadic pair with the first.
    color1 — base color (RGB)
    color2 — the color to check
    """
    r1, g1, b1 = [x / 255.0 for x in color1]
    r2, g2, b2 = [x / 255.0 for x in color2]

    h1, _, _ = rgb_to_hsv(r1, g1, b1)
    h2, _, _ = rgb_to_hsv(r2, g2, b2)

    hue1 = h1 * 360
    hue2 = h2 * 360

    triad1 = (hue1 + 120) % 360
    triad2 = (hue1 - 120) % 360

    def close(a, b):
        return abs((a - b + 180) % 360 - 180) <= hue_tolerance

    return close(hue2, triad1) or close(hue2, triad2)


def is_rectangle_palette_match(color1: tuple, color2: tuple, hue_tolerance: float = 15.0) -> bool:
    """
    Checks if the second color forms a rectangular palette with the first.
    """
    r1, g1, b1 = [x / 255.0 for x in color1]
    r2, g2, b2 = [x / 255.0 for x in color2]

    h1, _, _ = rgb_to_hsv(r1, g1, b1)
    h2, _, _ = rgb_to_hsv(r2, g2, b2)

    hue1 = h1 * 360
    hue2 = h2 * 360

    # Determine hues for a rectangular palette
    hues = [
        (hue1 + 60) % 360,
        (hue1 + 180) % 360,
        (hue1 + 240) % 360
    ]

    def close(a, b):
        return abs((a - b + 180) % 360 - 180) <= hue_tolerance

    return any(close(hue2, h) for h in hues)

def is_color_match(color1: tuple, color2: tuple, palette_type: str, hue_tolerance: float = 15.0) -> bool:
    """
    Використовує відповідну функцію, щоб перевірити, чи два кольори відповідають зазначеній гамі.

    Parameters:
        color1, color2 — RGB кортежі (0-255)
        palette_type — тип гами: 'monochromatic', 'analogous', 'complementary',
                        'split_complementary', 'triadic', 'rectangle'
        hue_tolerance — допустиме відхилення по тону в градусах
    Returns:
        bool — чи відповідають кольори заданій гамі
    """
    palette_type = palette_type.lower()

    if palette_type == "monochromatic":
        return is_monochromatic(color1, color2, hue_tolerance=hue_tolerance)
    
    elif palette_type == "analogous":
        return is_analogous(color1, color2, max_hue_difference=30.0)
    
    elif palette_type == "complementary":
        return is_complementary(color1, color2, hue_tolerance=hue_tolerance)
    
    elif palette_type == "split_complementary":
        return is_split_complementary(color1, color2, hue_tolerance=30.0)
    
    elif palette_type == "triadic":
        return is_triadic(color1, color2, hue_tolerance=hue_tolerance)
    
    elif palette_type == "rectangle":
        return is_rectangle_palette_match(color1, color2, hue_tolerance=hue_tolerance)
    
    else:
        raise ValueError(f"❌ Unsupported palette type: '{palette_type}'")


color_a = (255, 100, 50)   # bright red
color_b = (255, 180, 60)   # orange
print(is_monochromatic(color_a, color_b))  # True if they have similar hue

print(is_analogous(color_a, color_b))  # True because the hues are close

print(is_complementary(color_a, color_b))  # False, not complementary

blue = (0, 0, 255)
yellow = (255, 255, 0)
print(is_complementary(color_a, color_b))  # False, not complementary
