-- Equivalente en SQLite de 00_create_table_tmp.sql (dbo.tbl_sensors_data_temp)
CREATE TABLE IF NOT EXISTS tbl_sensors_data_temp (
    id_data               INTEGER PRIMARY KEY AUTOINCREMENT,
    id_sensor             INTEGER     NOT NULL,
    data_type             CHAR(4)     NOT NULL,
    data_value            REAL        NOT NULL,
    data_date             DATETIME    NOT NULL,
    block_name            VARCHAR(20) NOT NULL,
    id_sensor_on_provider INTEGER     NULL,
    create_user           INTEGER     NULL,
    create_date           DATETIME    NULL,
    create_ip             VARCHAR(20) NULL
);

CREATE INDEX IF NOT EXISTS IX_sensors_data_temp_filtros
    ON tbl_sensors_data_temp (data_date, block_name, data_type);
