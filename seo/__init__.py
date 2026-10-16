"""WP AIWriter SEO Engine: read-only WordPress inventory, audits and SEO matrix.

The engine never writes to WordPress. Only ``seo.fixes`` can, and only for entries an
owner approved in ``data/seo/approved-fixes.json`` when run with ``--apply``.
"""
