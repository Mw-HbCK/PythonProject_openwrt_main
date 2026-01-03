BEGIN TRANSACTION;
CREATE TABLE backup_history (
	id INTEGER NOT NULL, 
	backup_filename VARCHAR(255) NOT NULL, 
	backup_path VARCHAR(512) NOT NULL, 
	backup_size BIGINT NOT NULL, 
	databases TEXT NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	error_message TEXT, 
	cloud_uploaded BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "backup_history" VALUES(1,'','',0,'[]','failed','invalid literal for int() with base 10: ''30  # 保留最近N个备份''',0,'2026-01-01 17:30:55.267372');
CREATE TABLE users (
	id INTEGER NOT NULL, 
	username VARCHAR(80) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	token VARCHAR(64) NOT NULL, 
	created_at DATETIME, 
	updated_at DATETIME, 
	is_active BOOLEAN, role VARCHAR(20) DEFAULT 'user', 
	PRIMARY KEY (id)
);
INSERT INTO "users" VALUES(1,'admin','240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9','reW6pxH-OvjecVcvQZCfKbjsZRh3PU0DDaHCyyTM1oFTnhOxssP5v8R8iD1QKhS6','2025-12-30 07:25:58.232114','2025-12-30 13:46:16.486448',1,'admin');
CREATE UNIQUE INDEX ix_users_username ON users (username);
CREATE UNIQUE INDEX ix_users_token ON users (token);
COMMIT;