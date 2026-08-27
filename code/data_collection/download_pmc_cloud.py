#!/usr/bin/env python3
"""Download versioned PMC article XML from the official NLM AWS dataset.

The downloader converts individual JATS XML objects into tar.gz batches
consumed by the existing PMC extraction scripts. It intentionally
requires an explicit article-version choice when a PMCID has multiple versions.
"""

import argparse
import csv
import hashlib
import io
import json
import re
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


BUCKET_NAME = "pmc-oa-opendata"
BUCKET_HTTPS = "https://pmc-oa-opendata.s3.amazonaws.com"
ARTICLE_VERSION_PATTERN = re.compile(r"^(PMC\d+)(?:\.(\d+))?$", re.IGNORECASE)
MANIFEST_FIELDS = [
    "requested_id",
    "article_version",
    "pmcid",
    "version",
    "license_code",
    "is_pmc_openaccess",
    "is_manuscript",
    "is_retracted",
    "source_url",
    "source_md5",
    "downloaded_sha256",
    "archive",
    "member_path",
    "retrieved_utc",
    "status",
    "error",
]


def load_requested_ids(path):
    """Read one PMCID or versioned PMCID per line, preserving first occurrence."""
    requested_ids = []
    seen = set()
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            value = raw_line.split("#", 1)[0].strip().upper()
            if not value:
                continue
            match = ARTICLE_VERSION_PATTERN.fullmatch(value)
            if not match:
                raise ValueError(
                    f"Invalid identifier on line {line_number}: {value!r}. "
                    "Use PMC1234567 or PMC1234567.1."
                )
            if value not in seen:
                seen.add(value)
                requested_ids.append(value)
    if not requested_ids:
        raise ValueError(f"No PMC identifiers were found in {path}.")
    return requested_ids


def fetch_bytes(url, user_agent, timeout, max_retries):
    """Retrieve one public object with bounded exponential retry behavior."""
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == max_retries:
                raise RuntimeError(f"Failed to retrieve {url}: {error}") from error
            time.sleep(min(2**attempt, 16))
    raise RuntimeError(f"Failed to retrieve {url}.")


def list_article_versions(pmcid, user_agent, timeout, max_retries):
    """Return versioned prefixes currently available for one PMCID."""
    query = urllib.parse.urlencode(
        {"list-type": "2", "prefix": f"{pmcid}.", "delimiter": "/"}
    )
    payload = fetch_bytes(f"{BUCKET_HTTPS}/?{query}", user_agent, timeout, max_retries)
    root = ET.fromstring(payload)
    prefixes = []
    for element in root.iter():
        if element.tag.endswith("Prefix") and element.text:
            prefix = element.text.rstrip("/")
            if ARTICLE_VERSION_PATTERN.fullmatch(prefix):
                prefixes.append(prefix.upper())
    return sorted(set(prefixes), key=lambda value: int(value.rsplit(".", 1)[1]))


def resolve_article_version(requested_id, user_agent, timeout, max_retries):
    """Resolve an unversioned PMCID only when the bucket has one version."""
    match = ARTICLE_VERSION_PATTERN.fullmatch(requested_id)
    pmcid, version = match.groups()
    if version is not None:
        return f"{pmcid.upper()}.{int(version)}"

    versions = list_article_versions(pmcid.upper(), user_agent, timeout, max_retries)
    if not versions:
        raise ValueError(f"No reusable PMC dataset version was found for {pmcid.upper()}.")
    if len(versions) > 1:
        raise ValueError(
            f"{pmcid.upper()} has multiple available versions: {', '.join(versions)}. "
            "Specify the intended version explicitly in the input file."
        )
    return versions[0]


def fetch_article(article_version, user_agent, timeout, max_retries):
    """Retrieve metadata and XML and validate the object digest and identity."""
    metadata_url = f"{BUCKET_HTTPS}/{article_version}/{article_version}.json"
    metadata_bytes = fetch_bytes(metadata_url, user_agent, timeout, max_retries)
    metadata = json.loads(metadata_bytes.decode("utf-8"))

    expected_pmcid, expected_version = article_version.rsplit(".", 1)
    if str(metadata.get("pmcid", "")).upper() != expected_pmcid:
        raise ValueError(f"Metadata PMCID does not match {article_version}.")
    if int(metadata.get("version")) != int(expected_version):
        raise ValueError(f"Metadata version does not match {article_version}.")

    s3_xml_url = metadata.get("xml_url")
    if not s3_xml_url:
        raise ValueError(f"No XML object is available for {article_version}.")
    parsed = urllib.parse.urlsplit(s3_xml_url)
    if parsed.scheme != "s3" or parsed.netloc != BUCKET_NAME:
        raise ValueError(f"Unexpected XML URL for {article_version}: {s3_xml_url}")

    source_url = f"{BUCKET_HTTPS}/{parsed.path.lstrip('/')}"
    source_md5 = urllib.parse.parse_qs(parsed.query).get("md5", [""])[0].lower()
    xml_bytes = fetch_bytes(source_url, user_agent, timeout, max_retries)
    ET.fromstring(xml_bytes)

    downloaded_md5 = hashlib.md5(xml_bytes).hexdigest()
    if source_md5 and downloaded_md5 != source_md5:
        raise ValueError(
            f"MD5 mismatch for {article_version}: expected {source_md5}, "
            f"downloaded {downloaded_md5}."
        )
    return metadata, metadata_bytes, xml_bytes, source_url, source_md5


def add_bytes_to_tar(archive, member_name, payload):
    info = tarfile.TarInfo(member_name)
    info.size = len(payload)
    info.mtime = 0
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(payload))


def download_articles(
    requested_ids,
    output_directory,
    manifest_path,
    batch_size,
    user_agent,
    timeout,
    max_retries,
):
    """Download requested article versions into consistently named archive batches."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(manifest_path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    existing_archives = list(output_directory.glob("pmc_cloud_*.tar.gz"))
    if existing_archives:
        names = ", ".join(path.name for path in existing_archives[:3])
        raise FileExistsError(
            f"Output directory already contains PMC cloud archives ({names}). "
            "Use a new directory or move the existing archives first."
        )

    rows = []
    archive = None
    archive_path = None
    successes = 0
    try:
        for requested_id in requested_ids:
            row = {field: "" for field in MANIFEST_FIELDS}
            row["requested_id"] = requested_id
            try:
                article_version = resolve_article_version(
                    requested_id, user_agent, timeout, max_retries
                )
                if successes % batch_size == 0:
                    if archive is not None:
                        archive.close()
                    archive_number = successes // batch_size + 1
                    archive_path = output_directory / f"pmc_cloud_{archive_number:05d}.tar.gz"
                    archive = tarfile.open(archive_path, "w:gz", compresslevel=6)

                metadata, metadata_bytes, xml_bytes, source_url, source_md5 = fetch_article(
                    article_version, user_agent, timeout, max_retries
                )
                member_path = f"{article_version}/{article_version}.xml"
                add_bytes_to_tar(archive, member_path, xml_bytes)
                add_bytes_to_tar(
                    archive,
                    f"{article_version}/{article_version}.json",
                    metadata_bytes,
                )

                row.update(
                    {
                        "article_version": article_version,
                        "pmcid": metadata.get("pmcid", ""),
                        "version": metadata.get("version", ""),
                        "license_code": metadata.get("license_code", ""),
                        "is_pmc_openaccess": metadata.get("is_pmc_openaccess", ""),
                        "is_manuscript": metadata.get("is_manuscript", ""),
                        "is_retracted": metadata.get("is_retracted", ""),
                        "source_url": source_url,
                        "source_md5": source_md5,
                        "downloaded_sha256": hashlib.sha256(xml_bytes).hexdigest(),
                        "archive": archive_path.name,
                        "member_path": member_path,
                        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                        "status": "success",
                    }
                )
                successes += 1
                print(f"Downloaded {article_version} -> {archive_path.name}")
            except Exception as error:
                row.update({"status": "failed", "error": str(error)})
                print(f"Failed {requested_id}: {error}", file=sys.stderr)
            rows.append(row)
    finally:
        if archive is not None:
            archive.close()

    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    failures = len(rows) - successes
    print(f"Downloaded {successes} article versions; {failures} failed.")
    print(f"Acquisition manifest: {manifest_path}")
    return failures


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Download explicit PMC article versions from the official NLM AWS "
            "dataset and package their XML for this repository's extraction pipeline."
        )
    )
    parser.add_argument("--pmcid_file", required=True, help="One PMC ID per line.")
    parser.add_argument("--output_directory", default="../../data/raw/pmc")
    parser.add_argument(
        "--manifest",
        default="../../data/raw/pmc/download_manifest.csv",
        help="CSV provenance and checksum manifest written after retrieval.",
    )
    parser.add_argument("--batch_size", type=int, default=1000)
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--max_retries", type=int, default=4)
    parser.add_argument(
        "--user_agent",
        default="aiwriting-code-availability/1.0",
        help="HTTP User-Agent sent to the public NLM AWS dataset.",
    )
    args = parser.parse_args()
    if args.batch_size <= 0:
        parser.error("--batch_size must be positive.")
    if args.timeout <= 0:
        parser.error("--timeout must be positive.")
    if args.max_retries < 0:
        parser.error("--max_retries cannot be negative.")
    return args


def main():
    args = parse_args()
    requested_ids = load_requested_ids(args.pmcid_file)
    failures = download_articles(
        requested_ids=requested_ids,
        output_directory=args.output_directory,
        manifest_path=args.manifest,
        batch_size=args.batch_size,
        user_agent=args.user_agent,
        timeout=args.timeout,
        max_retries=args.max_retries,
    )
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
