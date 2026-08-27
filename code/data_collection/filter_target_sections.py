import argparse
import csv
import logging
import sys


LOGGER = logging.getLogger(__name__)
csv.field_size_limit(sys.maxsize)


def configure_logging(level):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def get_section_category(title, section_type):
    """Assign a normalized section category based on title and section type."""
    title = str(title).strip().lower()
    section_type = str(section_type).strip().lower()

    if "result" in title and "discussion" in title:
        return None

    if "intro" in section_type or "background" in section_type:
        return "introduction"
    if ("method" in section_type or "material" in section_type or "experimental" in section_type) and "supplementary" not in section_type:
        return "material and method"
    if "result" in section_type:
        return "result"
    if "discussion" in section_type or "conclu" in section_type:
        return "discussion and conclusion"
    if "intro" in title or "background" in title:
        return "introduction"
    if ("method" in title or "material" in title or "experimental" in title) and "supplementary" not in title:
        return "material and method"
    if "result" in title:
        return "result"
    if "discussion" in title or "conclu" in title:
        return "discussion and conclusion"
    return None


def extract_valid_paper_data(current_id, paper_rows):
    """Return concatenated introduction and discussion text when both are present."""
    if not current_id:
        return None

    seen_rows = set()
    has_intro = False
    has_discussion = False
    intro_content = ""
    discussion_content = ""

    for title, section_type, content in paper_rows:
        fingerprint = (title, section_type, content)
        if fingerprint in seen_rows:
            continue
        seen_rows.add(fingerprint)

        category = get_section_category(title, section_type)
        if category == "introduction":
            has_intro = True
            intro_content += content
        elif category == "discussion and conclusion":
            has_discussion = True
            discussion_content += content

    if has_intro and has_discussion:
        return [current_id, intro_content + discussion_content]
    return None


def validate_input_columns(fieldnames):
    required_columns = {"id", "section_title", "section_type", "section_content"}
    missing_columns = required_columns.difference(fieldnames or [])
    if missing_columns:
        raise ValueError(f"Input CSV is missing required columns: {sorted(missing_columns)}")


def filter_intro_discussion_sections(input_file, output_file):
    """Stream over section rows and retain papers with both introduction and discussion text."""
    LOGGER.info("Starting section filtering.")
    line_count = 0
    match_paper_count = 0

    with open(input_file, mode="r", encoding="utf-8") as fin, open(output_file, mode="w", encoding="utf-8", newline="") as fout:
        reader = csv.DictReader(fin)
        validate_input_columns(reader.fieldnames)
        writer = csv.writer(fout)
        writer.writerow(["id", "section_content"])

        current_id = None
        current_paper_rows = []
        write_buffer = []

        for row in reader:
            line_count += 1
            row_id = row["id"]
            title = row["section_title"]
            section_type = row["section_type"]
            content = row["section_content"]

            if row_id != current_id:
                result = extract_valid_paper_data(current_id, current_paper_rows)
                if result:
                    write_buffer.append(result)
                    match_paper_count += 1
                current_id = row_id
                current_paper_rows = []

            current_paper_rows.append((title, section_type, content))

            if line_count % 1_000_000 == 0:
                if write_buffer:
                    writer.writerows(write_buffer)
                    write_buffer.clear()
                LOGGER.info("Scanned %s rows and retained %s papers so far.", f"{line_count:,}", f"{match_paper_count:,}")

        result = extract_valid_paper_data(current_id, current_paper_rows)
        if result:
            write_buffer.append(result)
            match_paper_count += 1
        if write_buffer:
            writer.writerows(write_buffer)

    LOGGER.info(
        "Finished section filtering: %s rows scanned, %s papers written.",
        f"{line_count:,}",
        f"{match_paper_count:,}",
    )


def parse_args():
    parser = argparse.ArgumentParser(description="Retain introduction and discussion text for each paper.")
    parser.add_argument("--input_file", default="../../data/interim/pmc/extracted_article_sections.csv")
    parser.add_argument("--output_file", default="../../data/interim/pmc/intro_discussion_sections.csv")
    parser.add_argument("--log_level", default="INFO")
    return parser.parse_args()


def main():
    args = parse_args()
    configure_logging(args.log_level)
    filter_intro_discussion_sections(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
