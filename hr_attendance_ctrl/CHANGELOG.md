# Changelog

## 19.0.1.1.3 - 2026-08-12

- Made the complete transparent map overlay receive mouse and touch events.
- Added a full-size SVG interaction surface so dragging works outside existing polygon shapes.

## 19.0.1.1.2 - 2026-08-12

- Replaced pointer-capture panning with global mouse and touch listeners for broader browser and Odoo webview compatibility.
- Keep map dragging active when the cursor leaves the SVG overlay.

## 19.0.1.1.1 - 2026-08-12

- Added mouse and touch drag/pan support to the self-contained polygon editor.
- Prevented a map drag from accidentally creating a polygon vertex.

## 19.0.1.1.0 - 2026-08-12

- Added Odoo 19-compatible attendance controller and OWL patch.
- Store browser GPS coordinates during systray check-in and check-out.
- Resolve check-in and check-out office fields from PostGIS polygons.
- Replaced deprecated country-name fields with office-location relations.
- Added a self-contained polygon editor; no third-party JavaScript is downloaded at runtime.
- Restricted iframe messages to the same origin.
- Updated store documentation, privacy disclosure, and deployment requirements.

## 19.0.1.0.0 - 2026-08-12

- Initial Odoo 19 conversion.
