import re
import pandas as pd


PRODUCT_DICTIONARY = {

    "oreo_original": [
        "oreo original",
        "galletas oreo original",
        "oreo cookies original",
    ],

    "oreo_chocolate": [
        "oreo chocolate",
        "galletas de chocolate oreo",
        "oreo chocolate cookies",
    ],

    "oreo_vanilla": [
        "oreo vanilla",
        "oreo golden vanilla",
        "galletas de vainilla oreo",
    ],

    "pringles_sour_cream_onion": [
        "pringles sour cream onion",
        "pringles sour cream & onion",
        "pringles sour cream and onion",
        "pringles s cream onion",
    ],

    "pringles_cheddar": [
        "pringles cheddar",
        "pringles cheddar cheese",
    ],

    "pringles_pizza": [
        "pringles pizza",
    ],

    "ritz_original": [
        "ritz",
        "galleta ritz",
        "ritz crackers",
    ],

    "chips_ahoy_original": [
        "chips ahoy",
        "galletas chips ahoy",
        "chips ahoy cookies",
    ],

    "bauducco_wafer_chocolate": [
        "bauducco wafer chocolate",
        "galletas wafer chocolate bauducco",
        "wafer bauducco chocolate",
    ],

    "bauducco_wafer_vanilla": [
        "bauducco wafer vanilla",
        "wafer bauducco vanilla",
    ],

    "festival_strawberry": [
        "festival strawberry",
        "noel festival strawberry",
        "festival fresa",
    ],

    "toufayan_bagels": [
        "toufayan bagels",
        "bagels toufayan",
    ],
}


def normalize_text(x):

    if pd.isna(x):
        return ""

    x = str(x).lower()

    x = re.sub(
        r"[^a-z0-9\s&]",
        " ",
        x
    )

    x = re.sub(
        r"\s+",
        " ",
        x
    ).strip()

    return x


def infer_product_from_dictionary(product_name):

    text = normalize_text(product_name)

    for canonical, variants in PRODUCT_DICTIONARY.items():

        for variant in variants:

            variant = normalize_text(variant)

            if variant and variant in text:
                return canonical

    return None
