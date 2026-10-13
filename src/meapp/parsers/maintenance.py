import re
from datetime import date, datetime
from typing import TypedDict

from bs4 import BeautifulSoup
from dateparser import search
from rapidfuzz import fuzz, process

from meapp.exceptions import ParsingError
from meapp.models import MaintenanceReport


class ExtractedMaintenanceData(TypedDict):
    switchovers: tuple[int, int]
    generator: tuple[str, int]
    run_minutes: tuple[float, int]
    run_hours: tuple[float, int]
    load_kw: tuple[float, int]
    diesel_litres: tuple[float, int]


def remove_redundant_html(soup: BeautifulSoup) -> None:
    """Remove empty HTML tags and tag attributes."""
    for tag in reversed(soup.find_all(True)):
        if not tag.contents:
            tag.decompose()
        tag.attrs = {}


def get_first_date_row(soup: BeautifulSoup) -> list[str] | None:
    """Return the first table row containing the word 'date'."""
    date_word = re.compile(r"\bdate\b", re.IGNORECASE)

    for text_node in soup.find_all(string=date_word):
        row = text_node.find_parent("tr")
        if row:
            return list(row.stripped_strings)

    return None


def extract_date_from_text(text: str) -> tuple[date | None, int | None]:
    """Find the first date in text and return it with its character position."""
    normalized_text = text.lower().replace("today", "")
    results: list[tuple[str, datetime]] | None = search.search_dates(
        normalized_text,
        languages=["en"],
    )

    if results:
        matched_text, matched_datetime = results[0]
        return matched_datetime.date(), normalized_text.find(matched_text)

    return None, None


def get_text_not_in_table(soup: BeautifulSoup) -> str:
    """Remove tables from the soup and return the remaining text."""
    for table in soup.find_all("table"):
        table.decompose()

    return " ".join(text.strip() for text in soup.stripped_strings)


def get_date_and_shift(
    soup: BeautifulSoup,
    mail_date: date,
) -> tuple[tuple[date, int], tuple[str, int]]:
    """Return report date and shift as (value, flag) pairs.

    Flag 0 means the value was found and accepted.
    Flag 1 means a fallback value was used or the table date differed
    from mail_date.
    """
    default_date = (mail_date, 1)
    default_shift = ("Day", 1)

    row = get_first_date_row(soup)

    if row is not None and len(row) > 1:
        date_text = row[1]
        parts = re.findall(r"\d+", date_text)

        if len(parts) == 3:
            if len(parts[0]) == 4:
                # Year first, such as 2024-03-15.
                year, first, second = (int(part) for part in parts)
                readings = ((second, first), (first, second))
            else:
                # Year last, such as 05/03/2024.
                first, second, year = (int(part) for part in parts)
                readings = ((first, second), (second, first))

            if year < 100:
                year += 2000

            candidates: list[date] = []
            for day, month in readings:
                try:
                    candidate = date(year, month, day)
                except ValueError:
                    continue

                if candidate not in candidates:
                    candidates.append(candidate)

            if candidates:
                report_date_value = min(
                    candidates,
                    key=lambda candidate: abs(candidate - mail_date),
                )
                date_flag = 0 if report_date_value == mail_date else 1
                report_date_field = (report_date_value, date_flag)

                shift_value = row[3].strip().lower() if len(row) > 3 else ""
                shift_field = (
                    (shift_value.capitalize(), 0)
                    if shift_value
                    else default_shift
                )

                return report_date_field, shift_field

    # Preserve the original fallback: search outside the tables, accepting
    # the date only when it matches the date being processed.
    text_outside_table = get_text_not_in_table(soup)
    fallback_date, _ = extract_date_from_text(text_outside_table)

    if fallback_date is not None and fallback_date == mail_date:
        return (fallback_date, 0), ("Day", 0)

    return default_date, default_shift


def extract_other_data(text: str) -> ExtractedMaintenanceData:
    """Extract maintenance values as (value, flag) pairs.

    Flag 0 means found, flag 1 means not found and defaulted, and flag 2
    means found with an assumed unit.
    """
    text = re.sub(r"fuel\s+of", "", text, flags=re.IGNORECASE)

    number_pattern = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
    words = {
        "zero": 0,
        "none": 0,
        "no": 0,
        "one": 1,
        "two": 2,
        "three": 3,
        "four": 4,
        "five": 5,
        "six": 6,
        "seven": 7,
        "eight": 8,
        "nine": 9,
        "ten": 10,
        "eleven": 11,
        "twelve": 12,
        "thirteen": 13,
        "fourteen": 14,
        "fifteen": 15,
        "sixteen": 16,
        "seventeen": 17,
        "eighteen": 18,
        "nineteen": 19,
        "twenty": 20,
    }
    vocabulary = [
        "switchover",
        "switchovers",
        "generator",
        "consumed",
        "diesel",
        "litres",
        "liters",
        "minutes",
    ]
    separator = r"(?:&|and|,|/|\+|plus)"
    generator_list = re.compile(
        r"((?:\d[\d,]*(?:\.\d+)?\s*kva\s*(?:" + separator
        + r"\s*)?)+)generators?\b",
        re.IGNORECASE,
    )

    def to_number(value: str) -> float:
        return float(value.replace(",", ""))

    def fix_keyword(match: re.Match[str]) -> str:
        word = match.group(0)
        normalized_word = word.lower()

        if len(normalized_word) < 6 or normalized_word in vocabulary:
            return word

        cutoff = 85 if len(normalized_word) >= 8 else 80
        match_result = process.extractOne(
            normalized_word,
            vocabulary,
            scorer=fuzz.ratio,
            score_cutoff=cutoff,
        )
        return match_result[0] if match_result else word

    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"[A-Za-z]+", fix_keyword, text)

    extracted: ExtractedMaintenanceData = {
        "switchovers": (0, 1),
        "generator": (" KVA", 1),
        "run_minutes": (0.0, 1),
        "run_hours": (0.0, 1),
        "load_kw": (0.0, 1),
        "diesel_litres": (0.0, 1),
    }

    # Find the reported number of switchovers.
    match = re.search(
        r"switch\s*-?\s*overs?\b[^.]*?\bis\s+(\w+)",
        text,
        re.IGNORECASE,
    )
    if match:
        token = match.group(1).lower()
        switchovers = int(token) if token.isdigit() else words.get(token)

        # Keep the default flagged value if the word is unrecognized.
        if switchovers is not None:
            extracted["switchovers"] = (switchovers, 0)

    # Find generator ratings, preferring ratings grouped with "generator(s)".
    found_ratings: list[str] = []
    for match in generator_list.finditer(text):
        for rating in re.findall(
            number_pattern + r"\s*kva",
            match.group(1),
            re.IGNORECASE,
        ):
            if rating not in found_ratings:
                found_ratings.append(rating)

    if not found_ratings:
        match = re.search(number_pattern + r"\s*kva", text, re.IGNORECASE)
        if match:
            found_ratings.append(match.group(1))

    if found_ratings:
        generator_value = " & ".join(
            f"{rating} KVA" for rating in found_ratings
        )
        extracted["generator"] = (generator_value, 0)

    # Find running time in hours and/or minutes.
    run_pattern = re.compile(
        r"\b(?:run|runs|running|ran)\b\s*(?:for\s*)?(?=\d)"
        r"(?:" + number_pattern + r"\s*(?:hours?|hrs?|h)\b)?"
        r"\s*,?\s*(?:and\s*)?"
        r"(?:" + number_pattern + r"\s*(?:minutes?|mins?|m)\b)?",
        re.IGNORECASE,
    )

    for match in run_pattern.finditer(text):
        hours_text, minutes_text = match.group(1), match.group(2)
        if hours_text or minutes_text:
            hours = to_number(hours_text) if hours_text else 0.0
            minutes = to_number(minutes_text) if minutes_text else 0.0
            extracted["run_minutes"] = (hours * 60 + minutes, 0)
            extracted["run_hours"] = (hours + minutes / 60, 0)
            break

    # Find load in kW; a bare W is accepted with an assumed-unit flag.
    match = re.search(
        r"\bload\s*(?:of|is|:)?\s*" + number_pattern + r"\s*(k?)w\b",
        text,
        re.IGNORECASE,
    )
    if match:
        load_value = to_number(match.group(1))
        load_flag = 0 if match.group(2) else 2
        extracted["load_kw"] = (load_value, load_flag)

    # Anchor diesel quantity on "consumed" to avoid unrelated litre values.
    match = re.search(
        r"\bconsum\w*\s*(?:(?:of\s+)?(?:fuel|diesel)\s*)?(?:of\s*)?"
        + number_pattern
        + r"\s*(?:(?:of\s+)?(?:fuel|diesel)\s*(?:of\s*)?)?"
        + r"(?:litres?|liters?|ltrs?|l)\b",
        text,
        re.IGNORECASE,
    )
    if match:
        extracted["diesel_litres"] = (to_number(match.group(1)), 0)

    # If zero switchovers are explicit and no run/load/fuel data was found,
    # treat those operating values as zero.
    switchovers, switchovers_flag = extracted["switchovers"]
    if (
        switchovers == 0
        and switchovers_flag == 0
        and all(
            extracted[field][1] == 1
            for field in ("run_minutes", "load_kw", "diesel_litres")
        )
    ):
        for field in ("run_minutes", "run_hours", "load_kw", "diesel_litres"):
            extracted[field] = (0.0, 0)

    return extracted


def maintenance_parser(
    mail_content: str,
    mail_date: date,
) -> MaintenanceReport:
    """Parse an email body into a flagged maintenance report."""
    if not isinstance(mail_content, str) or not isinstance(mail_date, date):
        raise ParsingError("Maintenance email content or date has an invalid format.")

    try:
        soup = BeautifulSoup(mail_content, "lxml")
        remove_redundant_html(soup)

        report_date, shift = get_date_and_shift(soup, mail_date)
        text_outside_table = get_text_not_in_table(soup)
        other_data = extract_other_data(text_outside_table)

        return MaintenanceReport(
            report_date=report_date,
            shift=shift,
            switch_overs=other_data["switchovers"],
            generator=other_data["generator"],
            running_time_hr=other_data["run_hours"],
            running_time_mins=other_data["run_minutes"],
            avg_load=other_data["load_kw"],
            volume_of_diesel=other_data["diesel_litres"],
        )
    except ParsingError:
        raise
    except Exception as exc:
        # Never attach email content to an error message or log record.
        raise ParsingError("Maintenance email could not be parsed.") from exc
