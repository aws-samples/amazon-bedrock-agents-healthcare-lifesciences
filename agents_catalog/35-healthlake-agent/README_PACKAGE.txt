HealthLake AI Assistant - HTML Archive Package
===============================================

This HTML archive is designed to be self-contained when packaged with the images.

PACKAGING INSTRUCTIONS:
-----------------------

To create a complete self-contained archive:

1. Create a ZIP file containing:
   - README.html (this HTML file)
   - docs/ folder (with all subdirectories)
   
2. The folder structure should be:
   HealthLake-Agent-Documentation/
   ├── README.html
   └── docs/
       └── generated-diagrams/
           ├── healthlake_agentcore_architecture.png
           ├── agentcore_components.png
           └── healthlake_architecture.png

3. When extracted, open README.html in any web browser

ALTERNATIVE - Single File Distribution:
---------------------------------------

If you need a truly single-file solution, you can:

1. Open README.html in a web browser
2. Use the browser's "Save As" > "Web Page, Complete" option
3. This will create a folder with all embedded resources

NOTES:
------
- The HTML file uses relative paths to reference images
- All styling is embedded in the HTML (no external CSS)
- No JavaScript dependencies
- Works offline once packaged
- Compatible with all modern browsers

Created: February 24, 2026
Version: 1.0.0
