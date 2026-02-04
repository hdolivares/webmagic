-- Dump of customer_users table
-- Generated: 2026-02-04
-- Rows: 3

INSERT INTO customer_users (id, email, password_hash, full_name, phone, email_verified, email_verification_token, email_verified_at, password_reset_token, password_reset_expires, last_login, login_count, is_active, created_at, updated_at, primary_site_id) VALUES
('64729095-cf6a-4401-9e89-2fbb81321832', 'test_sub_1768981815.193588@example.com', '$2b$12$fYsvEAOXBMqenmmwbTdSZuX.sgvLUm8awhcgDUiRWeQ1lBBtPbIYq', 'Subscription Test User', NULL, false, 'ekwbV4SklaqiC-qL8k9HJFiW3IfObvl3XFIlMVR1VlQ', NULL, NULL, NULL, NULL, 0, true, '2026-01-21T07:50:16.927Z', '2026-01-21T07:50:16.927Z', NULL),
('4eb8b1ac-283c-4b83-bddb-93a1973e37fe', 'api-test@example.com', '$2b$12$id0W1Ge/da1jYgtM5.IZgOw9oN/Cnapw6kRSvZ/bu/roJD5Dem7vq', NULL, NULL, false, 'YAUGpnKqESbOcyoruw1gOZ3IDzNetB6UbcPqEgCD544', NULL, NULL, NULL, NULL, 0, true, '2026-01-21T07:57:25.673Z', '2026-01-21T07:57:25.673Z', NULL),
('de490e47-cc5b-4b9c-8eef-3d662e8a9d53', 'test@customer.com', '$2b$12$U8nXQokth9HwoRuElZdsw.rMEs9adxV/CUb/Ia4fOGg7yALuWeIv6', 'Test Customer', NULL, true, NULL, NULL, NULL, NULL, '2026-01-25T11:16:51.080Z', 11, true, '2026-01-24T20:54:09.965Z', '2026-01-25T05:16:51.081Z', NULL);

