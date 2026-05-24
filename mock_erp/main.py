from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from uuid import uuid4
from datetime import datetime
import sqlite3

app = FastAPI(title="Mock Food ERP", description="For Ozai demo")

class OrderLineItem(BaseModel):
    product: str
    quantity: float
    unit: str
    notes: str | None = None

class OrderRequest(BaseModel):
    customer: str
    line_items: list[OrderLineItem]
    confidence: float
    source_email_id: str

class OrderResponse(BaseModel):
    order_id: str
    status: str
    created_at: datetime

@app.post("/api/orders", response_model=OrderResponse)
async def create_order(order: OrderRequest):
    order_id = f"ORD-{uuid4().hex[:8].upper()}"
    
    # Store in SQLite for dashboard
    conn = sqlite3.connect("orders.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer TEXT,
            items_json TEXT,
            confidence REAL,
            created_at TEXT
        )
    """)
    c.execute(
        "INSERT INTO orders VALUES (?, ?, ?, ?, ?)",
        (order_id, order.customer, order.json(), order.confidence, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    return OrderResponse(
        order_id=order_id,
        status="created",
        created_at=datetime.now()
    )

@app.get("/api/health")
async def health():
    return {"status": "ok"}

    
@app.get("/api/orders")
async def get_orders():
    conn = sqlite3.connect("orders.db")
    conn.row_factory = sqlite3.Row  # This makes rows accessible as dict-like objects
    c = conn.cursor()
    
    # Get column names
    c.execute("SELECT * FROM orders")
    columns = [description[0] for description in c.description]
    
    # Fetch all rows
    rows = c.fetchall()
    
    # Convert to list of dicts
    orders = []
    for row in rows:
        orders.append(dict(zip(columns, row)))
    
    conn.close()
    
    return {"status": "ok", "status_code": 200, "data": orders}