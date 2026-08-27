import argparse
import csv
import logging
import os
import re
import tarfile
import time
import zlib
from collections import defaultdict

import pandas as pd
from lxml import etree


LOGGER = logging.getLogger(__name__)


def configure_logging(level):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("pubmed_processing.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def clean_element_for_text_extraction(element):
    """Remove inline markup that should not appear in the extracted plain text."""
    if element is None:
        return None
    try:
        cleaned_element = etree.fromstring(etree.tostring(element, encoding="utf-8", method="xml"))
        tags_to_remove = [
            "xref",
            "sup",
            "sub",
            "ref",
            "fn",
            "table-wrap",
            "fig",
            "media",
            "supplementary-material",
        ]
        for tag in tags_to_remove:
            for elem in cleaned_element.xpath(f".//{tag}"):
                parent = elem.getparent()
                if parent is not None:
                    if elem.tail:
                        previous = elem.getprevious()
                        if previous is not None:
                            previous.tail = (previous.tail or "") + elem.tail
                        else:
                            parent.text = (parent.text or "") + elem.tail
                    parent.remove(elem)
        return cleaned_element
    except (etree.SerialisationError, etree.XMLSyntaxError) as error:
        LOGGER.warning("Falling back to the original XML element after cleanup failed: %s", error)
        return element


def extract_text_recursively(element, skip_tags=None):
    """Recursively collect plain text while skipping selected XML tags."""
    if element is None:
        return ""
    if skip_tags is None:
        skip_tags = set()
    if element.tag in skip_tags:
        return ""
    text_parts = []
    if element.text:
        text_parts.append(element.text)
    for child in element:
        child_text = extract_text_recursively(child, skip_tags)
        if child_text:
            text_parts.append(child_text)
        if child.tail:
            text_parts.append(child.tail)
    text_content = " ".join(text_parts)
    text_content = re.sub(r"[\x00-\x1F\x7F]", "", text_content)
    text_content = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text_content)
    text_content = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text_content)
    text_content = re.sub(r"([.!?])([A-Z])", r"\1 \2", text_content)
    text_content = re.sub(r"\s+", " ", text_content)
    return text_content.strip()


def get_clean_text(element):
    """Extract normalized plain text from one XML element."""
    if element is None:
        return ""
    cleaned_element = clean_element_for_text_extraction(element)
    if cleaned_element is None:
        return ""
    try:
        block_tags = {"p", "title", "sec", "list-item", "disp-formula"}
        for elem in cleaned_element.iter():
            if elem.tag in block_tags:
                if elem.tail:
                    if not elem.tail.startswith(" "):
                        elem.tail = " " + elem.tail
                else:
                    elem.tail = " "

        text_content = etree.tostring(cleaned_element, method="text", encoding="unicode")
        text_content = re.sub(r"[\x00-\x1F\x7F]", "", text_content)
        text_content = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", text_content)
        text_content = re.sub(r"([a-zA-Z])(\d)", r"\1 \2", text_content)
        text_content = re.sub(r"([.!?])([A-Z])", r"\1 \2", text_content)
        text_content = re.sub(r"\s+", " ", text_content)
        return text_content.strip()
    except (etree.SerialisationError, Exception) as error:
        LOGGER.warning("Falling back to recursive text extraction: %s", error)
        return extract_text_recursively(
            cleaned_element,
            skip_tags={"xref", "sup", "sub", "ref", "fn", "table-wrap", "fig", "media", "supplementary-material"},
        )


def get_clean_text_fallback(element):
    if element is None:
        return ""
    try:
        return extract_text_recursively(
            element,
            skip_tags={"title", "xref", "sup", "sub", "ref", "fn", "table-wrap", "fig", "media", "supplementary-material"},
        )
    except Exception as error:
        LOGGER.warning("Fallback text extraction failed: %s", error)
        return ""


def get_section_content(sec_element):
    """Extract normalized text from a section, including nested sections."""
    if sec_element is None:
        return ""
    try:
        sec_copy = etree.fromstring(etree.tostring(sec_element, encoding="utf-8", method="xml"))
        title_elem = sec_copy.find("./title")
        if title_elem is not None:
            parent = title_elem.getparent()
            tail_text = title_elem.tail if title_elem.tail else ""
            parent.text = (parent.text or "") + " " + tail_text
            parent.remove(title_elem)
        return get_clean_text(sec_copy)
    except (etree.SerialisationError, etree.XMLSyntaxError) as error:
        LOGGER.warning("XML serialization failed during section extraction: %s", error)
        return get_clean_text_fallback(sec_element)


def parse_xml_with_clean_content(xml_file):
    """Extract top-level section titles, types, and cleaned text from one article."""
    try:
        tree = etree.parse(xml_file)
        root = tree.getroot()
    except etree.XMLSyntaxError:
        return []

    sections = []
    body = root.find(".//body")
    if body is None:
        return sections

    for index, sec in enumerate(body.xpath("./sec"), start=1):
        title_element = sec.find("./title")
        section_title = get_clean_text(title_element).strip() if title_element is not None else ""
        section_type = sec.attrib.get("sec-type", "")
        if not section_title and not section_type:
            section_title = f"section_{index}"
        sections.append((section_title, section_type, get_section_content(sec)))
    return sections


def process_focal_papers(paper_mapping, search_path, output_csv_path):
    """Extract full-text sections for focal papers identified from metadata."""
    total_start_time = time.time()
    total_tar_files = len(paper_mapping)
    total_target_papers = sum(len(pmcs) for pmcs in paper_mapping.values())

    LOGGER.info("Starting full-text extraction for %s focal papers from %s archives.", total_target_papers, total_tar_files)

    output_path = os.path.abspath(output_csv_path)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(["id", "accepted_year", "section_title", "section_type", "section_content"])

        total_found = 0
        for archive_index, (tar_name, pmc_dict) in enumerate(paper_mapping.items(), start=1):
            tar_path = os.path.join(search_path, tar_name)
            if not os.path.exists(tar_path):
                LOGGER.warning("Archive not found and will be skipped: %s", tar_path)
                continue

            tar_start_time = time.time()
            found_in_this_tar = 0
            found_articles = []

            try:
                with tarfile.open(tar_path, "r:gz") as tar:
                    for pmc_id, (inner_path, accepted_year) in pmc_dict.items():
                        try:
                            member = tar.getmember(inner_path)
                            xml_file_object = tar.extractfile(member)
                            if xml_file_object is None:
                                continue
                            sections = parse_xml_with_clean_content(xml_file_object)
                            for section_title, section_type, content in sections:
                                found_articles.append([pmc_id, accepted_year, section_title, section_type, content])
                            found_in_this_tar += 1
                        except KeyError:
                            LOGGER.warning("Member path not found in %s: %s", tar_name, inner_path)
                        except Exception as error:  # pragma: no cover - keep batch jobs running
                            LOGGER.warning("Failed to process %s in %s: %s", pmc_id, tar_name, error)
            except (tarfile.ReadError, zlib.error, EOFError) as error:
                LOGGER.error("Failed to open archive %s: %s", tar_name, error)

            if found_articles:
                csv_writer.writerows(found_articles)

            total_found += found_in_this_tar
            processing_time = time.time() - tar_start_time
            LOGGER.info(
                "[%s/%s] %s: extracted %s/%s papers in %.2fs.",
                archive_index,
                total_tar_files,
                tar_name,
                found_in_this_tar,
                len(pmc_dict),
                processing_time,
            )

    total_time = time.time() - total_start_time
    success_rate = (total_found / total_target_papers * 100.0) if total_target_papers > 0 else 0.0
    LOGGER.info("Finished full-text extraction: %s/%s papers found (%.1f%%).", total_found, total_target_papers, success_rate)
    LOGGER.info("Saved extracted sections to %s.", output_path)
    LOGGER.info("Total runtime: %.2fs.", total_time)


def build_paper_mapping(metadata_dataframe, year_start, year_end):
    """Build an archive-to-paper mapping from the metadata table."""
    dataframe = metadata_dataframe.copy()
    dataframe["accepted_date"] = dataframe["accepted_date"].astype(str)
    dataframe["extracted_year"] = pd.to_numeric(
        dataframe["accepted_date"].str.extract(r"^(\d{4})")[0],
        errors="coerce",
    )
    focal_df = dataframe[(dataframe["extracted_year"] >= year_start) & (dataframe["extracted_year"] <= year_end)].copy()
    if focal_df.empty:
        raise ValueError(f"No articles were found with accepted_date in the range {year_start}-{year_end}.")

    paper_mapping = defaultdict(dict)
    for _, row in focal_df.iterrows():
        file_name_raw = str(row["file_name"])
        pmc_id = str(row["article_pmc"])
        accepted_year = str(int(row["extracted_year"]))
        if ":" not in file_name_raw:
            LOGGER.warning("Skipping malformed file_name value without archive separator: %s", file_name_raw)
            continue
        tar_name, inner_path = file_name_raw.split(":", 1)
        paper_mapping[tar_name][pmc_id] = (inner_path, accepted_year)
    return paper_mapping


def parse_args():
    parser = argparse.ArgumentParser(description="Extract cleaned PMC full-text sections for focal papers.")
    parser.add_argument("--metadata_csv", default="../../data/interim/pmc/pmc_metadata.csv")
    parser.add_argument("--search_path", default="../../data/raw/pmc")
    parser.add_argument("--output_csv", default="../../data/interim/pmc/extracted_article_sections.csv")
    parser.add_argument("--year_start", type=int, default=2021)
    parser.add_argument("--year_end", type=int, default=2024)
    parser.add_argument("--log_level", default="INFO")
    return parser.parse_args()


def main():
    args = parse_args()
    configure_logging(args.log_level)
    metadata_df = pd.read_csv(args.metadata_csv)
    paper_mapping = build_paper_mapping(metadata_df, args.year_start, args.year_end)
    process_focal_papers(paper_mapping, args.search_path, args.output_csv)


if __name__ == "__main__":
    main()
