# Harbor WMS

Warehouse management with **Django 5** and **PostgreSQL**.

## Tables

| Table | Purpose |
| --- | --- |
| `product` | Master item: `name`, `unit` |
| `warehouse` | `code`, `name`, `location` |
| `stock` | Available quantity of a product in a warehouse |
| `stock_ledger` | Append-only history of stock movements (write + read, never edit) |
| `inventory_transaction` | Stock in, stock out, transfer, and adjustment events |
| `audit` | Append-only user activity history |
| `auth_user` | Django user accounts |

Stock quantity changes only when an inventory transaction is **posted**. Posting writes ledger rows and updates `stock`. Ledger and audit rows cannot be updated or deleted.

## Setup

```bash
cd wms
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

```bash
psql postgres -c "CREATE USER wms WITH PASSWORD 'wms';"
psql postgres -c "CREATE DATABASE wms OWNER wms;"
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Open http://127.0.0.1:8000 — `admin / admin123` or `operator / operator123`.
