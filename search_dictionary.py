# ==================================================
# CENTRAL SEARCH DICTIONARY
# Caribbean Retail AI
# ==================================================

SEARCH_DICTIONARY = {

    "WHITE_BREAD": [
        "white bread",
        "pan blanco",
        "wit brood",
        "white buns",
    ],

    "WHOLE_WHEAT_BREAD": [
        "whole wheat bread",
        "wholewheat bread",
        "pan integral",
        "volkoren bread",
        "bruine brood",
    ],

    "SPECIALTY_BREAD": [
        "multigrain bread",
        "multicereal",
        "avena",
        "oat bread",
        "seed bread",
    ],

    "HAMBURGER_BUNS": [
        "hamburger buns",
        "burger buns",
        "pan hamburguesa",
    ],

    "HOTDOG_BUNS": [
        "hot dog buns",
        "hotdog buns",
        "pan hot dog",
    ],

    "TORTILLAS_WRAPS": [
        "tortilla",
        "tortillas",
        "wrap",
        "wraps",
        "burrito",
        "taco",
    ],

    "PITA_FLATBREAD": [
        "pita",
        "flatbread",
        "naan",
        "lavash",
    ],

    "TOASTED_BREAD": [
        "toast",
        "tostada",
        "tostadas",
        "melba toast",
    ],

    "BAGELS": [
        "bagel",
        "bagels",
    ],

    "SWEET_COOKIES": [
        "cookies",
        "galletas",
        "oreo",
        "chips ahoy",
        "festival",
        "chokis",
        "emperador",
    ],

    "SAVORY_CRACKERS": [
        "crackers",
        "soda crackers",
        "saltine crackers",
        "saltinas",
        "ritz",
        "club social",
    ],

    "WAFERS": [
        "wafer",
        "wafers",
        "waffer",
        "barquillo",
    ],

    "SALTY_SNACKS": [
        "pringles",
        "tostitos",
        "doritos",
        "cheetos",
        "lays",
        "chips",
        "popcorn",
        "pretzels",
    ],

    "SWEET_BAKERY": [
        "croissant",
        "muffin",
        "brownie",
        "cake",
        "cupcake",
        "bizcocho",
    ],

    "FROZEN_BAKERY": [
        "frozen bread",
        "frozen dough",
        "frozen pastry",
        "frozen pizza",
        "frozen",
    ],
}


def get_search_terms():
    return SEARCH_DICTIONARY


def get_terms_for_category(category):
    return SEARCH_DICTIONARY.get(category, [])


def flatten_search_terms():
    terms = []

    for category, values in SEARCH_DICTIONARY.items():
        for term in values:
            terms.append(
                {
                    "commercial_category": category,
                    "term": term,
                }
            )

    return terms
