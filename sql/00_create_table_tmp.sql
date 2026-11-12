USE deptmaintenance
GO

/****** Object:  Table [dbo].[tbl_sensors_data]    Script Date: 14/04/2026 12:34:27 p.�m. ******/
SET ANSI_NULLS ON
GO

SET QUOTED_IDENTIFIER ON
GO

-- drop table [tbl_sensors_data_temp]
CREATE TABLE [dbo].[tbl_sensors_data_temp](
	[id_data] [int] IDENTITY(1,1) NOT NULL,
	[id_sensor] [int] NOT NULL,
	[data_type] [char](4) NOT NULL,
	[data_value] [real] NOT NULL,
	[data_date] [datetime] NOT NULL,
	[block_name] [varchar](20) NOT NULL,
	[id_sensor_on_provider] [int] NULL,
	[create_user] [int] NULL,
	[create_date] [datetime] NULL,
	[create_ip] [varchar](20) NULL,
 CONSTRAINT [PK_IOT_SensorData_temp] PRIMARY KEY CLUSTERED 
(
	[id_data] ASC
)WITH (PAD_INDEX = OFF, STATISTICS_NORECOMPUTE = OFF, IGNORE_DUP_KEY = OFF, ALLOW_ROW_LOCKS = ON, ALLOW_PAGE_LOCKS = ON, OPTIMIZE_FOR_SEQUENTIAL_KEY = OFF) ON [PRIMARY]
) ON [PRIMARY]
GO


-- Índice opcional para que los filtros de la interfaz sean rápidos
CREATE INDEX IX_sensors_data_temp_filtros
    ON [dbo].[tbl_sensors_data_temp] (data_date, block_name, data_type);
GO
