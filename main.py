import os
import sqlite3
from fastmcp import FastMCP

DB_PATH = os.path.join(os.path.dirname(__file__), "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

mcp = FastMCP(name="ExpenseTracker")


# -----------------------------
# Database Initialization
# -----------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS expenses(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                amount REAL NOT NULL,
                category TEXT NOT NULL,
                subcategory TEXT DEFAULT '',
                note TEXT DEFAULT ''
            )
        """)


init_db()


# -----------------------------
# Add Expense
# -----------------------------
@mcp.tool()
def add_expense(
    date: str,
    amount: float,
    category: str,
    subcategory: str = "",
    note: str = ""
):
    """Add a new expense entry."""

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            INSERT INTO expenses
            (date, amount, category, subcategory, note)
            VALUES (?, ?, ?, ?, ?)
            """,
            (date, amount, category, subcategory, note)
        )

        return {
            "status": "ok",
            "id": cur.lastrowid
        }


# -----------------------------
# List Expenses
# -----------------------------
@mcp.tool()
def list_expenses(start_date: str, end_date: str):
    """List expenses within an inclusive date range."""

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            """
            SELECT id, date, amount, category, subcategory, note
            FROM expenses
            WHERE date BETWEEN ? AND ?
            ORDER BY date ASC, id ASC
            """,
            (start_date, end_date)
        )

        cols = [d[0] for d in cur.description]

        return [
            dict(zip(cols, row))
            for row in cur.fetchall()
        ]


# -----------------------------
# Edit Expense
# -----------------------------
@mcp.tool()
def edit_expense(
    expense_id: int,
    date: str = None,
    amount: float = None,
    category: str = None,
    subcategory: str = None,
    note: str = None
):
    """Edit an existing expense."""

    fields = []
    values = []

    if date is not None:
        fields.append("date = ?")
        values.append(date)

    if amount is not None:
        fields.append("amount = ?")
        values.append(amount)

    if category is not None:
        fields.append("category = ?")
        values.append(category)

    if subcategory is not None:
        fields.append("subcategory = ?")
        values.append(subcategory)

    if note is not None:
        fields.append("note = ?")
        values.append(note)

    if not fields:
        return {
            "status": "error",
            "message": "No fields supplied for update"
        }

    values.append(expense_id)

    query = f"""
        UPDATE expenses
        SET {', '.join(fields)}
        WHERE id = ?
    """

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(query, values)

        if cur.rowcount == 0:
            return {
                "status": "error",
                "message": f"Expense ID {expense_id} not found"
            }

        return {
            "status": "ok",
            "message": f"Expense ID {expense_id} updated"
        }


# -----------------------------
# Delete Expense
# -----------------------------
@mcp.tool()
def delete_expense(expense_id: int):
    """Delete an expense by ID."""

    with sqlite3.connect(DB_PATH) as c:
        cur = c.execute(
            "DELETE FROM expenses WHERE id = ?",
            (expense_id,)
        )

        if cur.rowcount == 0:
            return {
                "status": "error",
                "message": f"Expense ID {expense_id} not found"
            }

        return {
            "status": "ok",
            "message": f"Expense ID {expense_id} deleted"
        }


# -----------------------------
# Summarize Expenses
# -----------------------------
@mcp.tool()
def summarize(
    start_date: str,
    end_date: str,
    category: str = None
):
    """Summarize expenses by category."""

    with sqlite3.connect(DB_PATH) as c:

        query = """
            SELECT category,
                   SUM(amount) AS total_amount
            FROM expenses
            WHERE date BETWEEN ? AND ?
        """

        params = [start_date, end_date]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += """
            GROUP BY category
            ORDER BY category ASC
        """

        cur = c.execute(query, params)

        cols = [d[0] for d in cur.description]

        return [
            dict(zip(cols, row))
            for row in cur.fetchall()
        ]


# -----------------------------
# Categories Resource
# -----------------------------
@mcp.resource(
    "expense://categories",
    mime_type="application/json"
)
def categories():
    """Available expense categories."""

    with open(CATEGORIES_PATH,
        "r",
        encoding="utf-8"
    ) as f:
        return f.read()


# -----------------------------
# Run MCP Server
# -----------------------------
if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8080)