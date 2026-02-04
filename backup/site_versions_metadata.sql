-- Dump of site_versions table (metadata only)
-- Generated: 2026-02-04
-- Rows: 1
-- Note: html_content is very large and stored separately in site_versions_html_content.txt

-- To restore, first insert metadata, then UPDATE the html_content from the separate file

INSERT INTO site_versions (id, site_id, version_number, css_content, js_content, assets, change_description, change_type, created_by_type, created_by_id, is_current, is_preview, created_at, html_content) VALUES
('74c125ca-5786-43ac-9f6b-c7e8f74d92f4', '640c1174-e53e-432a-8b9d-521928846223', 1, NULL, NULL, NULL, 'Initial site generation (migrated from filesystem)', 'initial', 'admin', NULL, true, false, '2026-01-21T07:31:03.372Z', NULL);

-- The html_content should be updated separately due to its large size
-- Use: UPDATE site_versions SET html_content = '<content from site_versions_html_content.txt>' WHERE id = '74c125ca-5786-43ac-9f6b-c7e8f74d92f4';

