import pytest

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

