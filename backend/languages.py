"""Weitere Sprachen für die Wortsuche: Polnisch, Niederländisch, Französisch, Italienisch, Spanisch.

Shops aus anderen Ländern (AliExpress PL, Direct-Running NL …) schreiben ihre Produktnamen
in ihrer Sprache. matching.py hängt diese Wörter an die deutschen/englischen an – dieselben
festen Begriffe ("schwarz", "Hosen"), damit alles andere gleich bleibt.

Schreibweise wie in matching.py, plus:
  "~" am Ende = beliebige Endung ("czarn~" -> czarny, czarna, czarne – polnische Endungen)
Bewusst NICHT dabei: Wörter, die auf Deutsch/Englisch etwas anderes heißen
("but" = polnisch Schuhe, "pull" = französisch Pullover, "plaid", "bord", "collar" …).
"""

COLORS = {
    "beige": ["beżow~", "kremow~", "crème", "crema"],
    "weiß": ["biał~", "biel~", "wit", "witte", "blanc", "blanche~", "bianc~", "blanco", "blanca"],
    "schwarz": ["czarn~", "zwart~", "noir~", "nero", "nera", "neri", "nere", "negro", "negra"],
    "grau": ["szar~", "grijs", "grijze", "gris", "grise~", "grigi~"],
    "braun": ["brązow~", "bruin~", "marron", "brun~", "marrone", "marrón"],
    "blau": ["niebiesk~", "granatow~", "blauw~", "bleu~", "blu", "azzurr~", "azul~"],
    "grün": ["zielon~", "groen~", "vert", "verte", "verts", "vertes", "verde", "verdi"],
    "oliv": ["oliwkow~", "olijf~", "olive~", "oliva"],
    "rosa": ["różow~", "roze", "rosado", "rosada"],
    "rot": ["czerwon~", "bordow~", "rood", "rode", "rouge~", "rosso", "rossa", "rossi", "rosse",
            "rojo", "roja"],
    "orange": ["pomarańczow~", "oranje", "arancion~", "naranja"],
    "gelb": ["żółt~", "geel", "gele", "jaune~", "giall~", "amarill~"],
    "silber": ["srebrn~", "zilver~", "argenté~", "argentat~", "plateado", "plateada"],
    "gold": ["złot~", "goud~", "doré~", "dorat~", "oro", "dorado", "dorada"],
}

STYLES = {
    "sportlich": ["sportow~", "sportief", "sportiv~", "deportiv~"],
    "elegant": ["eleganck~", "elegante", "élégant~"],
    "klassisch": ["klasyczn~", "klassiek~", "classique~", "classic~", "clásic~"],
    "minimalistisch": ["minimalistyczn~", "minimalistisch"],
    "skandinavisch": ["skandynawsk~", "scandinavisch~", "scandinave~", "scandinav~"],
    "casual": ["codzienn~", "décontracté~"],
}

CATEGORIES = {
    "Oberteile": ["koszul~", "koszulk~", "bluzk~", "bluza", "bluzy", "sweter~", "swetr~",
                  "trui", "truien", "overhemd~", "chemise~", "chemisier~", "maglion~",
                  "magliett~", "camicia", "camicie", "camicett~", "felpa", "felpe", "camiseta~",
                  "camisa~", "sudadera~", "blusa~"],
    "Hosen": ["spodni~", "spodenki", "dżins~", "jeansy", "legginsy", "szorty", "broek~",
              "spijkerbroek~", "pantalon~", "pantaloni", "pantaloncini", "pantalones",
              "vaqueros"],
    "Jacken": ["kurtk~", "płaszcz~", "marynark~", "kamizelk~", "jas", "jassen", "veste~",
               "manteau~", "blouson~", "giacc~", "giubbott~", "cappott~", "chaqueta~",
               "abrigo~", "cazadora~", "chaleco~"],
    "Kleider & Röcke": ["sukienk~", "spódnic~", "kombinezon~", "jurk~", "rok", "rokken",
                        "jupe~", "vestito", "vestiti", "abito", "abiti", "gonna", "gonne",
                        "vestido~", "falda~"],
    "Schuhe": ["buty", "butów", "trampk~", "sneakersy", "kozak~", "botk~", "sandał~", "klapk~",
               "szpilk~", "mokasyn~", "baleriny", "schoen~", "laarz~", "chaussure~",
               "bottes", "bottines", "baskets", "escarpins", "scarpe", "scarpa", "stival~",
               "sandali", "zapato~", "zapatilla~", "botas", "botines", "sandalias"],
    "Accessoires": ["torb~", "torebk~", "plecak~", "pasek", "paski", "naszyjnik~", "kolczyk~",
                    "bransolet~", "czapk~", "szalik~", "okulary", "biżuteri~", "handtas~",
                    "riem~", "sjaal~", "ketting~", "oorbel~", "rugzak~", "sac", "sacs",
                    "ceinture~", "écharpe~", "collier~", "lunettes", "bijou~", "chapeau~",
                    "borsa", "borse", "borsett~", "cintur~", "sciarp~", "collana~",
                    "orecchin~", "occhiali", "zaino", "cappello", "bolso~", "cinturón",
                    "bufanda~", "pendientes", "gafas", "mochila~", "gorro~", "gorra~"],
    "Deko": ["wazon~", "świec~", "dekoracj~", "vaas", "vazen", "kaars~", "decoratie~",
             "bougie~", "vaso", "vasi", "candel~", "decorazion~", "jarrón~", "vela", "velas",
             "decoración"],
    "Leuchten": ["lampa", "lampy", "lampk~", "kinkiet~", "żyrandol~", "lampada~", "lámpara~"],
    "Textilien": ["poduszk~", "koc", "koce", "narzut~", "dywan~", "zasłon~", "pościel~",
                  "kussen~", "deken~", "vloerkleed~", "gordijn~", "beddengoed", "coussin~",
                  "couverture~", "tapis", "rideau~", "cuscin~", "copert~", "tappet~", "cojín",
                  "cojines", "manta", "mantas", "alfombra~", "cortina~"],
    "Küche & Tisch": ["kubek", "kubki", "talerz~", "filiżank~", "mok", "mokken", "servies",
                      "assiette~", "vaisselle", "tazza", "tazze", "piatt~", "taza", "tazas",
                      "plato", "platos", "vajilla"],
    "Möbel": ["krzesł~", "krzesel", "stół", "stoł~", "stolik~", "regał~", "półk~", "komod~",
              "kanap~", "fotel~", "stoel~", "kast", "kasten", "fauteuil~", "chaise~",
              "étagère~", "armoire~", "canapé~", "sedia", "sedie", "tavol~", "mensol~",
              "divano~", "poltron~", "silla~", "mesa", "mesas", "estanter~", "sillón"],
    "Pflanzen & Töpfe": ["doniczk~", "plantenpot~", "bloempot~", "cache-pot", "maceta~"],
    "Wandgestaltung": ["lustr~", "obraz~", "plakat~", "ramk~", "schilderij~", "miroir~",
                       "cadre~", "affiche~", "specchi~", "quadro", "quadri", "espejo~",
                       "cuadro~", "lámina~"],
}
