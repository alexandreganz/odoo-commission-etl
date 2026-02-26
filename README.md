# Odoo ETL & Sales Analytics Dashboard

Professional Python application for extracting sales data from Odoo ERP and visualizing it through an interactive Streamlit dashboard.

## 🚀 Features

### ETL Pipeline
- **Hierarchical Extraction** - Top-down order → item extraction with perfect data integrity
- **Incremental Sync** - Delta updates based on `write_date` for efficient data refresh
- **Secure Configuration** - Credentials managed via `.env` file (never committed)
- **Metadata Tools** - Generate schema diagrams, field value maps, and relationship discovery

### Interactive Dashboard
- **Multi-Page Application** - 5 specialized views for comprehensive analysis
- **Real-Time Filtering** - Filter by operation type, salesperson, year, and value range
- **10+ Visualizations** - Charts, treemaps, distributions, and performance metrics
- **Data Export** - Download filtered data and metrics as CSV
- **Localhost Security** - Dashboard only accessible on your local machine

## 📊 Project Structure

```
Odoo/
├── README.md                          # This file
├── requirements.txt                   # Python dependencies
├── .env                              # Your credentials (DO NOT COMMIT)
├── .env.example                      # Template for credentials
├── .gitignore                        # Excludes sensitive files
│
├── config/
│   └── settings.py                   # Centralized configuration
│
├── src/
│   ├── etl/
│   │   ├── odoo_client.py           # Shared Odoo connection class
│   │   ├── main_pipeline.py         # Full hierarchical extraction
│   │   └── incremental_sync.py      # Delta sync for updates
│   │
│   └── metadata/
│       ├── generate_schema.py       # Generate DBML schema
│       ├── field_value_mapper.py    # Extract unique field values
│       └── discover_tags.py         # Discover model relationships
│
├── dashboard/
│   ├── app.py                       # Main dashboard entry point
│   │
│   ├── pages/                       # Multi-page dashboard views
│   │   ├── 1_overview.py           # Executive summary
│   │   ├── 2_sales_analysis.py     # Salesperson & customer insights
│   │   ├── 3_product_analysis.py   # Product performance
│   │   └── 4_operations.py         # Operation type breakdown
│   │
│   ├── components/
│   │   ├── filters.py              # Sidebar filter widgets
│   │   ├── charts.py               # Plotly chart generators
│   │   └── metrics.py              # KPI card components
│   │
│   └── utils/
│       ├── data_loader.py          # CSV loading with caching
│       └── data_processor.py       # Data aggregations
│
└── outputs/                         # Generated files (gitignored)
    ├── csv/
    │   ├── final_sales_export_top_down.csv
    │   └── sales_data.json
    └── metadata/
        ├── odoo_datamodel.csv
        ├── odoo_unique_values_map.csv
        └── odoo_model_fixed.dbml
```

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- Access to an Odoo instance with XML-RPC enabled

### Setup Steps

1. **Clone or navigate to the project directory**
   ```bash
   cd Odoo
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure credentials**
   ```bash
   # Copy the example file
   cp .env.example .env

   # Edit .env with your actual Odoo credentials
   # Required fields:
   #   ODOO_URL=https://your-odoo-instance.com
   #   ODOO_DB=your_database_name
   #   ODOO_USERNAME=your_username
   #   ODOO_PASSWORD=your_password
   ```

## 📖 Usage

### Running the ETL Pipeline

**Full Extraction (First Run)**
```bash
python -m src.etl.main_pipeline
```
- Extracts all orders and items from Odoo
- Output: `outputs/csv/final_sales_export_top_down.csv`
- Time: ~5-10 minutes for 18,000+ rows

**Incremental Sync (Updates Only)**
```bash
python -m src.etl.incremental_sync
```
- Only fetches records modified since last sync
- Output: `outputs/csv/sales_data.json`
- Time: <1 minute for typical updates

### Launching the Dashboard

```bash
streamlit run dashboard/app.py
```

Dashboard will open at: **http://localhost:8501**

**Dashboard Pages:**
- **Home** - Main overview with KPIs and key charts
- **1. Overview** - Executive summary with top performers
- **2. Sales Analysis** - Salesperson and customer deep-dive
- **3. Product Analysis** - Product performance and NCM classification
- **4. Operations** - Breakdown by operation type

### Metadata Tools

**Generate DBML Schema**
```bash
python -m src.metadata.generate_schema
```
Output: `outputs/metadata/odoo_model_fixed.dbml` (paste into dbdiagram.io)

**Extract Field Value Map**
```bash
python -m src.metadata.field_value_mapper
```
Output: `outputs/metadata/odoo_unique_values_map.csv`

**Discover Tag Model**
```bash
python -m src.metadata.discover_tags
```
Prints the model name for `etapa_tag_ids` field

## 📊 Data Dictionary

### CSV Output Fields (final_sales_export_top_down.csv)

| Field | Type | Description | Example |
|-------|------|-------------|---------|
| `numero` | String | Order document number | "INV-0001/26", "PV-2964/26" |
| `operacao_id` | String | Operation type | "Venda de Mercadoria", "Inventário" |
| `etapa_tag_ids` | String | Workflow stage/tag | "43", "Approved" |
| `vendedor_id` | String | Salesperson name | "João Silva" |
| `participante_id` | String | Customer name with CNPJ | "Empresa ABC - 12.345.678/0001-99" |
| `produto_codigo` | String | Product code | "PROD-001" |
| `produto_ncm_id` | String | NCM classification code | "8471.30.12" |
| `quantidade` | Float | Item quantity | 10.0 |
| `vr_nf` | Float | Invoice value (BRL) | 1500.50 |

**Total Rows:** ~18,590 (varies by data in your Odoo instance)

## 🔧 Troubleshooting

### Authentication Failed
```
❌ Authentication failed: check credentials in .env file
```
**Solution:** Verify your `.env` file has correct credentials:
- Check URL (include `https://`)
- Verify database name
- Test username/password in Odoo web interface first

### Data File Not Found (Dashboard)
```
Data file not found: outputs/csv/final_sales_export_top_down.csv
```
**Solution:** Run the ETL pipeline first:
```bash
python -m src.etl.main_pipeline
```

### Port Already in Use
```
OSError: [Errno 98] Address already in use
```
**Solution:** Stop existing Streamlit process or use different port:
```bash
streamlit run dashboard/app.py --server.port 8502
```

### Module Import Errors
```
ModuleNotFoundError: No module named 'streamlit'
```
**Solution:** Install requirements:
```bash
pip install -r requirements.txt
```

### Slow Dashboard Loading
**Solution:** Dashboard uses caching (`@st.cache_data`). First load is slower, subsequent loads are instant. Cache refreshes every hour automatically.

## 🔒 Security Notes

- **Never commit `.env`** - Contains sensitive credentials (already in `.gitignore`)
- **Outputs are gitignored** - CSV files may contain customer data
- **Dashboard is localhost-only** - Not accessible from external networks by default
- **XML-RPC Security** - Ensure your Odoo instance uses HTTPS

## 📈 Performance

- **ETL Pipeline:** Processes 18,000+ rows in ~5 minutes
- **Dashboard Loading:** <2 seconds with caching
- **Filter Updates:** Real-time (instant)
- **Memory Usage:** ~200MB for typical dataset

## 🛣️ Future Enhancements

- [ ] Add date field extraction for time-series analysis
- [ ] Implement automated scheduling (cron jobs)
- [ ] Add PDF export for reports
- [ ] Customer lifetime value calculations
- [ ] Data quality dashboard (missing values, outliers)
- [ ] Email alerts for sync failures

## 📝 Development Notes

### Adding New Charts

1. Create chart function in `dashboard/components/charts.py`
2. Import in page file (e.g., `dashboard/pages/2_sales_analysis.py`)
3. Call with filtered dataframe

### Adding New Pages

1. Create file `dashboard/pages/N_page_name.py` (N = page number)
2. Include standard imports and page config
3. Streamlit auto-detects and adds to sidebar

### Modifying Filters

Edit `dashboard/components/filters.py` - all pages use the same filter component.

## 🤝 Contributing

This is a personal project. For questions or issues:
1. Check the Troubleshooting section
2. Verify `.env` configuration
3. Review logs in terminal output

## 📄 License

Private project - All rights reserved

## 🙏 Acknowledgments

- **Odoo** - Open-source ERP platform
- **Streamlit** - Dashboard framework
- **Plotly** - Interactive visualizations
- **Pandas** - Data processing

---

**Last Updated:** 2026-02-03
**Python Version:** 3.8+
**Streamlit Version:** 1.28.0+
