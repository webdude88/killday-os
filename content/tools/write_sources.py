#!/usr/bin/env python3
"""Writes content/sources.json, the hand-curated list the resolver checks.

Keeping the list in code makes the repeated Gutenberg and Stack Exchange
entries one line each. Edit this file, not the generated JSON.
"""
import json
from pathlib import Path

ALL = ["lite", "plus", "standard", "full"]
UP = ["standard", "full"]
# Plus is for 128 GB sticks: Standard without the dictionary or the big map.
PLUS_UP = ["plus", "standard", "full"]
FULL = ["full"]
PD = "Public domain (US government work)"
SA = "CC BY-SA 4.0"
SE = "CC BY-SA 4.0 (Stack Exchange contributors)"


def zim(id_, title, folder, prefix, license_, source, tiers, desc="", disclaimer=None):
    return dict(id=id_, title=title, kind="zim", zim_dir=folder, zim_prefix=prefix, license=license_,
                source=source, tiers=tiers, description=desc, disclaimer=disclaimer)


def pdf(id_, title, url, license_, source, tiers=ALL, desc="", disclaimer=None, require_text=None):
    return dict(id=id_, title=title, kind="pdf", url=url, license=license_, source=source, tiers=tiers,
                description=desc, disclaimer=disclaimer, require_text=require_text)


def book(pg, title, tiers=ALL, desc=""):
    return dict(id=f"pg-{pg}", title=title, kind="html", url=f"https://www.gutenberg.org/cache/epub/{pg}/pg{pg}-images.html",
                license="Public domain in the USA (Project Gutenberg)", source="Project Gutenberg", tiers=tiers,
                description=desc, disclaimer=None, require_text=None)


def openstax(slug, title, tiers=PLUS_UP):
    return dict(id=f"openstax-{slug}", title=title, kind="openstax", slug=slug, source="OpenStax, Rice University",
                tiers=tiers, description="College-level textbook.", disclaimer=None, require_text=None)


def stack(site, title):
    return zim(f"se-{site}", f"Stack Exchange: {title}", "stack_exchange", f"{site}.stackexchange.com_en_all", SE,
               "Stack Exchange via Kiwix", ALL, "Community questions and answers.")


def region(id_, title, bbox, maxzoom, tiers):
    return dict(id=f"map-{id_}", title=title, kind="map", region=id_, bbox=bbox, maxzoom=maxzoom, tiers=tiers,
                license="ODbL 1.0 (OpenStreetMap contributors), tiles by Protomaps", source="OpenStreetMap via Protomaps",
                description=f"Detail to zoom {maxzoom}.", disclaimer=None)


def canning(part, name):
    return pdf(f"usda-canning-{part.lower()}", f"USDA Home Canning: {name}",
               f"https://nchfp.uga.edu/papers/guide/{part}_HomeCan{'' if part == 'INTRO' else '_'}rev0715.pdf",
               PD + ", USDA Bulletin 539", "USDA via National Center for Home Food Preservation")


SOURCES = {
    "disclaimers": {
        "general": "REFERENCE ONLY. This encyclopedia may be incomplete or out of date. It is reference material and not a substitute for professional medical, legal or safety advice.",
        "medical": "REFERENCE ONLY. This is reference material and not a substitute for professional medical care. If someone is seriously hurt or ill, contact emergency services or a qualified clinician if there is any way to do so.",
        "chemical": "REFERENCE ONLY. This is reference material and not a substitute for professional guidance. Chemicals can injure, poison or kill. Follow exact quantities and never mix chemicals unless the guide specifically tells you to.",
        "electrical": "REFERENCE ONLY. This is reference material and not a substitute for a qualified electrician. Electricity can kill. Disconnect power and verify it is off before touching any conductor.",
        "food": "REFERENCE ONLY. This is reference material and not a substitute for professional food-safety guidance. Improper canning can cause fatal botulism. Never eat a wild plant or mushroom unless an expert has positively identified it.",
    },
    "excluded": [
        {"title": "FM 21-76 and FM 3-05.70 US Army Survival manuals", "reason": "Public domain, but both include a chapter on improvised weapons. Excluded under the no-weapons rule."},
        {"title": "TM 31-210 Improvised Munitions Handbook and similar", "reason": "Instructions for building explosives and weapons."},
        {"title": "Kiwix zimgit-* collections (water, medicine, post-disaster, food, knots)", "reason": "Bundles of third-party PDFs whose individual licenses could not be verified."},
        {"title": "Canadian Prepper video ZIMs", "reason": "YouTube content with no clear free license."},
        {"title": "Where There Is No Doctor (Hesperian)", "reason": "Copyrighted with limited permissions. Not confirmed for redistribution here."},
        {"title": "ARRL band plan chart and license manuals", "reason": "Copyrighted by ARRL. FCC Part 97 and the frequency table are used instead."},
    ],
    "modules": [
        dict(id="general", title="General reference", blurb="Encyclopedia, dictionary, how-to books and travel guides.", disclaimer="general", items=[
            zim("wikipedia-mini", "Wikipedia (introductions only)", "wikipedia", "wikipedia_en_all_mini", SA, "Wikipedia via Kiwix", ["lite"], "The opening section of every English article."),
            zim("wikipedia-nopic", "Wikipedia (full text, no images)", "wikipedia", "wikipedia_en_all_nopic", SA, "Wikipedia via Kiwix", ["plus", "standard"], "Every English article, text only."),
            zim("wikipedia-maxi", "Wikipedia (with images)", "wikipedia", "wikipedia_en_all_maxi", SA, "Wikipedia via Kiwix", FULL, "Every English article with images."),
            zim("wiktionary", "Wiktionary", "wiktionary", "wiktionary_en_all_nopic", SA, "Wiktionary via Kiwix", UP, "English dictionary."),
            zim("wikibooks-nopic", "Wikibooks (no images)", "wikibooks", "wikibooks_en_all_nopic", SA, "Wikibooks via Kiwix", ["lite", "plus", "standard"], "Open textbooks and how-to books."),
            zim("wikibooks-maxi", "Wikibooks (with images)", "wikibooks", "wikibooks_en_all_maxi", SA, "Wikibooks via Kiwix", FULL, "Open textbooks and how-to books."),
            zim("wikivoyage-nopic", "Wikivoyage (no images)", "wikivoyage", "wikivoyage_en_all_nopic", SA, "Wikivoyage via Kiwix", ["lite"], "Travel and regional guides."),
            zim("wikivoyage-maxi", "Wikivoyage (with images)", "wikivoyage", "wikivoyage_en_all_maxi", SA, "Wikivoyage via Kiwix", PLUS_UP, "Travel and regional guides."),
        ]),
        dict(id="medical", title="Medical and first aid", blurb="First aid, field medicine and clinical reference.", disclaimer="medical", items=[
            zim("wikimed", "WikiMed medical encyclopedia", "other", "mdwiki_en_all_maxi", SA, "WikiProjectMed / MDWiki via Kiwix", ALL, "Plain-language clinical reference."),
            zim("wikipedia-med-nopic", "Wikipedia: Medicine (no images)", "wikipedia", "wikipedia_en_medicine_nopic", SA, "Wikipedia via Kiwix", ["lite"]),
            zim("wikipedia-med-maxi", "Wikipedia: Medicine (with images)", "wikipedia", "wikipedia_en_medicine_maxi", SA, "Wikipedia via Kiwix", PLUS_UP),
            zim("libretexts-med", "LibreTexts Medicine", "libretexts", "libretexts.org_en_med", "CC BY-NC-SA (varies by page, see each page)", "LibreTexts via Kiwix", PLUS_UP, "Open health-science textbooks."),
            pdf("army-fm-4-25-11", "FM 4-25.11 First Aid (US Army, 2002)", "https://archive.org/download/FM4-25x11/FM4-25x11.pdf", PD, "US Army via Internet Archive", ALL, "Older but complete first aid manual. Check newer guidance when you can.", require_text="public release"),
            pdf("army-atp-4-02-11", "ATP 4-02.11 Casualty Response and First Aid (US Army, 2026)", "https://armypubs.army.mil/epubs/DR_pubs/DR_a/ARN46159-ATP_4-02.11-000-WEB-1.pdf", PD, "US Army Publishing Directorate", ALL, "Current Army first aid doctrine.", require_text="public release"),
        ]),
        dict(id="self-reliance", title="Self-reliance", blurb="Repair guides, appropriate technology, gardening and practical Q&A.", disclaimer="electrical", items=[
            zim("appropedia", "Appropedia", "other", "appropedia_en_all_maxi", SA, "Appropedia via Kiwix", ALL, "Appropriate technology and sustainable living."),
            zim("ifixit", "iFixit repair guides", "ifixit", "ifixit_en_all", "CC BY-NC-SA 3.0", "iFixit via Kiwix", ALL, "Step-by-step repair for phones, computers and appliances."),
            stack("diy", "Home improvement"), stack("gardening", "Gardening and landscaping"), stack("cooking", "Cooking"), stack("electronics", "Electronics"), stack("ham", "Amateur radio"),
            zim("se-sustainability", "Stack Exchange: Sustainability", "stack_exchange", "sustainability.stackexchange.com_en_all", SE, "Stack Exchange via Kiwix", PLUS_UP, "Community questions and answers."),
        ]),
        dict(id="food", title="Food", blurb="Canning, preservation, cooking and wild food references.", disclaimer="food", items=[
            canning("INTRO", "Introduction"), canning("GUIDE01", "Principles of canning"), canning("GUIDE02", "Fruit"), canning("GUIDE03", "Tomatoes"),
            canning("GUIDE04", "Vegetables"), canning("GUIDE05", "Meat and seafood"), canning("GUIDE06", "Fermented food and pickles"), canning("GUIDE07", "Jams and jellies"),
            pdf("usfs-gtr-513", "Forest Service GTR-513: Northwest forest plants and fungi", "https://www.fs.usda.gov/pnw/pubs/pnw_gtr513.pdf", PD, "USDA Forest Service", ALL, "Species reference, not a foraging field guide. It does not replace expert identification."),
        ]),
        dict(id="water", title="Water and sanitation", blurb="Making water safe and keeping sanitation from making people sick.", disclaimer="chemical", items=[
            pdf("epa-emergency-disinfection", "EPA: Emergency Disinfection of Drinking Water", "https://www.epa.gov/sites/default/files/2017-09/documents/emergency_disinfection_of_drinking_water_sept2017.pdf", PD, "US EPA"),
            pdf("army-fm-21-10", "FM 21-10 Field Hygiene and Sanitation (US Army, 2000)", "https://archive.org/download/FM21-10_2000/FM21-10_2000.pdf", PD, "US Army via Internet Archive", ALL, "Latrines, waste and water discipline for groups in the field.", require_text="public release"),
            pdf("who-gdwq", "WHO: Guidelines for Drinking-water Quality (4th ed.)", "https://iris.who.int/bitstream/handle/10665/254637/9789241549950-eng.pdf", "CC BY-NC-SA 3.0 IGO", "World Health Organization", UP),
        ]),
        dict(id="shelter", title="Shelter, energy and repair", blurb="Preparedness, safe shelter and working safely with power.", disclaimer="electrical", items=[
            pdf("fema-are-you-ready", "FEMA: Are You Ready? Citizen Preparedness Guide", "https://www.ready.gov/sites/default/files/2021-11/are-you-ready-guide.pdf", PD, "FEMA / Ready.gov", ALL, disclaimer="general"),
            pdf("osha-3075", "OSHA 3075: Controlling Electrical Hazards", "https://www.osha.gov/sites/default/files/publications/osha3075.pdf", PD, "US Department of Labor, OSHA"),
        ]),
        dict(id="comms", title="Communications and navigation", blurb="Ham radio licensing, frequency allocations and land navigation.", disclaimer=None, items=[
            pdf("ncvec-technician", "FCC Technician exam question pool 2026-2030", "https://ncvec.org/downloads/2026-2030 Technician Pool and Syllabus Public Release Feb 19 2026.pdf", "Public domain (released by NCVEC QPC)", "NCVEC Question Pool Committee"),
            pdf("cfr-part-97", "47 CFR Part 97: Amateur Radio Service rules", "https://www.govinfo.gov/content/pkg/CFR-2024-title47-vol5/pdf/CFR-2024-title47-vol5-part97.pdf", PD, "US Government Publishing Office"),
            pdf("fcc-allocations", "FCC Table of Frequency Allocations", "https://transition.fcc.gov/oet/spectrum/table/fcctable.pdf", PD, "Federal Communications Commission"),
            pdf("usgs-map-symbols", "USGS Topographic Map Symbols", "https://pubs.usgs.gov/gip/TopographicMapSymbols/topomapsymbols.pdf", PD, "US Geological Survey"),
            pdf("army-fm-3-25-26", "FM 3-25.26 Map Reading and Land Navigation (US Army)", "https://archive.org/download/FM3-25x26/FM3-25x26.pdf", PD, "US Army via Internet Archive", ALL, "Map, compass and terrain navigation.", require_text="public release"),
        ]),
        dict(id="education", title="Education", blurb="Textbooks, classic literature and books for children.", disclaimer=None, items=[
            zim("khan-academy", "Khan Academy (videos)", "other", "khanacademy_en_all", "CC BY-NC-SA 3.0", "Khan Academy via Kiwix", FULL, "Maths and science lessons from a 2023 snapshot."),
            openstax("biology-2e", "OpenStax Biology 2e"), openstax("chemistry-2e", "OpenStax Chemistry 2e"),
            openstax("college-physics-2e", "OpenStax College Physics 2e"), openstax("anatomy-and-physiology-2e", "OpenStax Anatomy and Physiology 2e"),
            openstax("prealgebra-2e", "OpenStax Prealgebra 2e"), openstax("algebra-and-trigonometry-2e", "OpenStax Algebra and Trigonometry 2e"),
            book(84, "Frankenstein"), book(1342, "Pride and Prejudice"), book(2701, "Moby Dick"), book(1661, "The Adventures of Sherlock Holmes"), book(521, "Robinson Crusoe"), book(205, "Walden"), book(1228, "On the Origin of Species"),
            book(11, "Alice's Adventures in Wonderland", desc="For children."), book(120, "Treasure Island", desc="For children."), book(2591, "Grimms' Fairy Tales", desc="For children."), book(16, "Peter Pan", desc="For children."), book(55, "The Wonderful Wizard of Oz", desc="For children."), book(11339, "Aesop's Fables", desc="For children."),
        ]),
        dict(id="maps", title="Maps", blurb="Offline OpenStreetMap regions. Add more with the map script.", disclaimer=None, items=[
            region("world-overview", "World overview", [-180, -85, 180, 85], 6, ALL),
            region("usa-lower-48", "United States, lower 48", [-125.0, 24.4, -66.9, 49.5], 12, ALL),
            region("north-america", "North America, street level", [-170, 7, -50, 84], 15, UP),
            {**region("planet", "Whole planet, street level", [-180, -85, 180, 85], 15, FULL), "whole_planet": True},
        ]),
        dict(id="ai", title="Local AI assistant", blurb="Small offline chat model. It makes mistakes. Never rely on it for medical or safety decisions.", disclaimer="medical", items=[
            dict(id="ai-phi35", title="Phi-3.5 Mini model (Q4)", kind="file", path="ai/Phi-3.5-mini-instruct-Q4_K_M.gguf",
                 url="https://huggingface.co/bartowski/Phi-3.5-mini-instruct-GGUF/resolve/main/Phi-3.5-mini-instruct-Q4_K_M.gguf",
                 license="MIT (Microsoft)", source="Microsoft via Hugging Face", tiers=PLUS_UP, optional=True,
                 description="Runs on CPU. UNRELIABLE for medical or safety-critical decisions.", disclaimer=None),
        ]),
    ],
    "tools": [
        dict(id="kiwix-windows", title="Portable Kiwix for Windows", url="https://ftp.fau.de/kiwix/release/kiwix-tools/kiwix-tools_win-x86_64-3.8.1.zip", platform="windows-amd64", license="GPL-3.0"),
        dict(id="kiwix-macos-arm64", title="Portable Kiwix for Apple Silicon", url="https://ftp.fau.de/kiwix/release/kiwix-tools/kiwix-tools_macos-arm64-3.8.1.tar.gz", platform="darwin-arm64", license="GPL-3.0"),
        dict(id="kiwix-macos-x64", title="Portable Kiwix for Intel Macs", url="https://ftp.fau.de/kiwix/release/kiwix-tools/kiwix-tools_macos-x86_64-3.8.1.tar.gz", platform="darwin-amd64", license="GPL-3.0"),
        dict(id="kiwix-linux", title="Portable Kiwix for Linux", url="https://ftp.fau.de/kiwix/release/kiwix-tools/kiwix-tools_linux-x86_64-musl-3.8.1.tar.gz", platform="linux-amd64", license="GPL-3.0"),
        dict(id="llama-linux", title="llama.cpp CPU runtime", url="https://github.com/ggml-org/llama.cpp/releases/download/b12211/llama-b12211-bin-ubuntu-x64.tar.gz", platform="linux-amd64-ai", license="MIT", optional=True),
        dict(id="pmtiles-linux", title="pmtiles extractor", url="https://github.com/protomaps/go-pmtiles/releases/download/v1.31.2/go-pmtiles_1.31.2_Linux_x86_64.tar.gz", platform="build", license="BSD-3-Clause"),
    ],
}

Path(__file__).resolve().parents[1].joinpath("sources.json").write_text(json.dumps(SOURCES, indent=1) + "\n")
