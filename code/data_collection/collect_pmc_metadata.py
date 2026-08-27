import argparse
import logging
import os
import tarfile
import xml.etree.ElementTree as ET
from multiprocessing import Pool, cpu_count
from pathlib import Path

import pandas as pd


LOGGER = logging.getLogger(__name__)


def configure_logging(level):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(message)s",
    )


def _format_date(date_element):
    """Return a YYYY-MM-DD string when day, month, and year are all available."""
    if date_element is None:
        return None
    day_element = date_element.find("day")
    month_element = date_element.find("month")
    year_element = date_element.find("year")
    if day_element is None or month_element is None or year_element is None:
        return None
    day = (day_element.text or "").strip()
    month = (month_element.text or "").strip()
    year = (year_element.text or "").strip()
    if not day or not month or not year:
        return None
    return f"{year}-{month.zfill(2)}-{day.zfill(2)}"


def extract_dates_from_xml_content(xml_content, file_name):
    """Extract publication metadata from one PMC XML article."""
    try:
        root = ET.fromstring(xml_content)

        article_pmid_element = root.find(".//article-id[@pub-id-type='pmid']")
        article_pmc_element = root.find(".//article-id[@pub-id-type='pmc']")
        article_doi_element = root.find(".//article-id[@pub-id-type='doi']")
        journal_id_element = root.find(".//journal-id[@journal-id-type='publisher-id']")

        pub_dates = {"nihms-submitted": None, "ppub": None, "pmc-release": None}
        for pub_date in root.findall(".//pub-date"):
            pub_type = pub_date.attrib.get("pub-type")
            if pub_type in pub_dates:
                pub_dates[pub_type] = _format_date(pub_date)

        history_dates = {
            "received_date": None,
            "revised_date": None,
            "accepted_date": None,
        }
        for date_element in root.findall(".//history/date"):
            date_type = date_element.attrib.get("date-type")
            formatted_date = _format_date(date_element)
            if date_type == "received":
                history_dates["received_date"] = formatted_date
            elif date_type == "rev-recd":
                history_dates["revised_date"] = formatted_date
            elif date_type == "accepted":
                history_dates["accepted_date"] = formatted_date

        return {
            "file_name": file_name,
            "nihms-submitted": pub_dates["nihms-submitted"],
            "ppub": pub_dates["ppub"],
            "pmc-release": pub_dates["pmc-release"],
            "article_pmid": article_pmid_element.text if article_pmid_element is not None else None,
            "article_pmc": article_pmc_element.text if article_pmc_element is not None else None,
            "article_doi": article_doi_element.text if article_doi_element is not None else None,
            "journal_id": journal_id_element.text if journal_id_element is not None else None,
            "epub_date": _format_date(root.find(".//pub-date[@pub-type='epub']")),
            "received_date": history_dates["received_date"],
            "revised_date": history_dates["revised_date"],
            "accepted_date": history_dates["accepted_date"],
            "status": "success",
        }
    except ET.ParseError as error:
        LOGGER.warning("XML parsing failed for %s: %s", file_name, error)
        return {"file_name": file_name, "status": "failed", "error": f"XML parsing failed: {error}"}
    except Exception as error:  # pragma: no cover - defensive error capture for batch jobs
        LOGGER.warning("Metadata extraction failed for %s: %s", file_name, error)
        return {
            "file_name": file_name,
            "status": "failed",
            "error": f"Metadata extraction failed: {error}",
        }


def process_single_tar_gz(tar_gz_path):
    """Extract metadata from all XML files in one PMC tar.gz archive."""
    results = []
    tar_gz_name = os.path.basename(tar_gz_path)

    try:
        with tarfile.open(tar_gz_path, "r:gz") as tar:
            xml_members = [member for member in tar.getmembers() if member.name.endswith(".xml") and member.isfile()]
            LOGGER.info("Processing %s with %s XML files.", tar_gz_name, len(xml_members))
            for member in xml_members:
                try:
                    xml_file = tar.extractfile(member)
                    if xml_file is None:
                        continue
                    xml_content = xml_file.read().decode("utf-8")
                    full_file_name = f"{tar_gz_name}:{member.name}"
                    results.append(extract_dates_from_xml_content(xml_content, full_file_name))
                except Exception as error:  # pragma: no cover - batch jobs should keep going
                    results.append(
                        {
                            "file_name": f"{tar_gz_name}:{member.name}",
                            "status": "failed",
                            "error": f"XML extraction failed: {error}",
                        }
                    )
                    LOGGER.warning("Failed to process %s inside %s: %s", member.name, tar_gz_name, error)
    except Exception as error:  # pragma: no cover - batch jobs should keep going
        results.append(
            {
                "file_name": tar_gz_name,
                "status": "failed",
                "error": f"Archive processing failed: {error}",
            }
        )
        LOGGER.error("Failed to open archive %s: %s", tar_gz_name, error)

    return results


def find_all_tar_gz_files(root_directory):
    """Return all .tar.gz files under a directory."""
    return [str(path) for path in Path(root_directory).rglob("*.tar.gz")]


def process_multiple_tar_gz_files(source_directory, output_csv, max_workers=None):
    """Extract metadata from all PMC archives under a directory."""
    tar_gz_files = find_all_tar_gz_files(source_directory)
    if not tar_gz_files:
        raise FileNotFoundError(f"No .tar.gz files were found under {source_directory}.")

    if max_workers is None:
        max_workers = min(cpu_count(), len(tar_gz_files))
    if max_workers <= 0:
        raise ValueError("max_workers must be a positive integer.")

    LOGGER.info("Found %s archives under %s.", len(tar_gz_files), source_directory)
    LOGGER.info("Using %s worker processes.", max_workers)

    all_results = []
    with Pool(processes=max_workers) as pool:
        for tar_result in pool.map(process_single_tar_gz, tar_gz_files):
            all_results.extend(tar_result)

    success_results = [result for result in all_results if result.get("status") == "success"]
    failed_results = [result for result in all_results if result.get("status") == "failed"]

    LOGGER.info(
        "Finished metadata extraction: %s XML files processed, %s succeeded, %s failed.",
        len(all_results),
        len(success_results),
        len(failed_results),
    )

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if success_results:
        dataframe = pd.DataFrame(success_results).drop(columns=["status"], errors="ignore")
        dataframe.to_csv(output_path, index=False, encoding="utf-8")
    else:
        raise RuntimeError("No XML files were processed successfully.")

    report_path = output_path.parent / "processing_report.txt"
    with report_path.open("w", encoding="utf-8") as report_file:
        report_file.write("Processing report\n")
        report_file.write(f"Archive files: {len(tar_gz_files)}\n")
        report_file.write(f"XML files: {len(all_results)}\n")
        report_file.write(f"Successful files: {len(success_results)}\n")
        report_file.write(f"Failed files: {len(failed_results)}\n")
        if failed_results:
            report_file.write("\nFailures\n")
            for index, failed_result in enumerate(failed_results, start=1):
                report_file.write(
                    f"{index}. {failed_result['file_name']}: {failed_result.get('error', 'Unknown error')}\n"
                )

    LOGGER.info("Saved metadata to %s.", output_path)
    LOGGER.info("Saved processing report to %s.", report_path)


def parse_args():
    parser = argparse.ArgumentParser(description="Extract publication metadata from PMC XML archives.")
    parser.add_argument("--source_directory", default="../../data/raw/pmc")
    parser.add_argument("--output_csv", default="../../data/interim/pmc/pmc_metadata.csv")
    parser.add_argument("--max_workers", type=int, default=None)
    parser.add_argument("--log_level", default="INFO")
    return parser.parse_args()


def main():
    args = parse_args()
    configure_logging(args.log_level)
    process_multiple_tar_gz_files(args.source_directory, args.output_csv, args.max_workers)


if __name__ == "__main__":
    main()
