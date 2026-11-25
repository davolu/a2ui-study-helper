"""
Try it: what happens when an agent asks for a block that is not in the catalog?

    ../.venv/bin/python check_invalid_ui.py

The official SDK rejects it, so the broken UI never reaches the browser.
"""

from a2ui.core import A2uiError

from study_agent import CATALOG, GENERATOR

processor = GENERATOR.create_processor({"1.0": {"supportedCatalogIds": [CATALOG.catalog_id]}})

reply_from_agent = """Here is your answer!
<a2ui-json>[{"version": "1.0", "createSurface": {
  "surfaceId": "demo", "catalogId": "%s",
  "components": [{"id": "root", "component": "Spaceship", "text": "Blast off"}]
}}]</a2ui-json>""" % CATALOG.catalog_id

try:
    processor.parse_response(reply_from_agent)
    print("Accepted (this should not happen)")
except A2uiError as error:
    print("Rejected by the A2UI SDK:")
    print(" ", error)
