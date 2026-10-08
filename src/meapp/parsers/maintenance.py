import re
from datetime import date, datetime


from bs4 import SoupStrainer, BeautifulSoup, Tag
from word2number import w2n
from dateparser import search
from rapidfuzz import process, fuzz


from meapp.models import MaintenanceReport


def remove_redundant_html(soup: BeautifulSoup):
    # this is to remove the attributes from the document and remove empty tags
    
    for tag in reversed(soup.find_all(True)):
        if not tag.contents:
            tag.decompose()  # Completely removes the tag from the tree
        tag.attrs = {}

    
def get_first_date_row(soup: BeautifulSoup) -> list[str] | None:
    """Will find and extract the date if it appears in a tr tag before the main table content. Returns a list of strings ["date:", ACTUAL DATE, "shift", ACTUAL SHIFT]"""
    DATE_WORD = re.compile(r"\bdate\b", re.I)

    for text_node in soup.find_all(string=DATE_WORD):
        row = text_node.find_parent("tr")
        if row:
            return list(row.stripped_strings)
        
    return None


def extract_date_from_text(text: str) -> tuple[date | None, int | None]:
    text = text.lower().replace("today", "")
    # Correct type hint: search_dates returns a list of tuples, or None
    results: list[tuple[str, datetime]] | None = search.search_dates(text, languages=['en'])
    
    if results:
        # results[0] is the first match tuple: ('January 12, 2024', datetime_obj)
        # results[0][1] gets the datetime object
        matched_str, dt_obj = results[0]
        
        # Returning a 2-tuple matching your type annotation
        return dt_obj.date(), text.find(matched_str)

    return None, None

def get_date_and_shift(
    soup: BeautifulSoup, 
    mail_date: date
    ) -> tuple[None | date, None | str]:

    """
    Parses a BeautifulSoup object to extract a shift date and shift name.
    Return None, None if not found.
    """

    row = get_first_date_row(soup)

    if isinstance(row, list):
        # it should be the second object in the row
        try:
            shift: str | None = row[3].lower()
        except IndexError:
        
            shift = None
        
        try:
            report_date: str = row[1]

        except IndexError:
            return None, None
                
        
        parts = re.findall(r"\d+", report_date)

        if len(parts) != 3:
            return None, None

        if len(parts[0]) == 4:  # year first, e.g. 2024-03-15
            year, first, second = (int(p) for p in parts)
            readings = ((second, first), (first, second))  # (day, month), yyyy-mm-dd first
        else:  # year last, e.g. 05/03/2024
            first, second, year = (int(p) for p in parts)
            readings = ((first, second), (second, first))  # (day, month), dd/mm first

        if year < 100:  # two-digit year
            year += 2000

        candidates: list[date] = []
        for day, month in readings:
            try:
                d = date(year, month, day)
            except ValueError:
                continue
            if d not in candidates:
                candidates.append(d)

        if not candidates:
            return None, None

        return min(candidates, key=lambda d: abs(d - mail_date)), shift

    return (None, None)

    
def get_text_not_in_table(soup: BeautifulSoup) -> str:
    for table in soup.find_all("table"):
        table.decompose()

    texts = " ".join(t.strip() for t in soup.stripped_strings)

    return texts


def extract_other_data(text: str) -> dict:
    """Return switchovers, generator, run_minutes, run_hours, load_kw, diesel_litres.
    Each value is (value, flag): flag 0 = found, flag 1 = not found (default used),
    flag 2 = found but unit assumed (load written as "w" instead of "kw")."""

    text = re.sub(r"fuel\s+of", "", text, flags=re.I)

    NUM = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"   # 700, 1,200, 8.5
    WORDS = {
        "zero": 0, "none": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4,
        "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, 
        "twelve": 12, "thirteen": 13, "fourteen":14, "fifteen": 15, "sixteen": 16,
        "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
        }
    VOCAB = ["switchover", "switchovers", "generator", "consumed", "diesel",
             "litres", "liters", "minutes"]
    SEP = r"(?:&|and|,|/|\+|plus)"
    GEN_LIST = re.compile(
        r"((?:\d[\d,]*(?:\.\d+)?\s*kva\s*(?:" + SEP + r"\s*)?)+)generators?\b", re.I)

    def to_num(s: str) -> float:
        return float(s.replace(",", ""))

    def fix_word(m: re.Match) -> str:
        word, low = m.group(0), m.group(0).lower()
        if process is None or len(low) < 6 or low in VOCAB:
            return word
        cutoff = 85 if len(low) >= 8 else 80
        hit = process.extractOne(low, VOCAB, scorer=fuzz.ratio, score_cutoff=cutoff)
        return hit[0] if hit else word

    t = re.sub(r"https?://\S+", " ", text)      # URLs contain digits; remove first
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"[A-Za-z]+", fix_word, t)       # correct typos in keywords

    out = {
        "switchovers": (0, 1),
        "generator": (" KVA", 1),
        "run_minutes": (0, 1),
        "run_hours": (0, 1),
        "load_kw": (0, 1),
        "diesel_litres": (0, 1),
    }

    # 1) number of switchovers (digit or word, e.g. "is THREE")
    m = re.search(r"switch\s*-?\s*overs?\b[^.]*?\bis\s+(\w+)", t, re.I)
    if m:
        tok = m.group(1).lower()
        out["switchovers"] = (int(tok) if tok.isdigit() else WORDS.get(tok), 0)

    # 2) generator type(s): every KVA rating in a list that ends in "generator(s)"
    found = []
    for m in GEN_LIST.finditer(t):
        for n in re.findall(NUM + r"\s*kva", m.group(1), re.I):
            if n not in found:
                found.append(n)
    if not found:                                   # fallback: first KVA mention anywhere
        m = re.search(NUM + r"\s*kva", t, re.I)
        if m:
            found.append(m.group(1))
    if found:
        out["generator"] = (" & ".join(f"{n} KVA" for n in found), 0)

    # 3) run time: hours and/or minutes; run / runs / running / ran; "for" optional
    run_re = re.compile(
        r"\b(?:run|runs|running|ran)\b\s*(?:for\s*)?(?=\d)"
        r"(?:" + NUM + r"\s*(?:hours?|hrs?|h)\b)?"
        r"\s*,?\s*(?:and\s*)?"
        r"(?:" + NUM + r"\s*(?:minutes?|mins?|m)\b)?",
        re.I)
    for m in run_re.finditer(t):
        if m.group(1) or m.group(2):            # skip empty matches like "run for 5 days"
            hours = to_num(m.group(1)) if m.group(1) else 0
            minutes = to_num(m.group(2)) if m.group(2) else 0
            out["run_minutes"] = ((hours * 60) + minutes, 0)
            out["run_hours"] = (hours + (minutes / 60), 0)
            break

    # 4) load in kW (also accepts a bare "w"; flag 2 = unit assumed)
    m = re.search(r"\bload\s*(?:of|is|:)?\s*" + NUM + r"\s*(k?)w\b", t, re.I)
    if m:
        out["load_kw"] = (to_num(m.group(1)), 0)
        if not m.group(2):                      # sender wrote "w", not "kw"
            out["load_kw"] = (out["load_kw"][0], 2)

    # 5) litres consumed (anchored on "consumed" so the forklift's litres are ignored)
    m = re.search(
        r"\bconsum\w*\s*(?:(?:of\s+)?(?:fuel|diesel)\s*)?(?:of\s*)?" + NUM +
        r"\s*(?:(?:of\s+)?(?:fuel|diesel)\s*(?:of\s*)?)?"
        r"(?:litres?|liters?|ltrs?|l)\b",
        t, re.I)
    if m:
        out["diesel_litres"] = (to_num(m.group(1)), 0)

    # 6) generator didn't run: zero switchovers and nothing reported about run/load/litres
    sw, sw_flag = out["switchovers"]
    if sw == 0 and sw_flag == 0 and all(out[k][1] == 1 for k in ("run_minutes", "load_kw", "diesel_litres")):
        for k in ("run_minutes", "run_hours", "load_kw", "diesel_litres"):
            out[k] = (0, 0)

    return out



def maintenance_parser(mail_content, mail_date):
    soup = BeautifulSoup(mail_content, "lxml")
    remove_redundant_html(soup)

    report_date = (mail_date, 1)
    shift = ("day", 1)
    # error code of 0 means no issue
    # error code of 1 means there is an issue, so mark cell in red

    date, shift = get_date_and_shift(soup, mail_date)
    text_outside_table = get_text_not_in_table(soup)

    if date:
        if date == mail_date:
            report_date = (date, 0)
            shift = (shift, 0)
        else:
            report_date = (date, 1)
            shift = (shift, 0)
    else:
        date, index = extract_date_from_text(text_outside_table)

        if date:
            if date == mail_date:
                report_date = (date, 0)
                shift = ("Day", 0)

    other_data = extract_other_data(text_outside_table)

    return MaintenanceReport(
        report_date = report_date,
        shift = shift,
        switch_overs = other_data["switchovers"],
        generator = other_data["generator"],
        running_time_hr = other_data["run_hours"],
        running_time_mins = other_data["run_minutes"],
        avg_load = other_data["load_kw"],
        volume_of_diesel = other_data["diesel_litres"]
    )
