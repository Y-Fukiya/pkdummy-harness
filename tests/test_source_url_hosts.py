from tools.build_docs_site import source_metadata
from tools.pharmacology_review import source_kind


def test_source_classification_uses_hostname_not_substrings():
    for domain in ("pubmed.ncbi.nlm.nih.gov", "dailymed.nlm.nih.gov", "sciencedirect.com"):
        assert source_metadata(f"https://{domain}.example.org/123/")["kind"] == f"{domain}.example.org"
    assert source_kind("https://evil.example/?next=https://www.fda.gov") == "unclassified"
    assert source_kind("https://fda.gov.example.org") == "unclassified"
    assert source_kind("https://www.accessdata.fda.gov/label.pdf") == "regulatory"
    assert source_kind("https://pubmed.ncbi.nlm.nih.gov/123/") == "primary_or_regulatory"
