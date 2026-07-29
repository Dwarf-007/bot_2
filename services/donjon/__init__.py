"""
SERVICES/DONJON/__init__.py
Consolidated Donjon import-graph package.

Groups the Donjon-specific import pipeline that was previously spread across
``services/generators`` (donjon_json_importer) and ``services/dungeons``
(graph builder, TSV parser, corridor resolver, bundle exporter, post-processing
pipeline + hook).
"""