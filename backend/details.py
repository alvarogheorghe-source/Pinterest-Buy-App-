"""Schnitt & Details: die genauen Merkmale eines Teils – "Bootcut", "Light Wash", "Rollkragen" …

Farbe + Stil + Kategorie ("schwarze Hose") ist zu grob. Wer Baggy-Jeans in Light Wash pinnt,
will keine schwarzen Skinny-Jeans sehen. Deshalb erkennt die App pro Kategorie mehrere
Merkmale aus den Pin-Texten (später auch aus dem Bild, image_tags.py) und nutzt sie:
- für genauere Suchen:   "Herren Baggy Light Wash Jeans" statt "Herren Hose"
- fürs Ranking:          Bootcut-Jeans vor Skinny-Jeans, wenn du Bootcut pinnst

Jedes Merkmal gehört zu einer Gruppe. Pro Suche höchstens ein Merkmal je Gruppe
(keine "Skinny Bootcut Jeans"). Gruppe "typ" ist besonders: Sie ersetzt das Kategorie-Wort
("Hoodie" statt "Pullover", "Chelsea Boots" statt "Sneaker").

Neue Merkmale einfach unten eintragen:  Detail(Gruppe, Kategorien, Deutsch, Englisch, Wörter)
Wörter wie bei matching.py: Deutsch + Englisch, "*" vorne erlaubt zusammengesetzte Wörter.
"""

from dataclasses import dataclass

from backend.matching import ADJECTIVE, _compile, find_terms

HOSEN, OBEN, JACKEN, KLEIDER, SCHUHE, ACC = ("Hosen", "Oberteile", "Jacken", "Kleider & Röcke",
                                            "Schuhe", "Accessoires")
MODE = (HOSEN, OBEN, JACKEN, KLEIDER, SCHUHE, ACC)
KLEIDUNG = (HOSEN, OBEN, JACKEN, KLEIDER)


@dataclass(frozen=True)
class Detail:
    group: str                   # "schnitt", "bund", "waschung", "länge", "typ" …
    categories: tuple[str, ...]  # wo das Merkmal Sinn ergibt
    de: str                      # Suchwort eBay (Deutsch) – auch der Anzeigename
    en: str                      # Suchwort Etsy/AliExpress (Englisch)
    words: tuple[str, ...]       # so steht es in Pins und Produkttiteln


def _d(group, categories, de, en, *words) -> Detail:
    return Detail(group, tuple(categories), de, en, tuple(words))


DETAILS = [
    # --- Hosen: Typ ------------------------------------------------------------------------------
    _d("typ", [HOSEN], "Jeans", "jeans", "*jeans", "denim pants"),
    _d("typ", [HOSEN], "Cargohose", "cargo pants", "cargohose", "cargo pants", "cargos",
       "cargo trousers"),
    _d("typ", [HOSEN], "Jogginghose", "sweatpants", "jogginghose", "sweatpants", "jogger",
       "joggers", "trackpants", "track pants", "trainingshose"),
    _d("typ", [HOSEN], "Anzughose", "tailored trousers", "anzughose", "stoffhose", "bundfaltenhose",
       "tailored trousers", "suit pants", "dress pants", "pleated trousers", "slacks"),
    _d("typ", [HOSEN], "Shorts", "shorts", "shorts", "jorts", "bermuda", "bermudas"),
    _d("typ", [HOSEN], "Leggings", "leggings", "leggings", "yoga pants", "flared leggings"),
    _d("typ", [HOSEN], "Lederhose", "leather pants", "lederhose", "leather pants",
       "leather trousers"),
    # --- Hosen: Schnitt --------------------------------------------------------------------------
    _d("schnitt", [HOSEN], "Bootcut", "bootcut", "bootcut", "boot cut", "boot-cut"),
    _d("schnitt", [HOSEN], "Straight Leg", "straight leg", "straight", "straight leg",
       "straight-leg", "straight fit", "gerades bein", "gerade geschnitten"),
    _d("schnitt", [HOSEN], "Wide Leg", "wide leg", "wide leg", "wide-leg", "weites bein",
       "weite", "palazzo", "culotte", "culottes"),
    _d("schnitt", [HOSEN], "Baggy", "baggy", "baggy", "loose", "loose fit", "relaxed",
       "relaxed fit", "skater jeans", "skater pants"),
    _d("schnitt", [HOSEN], "Skinny", "skinny", "skinny", "röhre", "röhrenjeans", "jeggings"),
    _d("schnitt", [HOSEN], "Slim Fit", "slim fit", "slim", "slim fit", "slim-fit"),
    _d("schnitt", [HOSEN], "Flared", "flare", "flared", "flare", "flares", "schlag", "schlaghose",
       "bell bottom", "bell bottoms", "bell-bottom", "ausgestellt"),
    _d("schnitt", [HOSEN], "Mom Jeans", "mom jeans", "mom jeans", "mom fit", "mom-jeans",
       "momjeans"),
    _d("schnitt", [HOSEN], "Barrel", "barrel", "barrel", "barrel leg", "horseshoe"),
    _d("schnitt", [HOSEN], "Tapered", "tapered", "tapered", "karottenhose", "carrot fit"),
    _d("schnitt", [HOSEN], "Parachute", "parachute pants", "parachute", "fallschirmhose"),
    _d("schnitt", [HOSEN], "Carpenter", "carpenter", "carpenter", "carpenter pants",
       "double knee", "workwear pants"),
    # --- Hosen: Bund -----------------------------------------------------------------------------
    _d("bund", [HOSEN, KLEIDER], "High Waist", "high waisted", "high waist", "high-waist",
       "highwaist", "high waisted", "high rise", "high-rise", "hoher bund"),
    _d("bund", [HOSEN, KLEIDER], "Low Rise", "low rise", "low rise", "low-rise", "low waist",
       "low-waist", "tiefer bund", "hüfthose", "hüftjeans"),
    _d("bund", [HOSEN], "Mid Rise", "mid rise", "mid rise", "mid-rise", "mid waist"),
    # --- Waschung (Denim) ----------------------------------------------------------------------
    _d("waschung", [HOSEN, JACKEN, KLEIDER], "Light Wash", "light wash", "light wash",
       "light-wash", "lightwash", "helle waschung", "light blue denim", "hellblaue jeans"),
    _d("waschung", [HOSEN, JACKEN, KLEIDER], "Dark Wash", "dark wash", "dark wash", "dark-wash",
       "raw denim", "rinse wash", "dunkle waschung", "indigo"),
    _d("waschung", [HOSEN, JACKEN, KLEIDER], "Washed Black", "washed black", "washed black",
       "faded black", "black wash", "washed grey"),
    _d("waschung", [HOSEN, JACKEN, KLEIDER, OBEN], "Acid Wash", "acid wash", "acid wash",
       "acid-wash", "stonewashed", "stone washed", "stonewash", "bleached"),
    _d("used", [HOSEN, JACKEN, KLEIDER, OBEN], "Distressed", "distressed", "distressed",
       "ripped", "destroyed", "used look", "zerrissen", "risse"),
    # --- Oberteile: Typ --------------------------------------------------------------------------
    _d("typ", [OBEN], "Hoodie", "hoodie", "hoodie", "hoody", "kapuzenpullover", "zip hoodie",
       "zip-hoodie"),
    _d("typ", [OBEN], "Sweatshirt", "sweatshirt", "sweatshirt", "crewneck", "crew neck sweater"),
    _d("typ", [OBEN], "T-Shirt", "t-shirt", "t-shirt", "tshirt", "t shirt", "graphic tee",
       "baby tee", "tee shirt"),
    _d("typ", [OBEN], "Hemd", "button up shirt", "*hemd", "button up", "button-up", "button down",
       "button-down", "flannel", "flanellhemd", "overshirt"),
    _d("typ", [OBEN], "Bluse", "blouse", "*bluse", "blouse"),
    _d("typ", [OBEN], "Strickpullover", "knit sweater", "strickpullover", "knit sweater",
       "knitted sweater", "jumper", "cable knit"),
    _d("typ", [OBEN, JACKEN], "Cardigan", "cardigan", "cardigan", "strickjacke"),
    _d("typ", [OBEN], "Tanktop", "tank top", "tank top", "tanktop", "trägertop", "camisole",
       "cami", "spaghettiträger"),
    _d("typ", [OBEN], "Longsleeve", "long sleeve top", "longsleeve", "long sleeve",
       "langarmshirt"),
    _d("typ", [OBEN], "Poloshirt", "polo shirt", "polo", "poloshirt", "polo shirt"),
    _d("typ", [OBEN], "Korsett", "corset top", "korsett", "corset", "bustier"),
    _d("typ", [OBEN], "Pullunder", "sweater vest", "pullunder", "sweater vest", "strickweste"),
    _d("typ", [OBEN], "Trikot", "jersey", "trikot", "jersey", "football shirt", "fußballtrikot"),
    _d("typ", [OBEN], "Bodysuit", "bodysuit", "bodysuit", "body"),
    # --- Oberteile & Jacken: Schnitt -------------------------------------------------------------
    _d("schnitt", [OBEN, JACKEN, HOSEN], "Cropped", "cropped", "cropped", "crop", "bauchfrei",
       "kurz geschnitten"),
    _d("schnitt", [OBEN, JACKEN], "Boxy", "boxy", "boxy", "boxy fit"),
    _d("schnitt", [OBEN, KLEIDER], "Figurbetont", "fitted", "fitted", "figurbetont", "tight",
       "eng anliegend", "slim fit top", "bodycon"),
    _d("schnitt", [OBEN, JACKEN], "Longline", "longline", "longline", "extra lang"),
    _d("schnitt", [OBEN, JACKEN], "Zip", "half zip", "half zip", "half-zip", "quarter zip",
       "quarter-zip", "troyer", "zip up", "zip-up"),
    # --- Ausschnitt & Ärmel ------------------------------------------------------------------------
    _d("ausschnitt", [OBEN, KLEIDER], "Rollkragen", "turtleneck", "rollkragen", "turtleneck",
       "mock neck", "stehkragen", "rollkragenpullover"),
    _d("ausschnitt", [OBEN, KLEIDER], "V-Ausschnitt", "v-neck", "v-ausschnitt", "v-neck",
       "v neck"),
    _d("ausschnitt", [OBEN, KLEIDER], "Schulterfrei", "off shoulder", "schulterfrei",
       "off shoulder", "off-shoulder", "carmen"),
    _d("ausschnitt", [OBEN, KLEIDER], "Neckholder", "halter", "neckholder", "halter",
       "halterneck", "halter neck"),
    _d("ausschnitt", [OBEN, KLEIDER], "Square Neck", "square neck", "square neck", "karree",
       "karree-ausschnitt"),
    _d("ausschnitt", [OBEN, KLEIDER], "Rückenfrei", "backless", "rückenfrei", "backless",
       "open back"),
    _d("ärmel", [OBEN, KLEIDER], "Puffärmel", "puff sleeve", "puffärmel", "puff sleeve",
       "puff sleeves", "ballonärmel"),
    _d("ärmel", [OBEN, KLEIDER], "Ärmellos", "sleeveless", "ärmellos", "sleeveless"),
    # --- Jacken: Typ -----------------------------------------------------------------------------
    _d("typ", [JACKEN], "Jeansjacke", "denim jacket", "jeansjacke", "denim jacket",
       "jean jacket", "trucker jacket"),
    _d("typ", [JACKEN], "Lederjacke", "leather jacket", "lederjacke", "leather jacket"),
    _d("typ", [JACKEN], "Bikerjacke", "biker jacket", "bikerjacke", "biker jacket",
       "moto jacket", "motorradjacke"),
    _d("typ", [JACKEN], "Bomberjacke", "bomber jacket", "bomber", "bomberjacke", "flight jacket",
       "pilotenjacke"),
    _d("typ", [JACKEN], "Pufferjacke", "puffer jacket", "puffer", "pufferjacke", "daunenjacke",
       "steppjacke", "down jacket", "puffy jacket"),
    _d("typ", [JACKEN], "Trenchcoat", "trench coat", "trench", "trenchcoat", "trench coat"),
    _d("typ", [JACKEN], "Blazer", "blazer", "blazer", "sakko"),
    _d("typ", [JACKEN], "Mantel", "coat", "*mantel", "coat", "overcoat", "wool coat"),
    _d("typ", [JACKEN], "Windbreaker", "windbreaker", "windbreaker", "windjacke", "track jacket",
       "trainingsjacke"),
    _d("typ", [JACKEN], "Collegejacke", "varsity jacket", "varsity", "collegejacke",
       "college jacke", "letterman"),
    _d("typ", [JACKEN], "Arbeitsjacke", "work jacket", "work jacket", "arbeitsjacke",
       "chore jacket", "detroit jacket", "workwear jacket"),
    _d("typ", [JACKEN], "Parka", "parka", "parka"),
    _d("typ", [JACKEN], "Fleecejacke", "fleece jacket", "fleecejacke", "fleece jacket",
       "teddyjacke", "sherpa jacket"),
    _d("typ", [JACKEN, OBEN], "Weste", "vest", "weste", "puffer vest", "gilet"),
    # --- Kleider & Röcke -----------------------------------------------------------------------
    _d("typ", [KLEIDER], "Rock", "skirt", "rock", "minirock", "midirock", "maxirock", "jeansrock",
       "faltenrock", "skirt"),
    _d("typ", [KLEIDER], "Jumpsuit", "jumpsuit", "jumpsuit", "overall", "playsuit", "romper"),
    _d("länge", [KLEIDER, ACC], "Mini", "mini", "mini", "minikleid", "minirock", "short dress",
       "mini skirt", "mini dress", "mini bag"),
    _d("länge", [KLEIDER], "Midi", "midi", "midi", "midikleid", "midirock", "midi dress",
       "midi skirt"),
    _d("länge", [KLEIDER], "Maxi", "maxi", "maxi", "maxikleid", "maxirock", "bodenlang",
       "maxi dress", "maxi skirt"),
    _d("schnitt", [KLEIDER], "A-Linie", "a-line", "a-linie", "a-line", "a line", "skater skirt"),
    _d("schnitt", [KLEIDER], "Slip", "slip", "slip dress", "slipdress", "slip skirt"),
    _d("schnitt", [KLEIDER], "Wickel", "wrap", "wickelkleid", "wickelrock", "wrap dress",
       "wrap skirt"),
    _d("schnitt", [KLEIDER], "Plissee", "pleated", "plissee", "pleated", "faltenrock",
       "plisseerock"),
    _d("schnitt", [KLEIDER], "Tüll", "tulle", "tüll", "tulle", "tutu"),
    _d("schnitt", [KLEIDER], "Hemdblusenkleid", "shirt dress", "hemdblusenkleid", "shirt dress",
       "shirtdress"),
    # --- Schuhe ----------------------------------------------------------------------------------
    _d("typ", [SCHUHE], "Sneaker", "sneakers", "*sneaker", "trainers"),
    _d("typ", [SCHUHE], "Stiefel", "boots", "*stiefel", "boot", "boots", "stiefelette",
       "stiefeletten", "ankle boots"),
    _d("typ", [SCHUHE], "Chelsea Boots", "chelsea boots", "chelsea", "chelsea boots"),
    _d("typ", [SCHUHE], "Cowboystiefel", "cowboy boots", "cowboy", "cowboystiefel",
       "western boots", "westernstiefel"),
    _d("typ", [SCHUHE], "Combat Boots", "combat boots", "combat boots", "springerstiefel",
       "biker boots", "lace up boots", "schnürstiefel"),
    _d("typ", [SCHUHE], "Loafer", "loafers", "loafer", "loafers", "penny loafer", "mokassin"),
    _d("typ", [SCHUHE], "Ballerinas", "ballet flats", "ballerina", "ballerinas", "ballet flats",
       "ballet flat"),
    _d("typ", [SCHUHE], "Mary Janes", "mary jane shoes", "mary jane", "mary janes",
       "spangenschuhe"),
    _d("typ", [SCHUHE], "Sandalen", "sandals", "sandale", "sandalen", "sandals", "slides",
       "pantoletten", "flip flops", "riemchensandalen"),
    _d("typ", [SCHUHE], "Clogs", "clogs", "clog", "clogs"),
    _d("typ", [SCHUHE], "Heels", "heels", "heels", "high heels", "pumps", "stiletto",
       "stilettos", "kitten heels", "absatzschuhe", "slingback", "slingbacks"),
    _d("typ", [SCHUHE], "Hausschuhe", "slippers", "hausschuhe", "slipper", "slippers"),
    _d("schnitt", [SCHUHE, ACC], "Chunky", "chunky", "chunky", "klobig", "dad shoes",
       "dad sneaker", "dad sneakers"),
    _d("sohle", [SCHUHE], "Plateau", "platform", "plateau", "platform", "plateausohle"),
    _d("schaft", [SCHUHE], "High Top", "high top", "high top", "high-top", "hi top"),
    _d("schaft", [SCHUHE], "Low Top", "low top", "low top", "low-top"),
    _d("schaft", [SCHUHE], "Kniehoch", "knee high", "kniehoch", "knee high", "knee-high",
       "overknee", "over the knee"),
    _d("schnitt", [SCHUHE], "Spitz", "pointed toe", "spitz", "pointed", "pointed toe",
       "pointy"),
    _d("schnitt", [SCHUHE], "Retro Runner", "retro running", "retro runner", "retro running",
       "running sneaker", "laufschuh"),
    # --- Accessoires ---------------------------------------------------------------------------
    _d("typ", [ACC], "Schultertasche", "shoulder bag", "schultertasche", "shoulder bag",
       "baguette bag", "crossbody", "umhängetasche", "crossbody bag"),
    _d("typ", [ACC], "Rucksack", "backpack", "rucksack", "backpack"),
    _d("typ", [ACC], "Shopper", "tote bag", "tote", "tote bag", "shopper", "jutebeutel"),
    _d("typ", [ACC], "Clutch", "clutch", "clutch", "abendtasche"),
    _d("typ", [ACC], "Gürteltasche", "belt bag", "gürteltasche", "bauchtasche", "belt bag",
       "fanny pack", "bum bag"),
    _d("typ", [ACC], "Kette", "necklace", "kette", "halskette", "necklace", "choker"),
    _d("typ", [ACC], "Ohrringe", "earrings", "ohrringe", "earrings", "creolen", "hoops",
       "hoop earrings"),
    _d("typ", [ACC], "Ring", "ring", "ring", "ringe", "rings"),
    _d("typ", [ACC], "Armband", "bracelet", "armband", "bracelet", "armreif"),
    _d("typ", [ACC], "Gürtel", "belt", "*gürtel", "belt"),
    _d("typ", [ACC], "Mütze", "beanie", "beanie", "*mütze", "strickmütze"),
    _d("typ", [ACC], "Cap", "cap", "cap", "basecap", "baseball cap", "kappe", "trucker cap"),
    _d("typ", [ACC], "Sonnenbrille", "sunglasses", "sonnenbrille", "sunglasses", "shades"),
    _d("typ", [ACC], "Schal", "scarf", "schal", "scarf", "halstuch", "bandana", "seidentuch"),
    _d("typ", [ACC], "Haarklammer", "claw clip", "haarklammer", "claw clip", "haarspange",
       "hair clip", "scrunchie"),
    # --- Material (alle Kleidung) ------------------------------------------------------------
    _d("material", MODE, "Leder", "leather", "leder", "echtleder", "leather"),
    _d("material", MODE, "Kunstleder", "faux leather", "kunstleder", "faux leather",
       "vegan leather", "pu leather"),
    _d("material", MODE, "Wildleder", "suede", "wildleder", "suede", "velours"),
    _d("material", KLEIDUNG, "Denim", "denim", "denim"),
    _d("material", KLEIDUNG, "Leinen", "linen", "leinen", "linen"),
    _d("material", KLEIDUNG, "Cord", "corduroy", "cord", "kord", "corduroy", "cordhose"),
    _d("material", KLEIDUNG + (ACC,), "Satin", "satin", "satin", "seide", "silk", "silky"),
    _d("material", KLEIDUNG + (ACC,), "Wolle", "wool", "wolle", "wool", "merino", "kaschmir",
       "cashmere", "alpaka", "mohair"),
    _d("material", KLEIDUNG + (SCHUHE,), "Fleece", "fleece", "fleece", "teddy", "sherpa",
       "plüsch", "faux fur", "kunstfell"),
    _d("material", KLEIDUNG, "Strick", "knit", "strick", "knit", "knitted", "gestrickt",
       "zopfmuster", "crochet", "häkel"),
    _d("material", KLEIDUNG + (ACC,), "Spitze", "lace", "spitze", "lace"),
    _d("material", KLEIDUNG, "Mesh", "mesh", "mesh", "sheer", "transparent", "netzstoff"),
    _d("material", KLEIDUNG, "Nylon", "nylon", "nylon", "shell", "ripstop"),
    _d("material", KLEIDUNG, "Samt", "velvet", "samt", "velvet", "velour"),
    _d("material", KLEIDUNG + (SCHUHE, ACC), "Lack", "patent", "lack", "lackleder", "patent",
       "latex", "vinyl"),
    # --- Muster (alle Mode) ----------------------------------------------------------------------
    _d("muster", MODE, "Gestreift", "striped", "gestreift", "streifen", "striped", "stripes",
       "pinstripe", "nadelstreifen"),
    _d("muster", MODE, "Kariert", "plaid", "kariert", "karo", "plaid", "tartan", "checked",
       "gingham", "vichy", "houndstooth", "hahnentritt"),
    _d("muster", MODE, "Geblümt", "floral", "geblümt", "blumenmuster", "floral print",
       "flower print", "ditsy"),
    _d("muster", MODE, "Leo", "leopard", "leo", "leopard", "leoprint", "animal print",
       "leopardenmuster"),
    _d("muster", MODE, "Zebra", "zebra", "zebra", "zebra print"),
    _d("muster", MODE, "Gepunktet", "polka dot", "gepunktet", "punkte", "polka dot",
       "polka dots", "dotted"),
    _d("muster", MODE, "Camouflage", "camo", "camo", "camouflage", "tarnmuster"),
    _d("muster", MODE, "Print", "graphic", "graphic", "print", "aufdruck", "motiv", "printed"),
    _d("muster", MODE, "Batik", "tie dye", "batik", "tie dye", "tie-dye"),
    _d("muster", MODE, "Paisley", "paisley", "paisley", "bandana print"),
    _d("muster", MODE, "Colorblock", "color block", "colorblock", "color block",
       "colour block", "colourblock"),
    _d("muster", MODE, "Glitzer", "sequin", "glitzer", "pailletten", "sequin", "sequins",
       "glitter", "sparkly", "metallic"),
    # --- Kleine Details ---------------------------------------------------------------------------
    _d("detail", KLEIDUNG, "Schleife", "bow", "schleife", "schleifen", "bow detail"),
    _d("detail", KLEIDUNG, "Rüschen", "ruffle", "rüschen", "ruffle", "ruffles", "volant",
       "frills"),
    _d("detail", KLEIDUNG + (SCHUHE, ACC), "Fransen", "fringe", "fransen", "fringe"),
    _d("detail", KLEIDUNG, "Schnürung", "lace up", "schnürung", "lace-up", "lace up",
       "tie front"),
    _d("detail", KLEIDUNG, "Cut Out", "cut out", "cut out", "cut-out", "cutout"),
    _d("detail", KLEIDUNG, "Raw Hem", "raw hem", "raw hem", "offener saum", "frayed"),
    _d("detail", KLEIDUNG + (SCHUHE, ACC), "Nieten", "studded", "nieten", "studded", "studs"),
    _d("detail", KLEIDUNG, "Stickerei", "embroidered", "stickerei", "bestickt", "embroidered",
       "embroidery"),
]

BY_NAME = {detail.de: detail for detail in DETAILS}
assert len(BY_NAME) == len(DETAILS), "Jedes Merkmal braucht einen eigenen deutschen Namen"

PATTERNS = _compile({d.de: list(d.words) for d in DETAILS}, suffix=ADJECTIVE)


def find(text: str, categories) -> set[tuple[str, str]]:
    """Welche Merkmale passen zu welcher Kategorie im Text?
    -> {("Hosen", "Bootcut"), ("Hosen", "Light Wash"), ("Oberteile", "Cropped")}"""
    categories = set(categories)
    if not categories:
        return set()
    return {(category, name) for name in find_terms(text, PATTERNS)
            for category in categories & set(BY_NAME[name].categories)}
