from app.services.image_utils import extract_multimedia_blocks


def test_extract_multimedia_blocks_empty_input():
    assert extract_multimedia_blocks({}) == []
    assert extract_multimedia_blocks([]) == []
    assert extract_multimedia_blocks(None) == []


def test_extract_multimedia_blocks_no_multimedia_key():
    outline = {
        "Introduction": {
            "Content": "Some text",
        }
    }
    assert extract_multimedia_blocks(outline) == []


def test_extract_multimedia_blocks_two_blocks_example():
    outline = {
        "Introduction": {
            "Content": "Vulkan Vegas est une plateforme...",
            "MULTIMEDIA": {
                "Type": "Tableau récapitulatif",
                "Description": "Tableau HTML présentant : Licence, Nombre de jeux...",
                "Purpose": "Offrir une vision immédiate des points forts.",
                "Markup": "<table>, <thead>, <tbody>",
            },
        },
        "Login_Section": {
            "Content": "Pour accéder à votre espace personnel...",
            "MULTIMEDIA": {
                "Type": "Schéma de processus",
                "Description": "Infographie simple montrant les 3 étapes...",
                "Purpose": "Guider visuellement l'utilisateur.",
                "Markup": "<figure> avec <figcaption>",
            },
        },
    }

    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 2

    assert blocks[0]["id"] == "img_1"
    assert blocks[0]["section"] == "Introduction"
    assert blocks[0]["section_content"].startswith("Vulkan Vegas est une plateforme")
    assert blocks[0]["multimedia"]["Type"] == "Tableau récapitulatif"

    assert blocks[1]["id"] == "img_2"
    assert blocks[1]["section"] == "Login_Section"
    assert blocks[1]["section_content"].startswith("Pour accéder à votre espace personnel")
    assert blocks[1]["multimedia"]["Type"] == "Schéma de processus"


def test_extract_multimedia_blocks_nested_structures():
    outline = {
        "SectionA": {
            "Content": "A root content",
            "Child": {
                "Content": "Child content that will be used as section_content",
                "MULTIMEDIA": {
                    "Type": "Infographic",
                    "Description": "Desc",
                    "Purpose": "Purpose",
                    "Markup": "<figure>",
                },
            },
        }
    }

    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert blocks[0]["id"] == "img_1"
    # parent_key becomes the key name of the dict containing MULTIMEDIA ("Child")
    assert blocks[0]["section"] == "Child"
    assert blocks[0]["section_content"] == "Child content that will be used as section_content"
    assert blocks[0]["multimedia"]["Type"] == "Infographic"


def test_extract_multimedia_blocks_numbered_keys():
    outline = {
        "H2_1": "Connexion et Inscription",
        "MULTIMEDIA_1": {
            "Type": "Bouton d'action (CTA)",
            "Description": "Bouton contraste 'Se connecter'",
            "Purpose": "Repondre a l'intent de navigation",
        },
        "MULTIMEDIA_2": {
            "Type": "Tableau HTML",
            "Description": "Tableau comparatif des paliers de bonus",
            "Purpose": "Structurer les donnees chiffrees",
        },
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 2
    assert blocks[0]["multimedia"]["Type"] == "Bouton d'action (CTA)"
    assert blocks[1]["multimedia"]["Type"] == "Tableau HTML"


def test_extract_multimedia_blocks_lowercase_key():
    outline = {
        "Intro": {
            "content": "Lowercase multimedia key example",
            "multimedia": {
                "Type": "Image",
                "Description": "Simple test image",
                "Purpose": "Validate lowercase key support",
            },
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert blocks[0]["section"] == "Intro"
    assert blocks[0]["multimedia"]["Type"] == "Image"


def test_extract_multimedia_blocks_empty_type_defaults_to_image():
    outline = {
        "Section": {
            "Content": "Body text",
            "MULTIMEDIA": {
                "Description": "Hero visual without explicit type",
                "Purpose": "Illustrate section",
            },
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert blocks[0]["multimedia"]["Type"] == "Image"


def test_extract_multimedia_russian_key():
    """Russian МУЛЬТИМЕДИА key as dict."""
    outline = {
        "Section": {
            "Content": "Текст секции",
            "МУЛЬТИМЕДИА": {
                "Type": "Image",
                "Description": "Абстрактная визуализация бонусов",
                "Purpose": "Иллюстрация к секции",
            },
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert "бонусов" in blocks[0]["multimedia"]["Description"]


def test_extract_multimedia_russian_key_as_string():
    """Russian МУЛЬТИМЕДИА key with string value."""
    outline = {
        "Section": {
            "Content": "Текст",
            "МУЛЬТИМЕДИА": "Инфографика — пошаговая схема регистрации на сайте",
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert blocks[0]["multimedia"]["Type"] == "Infographic"
    assert "регистрации" in blocks[0]["multimedia"]["Description"]


def test_extract_multimedia_french_key():
    """French MULTIMÉDIA key."""
    outline = {
        "Section": {
            "Content": "Texte",
            "MULTIMÉDIA": {
                "Type": "Infographie",
                "Description": "Schéma des étapes d'inscription",
            },
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_russian_text_in_content():
    """Russian МУЛЬТИМЕДИА embedded in Content text."""
    outline = {
        "H2": "Бонусы",
        "Content": "Описание бонусов. [МУЛЬТИМЕДИА: Инфографика — сравнение бонусных программ] Продолжение текста.",
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert "бонусных" in blocks[0]["multimedia"]["Description"]


def test_extract_multimedia_french_text_in_content():
    """French [MULTIMÉDIA: ...] in Content."""
    outline = {
        "H2": "Inscription",
        "Content": "Processus d'inscription. [MULTIMÉDIA: Infographie montrant les 3 étapes] Suite.",
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_string_value():
    """MULTIMEDIA key exists but value is a string, not dict."""
    outline = {
        "H2": "Bonus Section",
        "Content": "Text about bonuses",
        "MULTIMEDIA": "Infographic showing bonus tiers with percentages and icons",
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert blocks[0]["multimedia"]["Type"] == "Infographic"


def test_extract_multimedia_from_content_brackets():
    """MULTIMEDIA embedded in Content as [MULTIMEDIA: ...]."""
    outline = {
        "H2": "Login",
        "Content": "Steps. [MULTIMEDIA: Infographic — step-by-step visual showing 3 login steps] More.",
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_image_description_key():
    """Alternative key: image_description."""
    outline = {
        "H2": "Games",
        "Content": "About games",
        "image_description": "Hero visual of slot machine reels with glowing symbols",
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1
    assert "slot machine" in blocks[0]["multimedia"]["Description"].lower()


def test_extract_multimedia_изображение_key():
    """Russian key 'изображение'."""
    outline = {
        "Section": {
            "Content": "Текст",
            "изображение": "Абстрактный щит безопасности с неоновыми акцентами",
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 1


def test_extract_multimedia_mixed_languages():
    """Mix of English dict and Russian text MULTIMEDIA."""
    outline = {
        "Section1": {
            "Content": "English text",
            "MULTIMEDIA": {
                "Type": "Image",
                "Description": "Proper dict image",
            },
        },
        "Section2": {
            "Content": "Русский текст [МУЛЬТИМЕДИА: Картинка — визуализация процесса оплаты]",
        },
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 2


def test_extract_multimedia_list_value():
    """MULTIMEDIA as list of dicts."""
    outline = {
        "Section": {
            "Content": "Text",
            "MULTIMEDIA": [
                {"Type": "Image", "Description": "First image"},
                {"Type": "Infographic", "Description": "Second infographic"},
            ],
        }
    }
    blocks = extract_multimedia_blocks(outline)
    assert len(blocks) == 2
