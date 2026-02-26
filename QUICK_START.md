# Quick Start Guide - Odoo Sales Dashboard

## 🚀 Launch Dashboard (Fastest Way)

```bash
cd Odoo
streamlit run dashboard/app.py
```

**Dashboard URL:** http://localhost:8501

## 📊 What You'll See

### Main Dashboard (Home Page)
- 💰 Total Revenue
- 📦 Total Orders
- 📊 Active Products
- 📈 Average Order Value
- Interactive charts and filters

### Navigation (Sidebar)
1. **Overview** - Executive summary with top performers
2. **Sales Analysis** - Salesperson and customer insights
3. **Product Analysis** - Product performance and NCM codes
4. **Operations** - Breakdown by operation type

### Filters (Sidebar)
- Operation Type (multi-select)
- Salesperson (multi-select)
- Year (multi-select)
- Invoice Value Range (slider)

## 🔧 If This Is Your First Time

### 1. Install Dependencies (One Time Only)
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials (Already Done!)
Your `.env` file already contains:
```
ODOO_URL=https://agromaquinas.teste.tauga.online
ODOO_DB=teste_agromaquinas
ODOO_USERNAME=teste
ODOO_PASSWORD=Ale.12125
```

### 3. Data Already Loaded ✅
The CSV file with 18,590 rows is already in `outputs/csv/`.
**You can start the dashboard immediately!**

## 🔄 Running ETL Pipeline (Optional)

Only run these if you need to refresh data from Odoo:

### Full Extraction
```bash
python -m src.etl.main_pipeline
```
Extracts all orders and items (~5-10 min for 18k+ rows)

### Incremental Sync (Faster)
```bash
python -m src.etl.incremental_sync
```
Only fetches new/modified records (<1 min)

## 📁 Important Files

| File | Purpose |
|------|---------|
| `dashboard/app.py` | Main dashboard entry point |
| `outputs/csv/final_sales_export_top_down.csv` | Your 18,590 row dataset |
| `.env` | Your Odoo credentials (secure, gitignored) |
| `README.md` | Full documentation |
| `IMPLEMENTATION_SUMMARY.md` | What was built |

## 🎯 Common Tasks

### Export Filtered Data
1. Apply filters in sidebar
2. Scroll to "Raw Data Explorer"
3. Click "📥 Download Filtered Data as CSV"

### Search for Specific Product
1. Go to "Product Analysis" page
2. Click "🔍 Product Search" tab
3. Enter product code

### View Top Salespeople
1. Go to "Sales Analysis" page
2. Adjust slider for number of salespeople
3. View chart and detailed table

## ⚠️ Troubleshooting

### Port Already in Use
```bash
streamlit run dashboard/app.py --server.port 8502
```

### Dashboard Shows "Data file not found"
```bash
# Run the ETL pipeline first
python -m src.etl.main_pipeline
```

### "Authentication failed"
Check your `.env` file credentials match your Odoo instance.

## 🎉 That's It!

Your dashboard is ready to use with existing data.

**Launch command:**
```bash
streamlit run dashboard/app.py
```

**Access at:** http://localhost:8501

Enjoy exploring your Odoo sales data! 📊✨
