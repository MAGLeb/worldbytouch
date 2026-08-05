#!/usr/bin/env python3
"""
Country names for the map labels and legends, keyed by ISO3.

Keyed by the geoBoundaries `source_file` column (the ISO3 code the polygon was
downloaded under) — NOT by `shapeName`, which is unreliable in the merged file
(Italy comes through as "Nord-Ovest", Azerbaijan as "Contiguous Azerbaijan").

Only countries listed here can receive a number: a label is worthless without a
legend entry, and inventing Serbian names we cannot verify is worse than
leaving a country unlabelled. The Serbian column is the author's own curated
list, carried over verbatim from the previous capital-keyed table.
"""

# ISO3 -> (English name, Serbian ekavian name)
COUNTRIES = {
    "RUS": ("Russia", "Rusija"),
    "TUR": ("Turkey", "Turska"),
    "IRN": ("Iran", "Iran"),
    "SAU": ("Saudi Arabia", "Saudijska Arabija"),
    "EGY": ("Egypt", "Egipat"),
    "DZA": ("Algeria", "Alžir"),
    "UKR": ("Ukraine", "Ukrajina"),
    "POL": ("Poland", "Poljska"),
    "ROU": ("Romania", "Rumunija"),
    "IRQ": ("Iraq", "Irak"),
    "AFG": ("Afghanistan", "Avganistan"),
    "LBY": ("Libya", "Libija"),
    "TUN": ("Tunisia", "Tunis"),
    "SYR": ("Syria", "Sirija"),
    "JOR": ("Jordan", "Jordan"),
    "AZE": ("Azerbaijan", "Azerbejdžan"),
    "GEO": ("Georgia", "Gruzija"),
    "ARM": ("Armenia", "Jermenija"),
    "GRC": ("Greece", "Grčka"),
    "BGR": ("Bulgaria", "Bugarska"),
    "SRB": ("Serbia", "Srbija"),
    "HUN": ("Hungary", "Mađarska"),
    "AUT": ("Austria", "Austrija"),
    "ITA": ("Italy", "Italija"),
    "DEU": ("Germany", "Nemačka"),
    "BLR": ("Belarus", "Belorusija"),
    "SDN": ("Sudan", "Sudan"),
    "YEM": ("Yemen", "Jemen"),
    "OMN": ("Oman", "Oman"),
    "ARE": ("Emirates", "Emirati"),
    "QAT": ("Qatar", "Katar"),
    "KWT": ("Kuwait", "Kuvajt"),
    "BHR": ("Bahrain", "Bahrein"),
    "LBN": ("Lebanon", "Liban"),
    "ISR": ("Israel", "Izrael"),
    "CYP": ("Cyprus", "Kipar"),
    "ALB": ("Albania", "Albanija"),
    "MKD": ("Macedonia", "Makedonija"),
    "MNE": ("Montenegro", "Crna Gora"),
    "BIH": ("Bosnia", "Bosna"),
    "HRV": ("Croatia", "Hrvatska"),
    "SVN": ("Slovenia", "Slovenija"),
    "SVK": ("Slovakia", "Slovačka"),
    "CZE": ("Czechia", "Češka"),
}

# Deliberately absent: MAR (Morocco) lies west of the 5°E map edge and is not
# on this map at all — the old capital list carried it with a sign-flipped
# longitude (+6.85 instead of −6.85), which dropped the label inside ALGERIA
# and labelled Algeria "Rabat / Maroko". Fixed 2026-08-05 by keying on the
# country polygon instead of a capital coordinate.


def name_en(iso):
    e = COUNTRIES.get(iso)
    return e[0] if e else None


def name_sr(iso):
    e = COUNTRIES.get(iso)
    return e[1] if e else None
