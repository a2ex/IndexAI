import logging
from datetime import datetime, timezone
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)


def generate_sitemap(urls: list[str], output_path: str) -> str:
    """Generate a valid sitemap XML file."""
    urlset = ET.Element("urlset")
    urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")

    for url in urls:
        url_elem = ET.SubElement(urlset, "url")
        loc = ET.SubElement(url_elem, "loc")
        loc.text = url
        lastmod = ET.SubElement(url_elem, "lastmod")
        lastmod.text = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        changefreq = ET.SubElement(url_elem, "changefreq")
        changefreq.text = "daily"
        priority = ET.SubElement(url_elem, "priority")
        priority.text = "0.8"

    tree = ET.ElementTree(urlset)
    tree.write(output_path, encoding="UTF-8", xml_declaration=True)
    logger.info(f"Generated sitemap with {len(urls)} URLs at {output_path}")
    return output_path
