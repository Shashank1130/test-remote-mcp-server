from fastmcp import FastMCP
import os
import aiosqlite
import tempfile

# Use temporary directory which should be writable
TEMP_DIR = tempfile.gettempdir()
DB_PATH = os.path.join(TEMP_DIR, "expenses.db")
CATEGORIES_PATH = os.path.join(os.path.dirname(__file__), "categories.json")

print(f"Database path: {DB_PATH}")

mcp = FastMCP("ExpenseTracker")


def init_db():
    """Initialize the database."""
    try:
        import sqlite3

        with sqlite3.connect(DB_PATH) as c:
            c.execute("PRAGMA journal_mode=WAL")

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

            # Test write access
            c.execute(
                "INSERT OR IGNORE INTO expenses(date, amount, category) VALUES ('2000-01-01', 0, 'test')"
            )
            c.execute("DELETE FROM expenses WHERE category = 'test'")

            print("Database initialized successfully with write access")

    except Exception as e:
        print(f"Database initialization error: {e}")
        raise


# Initialize database synchronously at module load
init_db()


@mcp.tool()
async def add_expense(
    date,
    amount,
    category,
    subcategory="",
    note=""
):
    """Add a new expense entry to the database."""

    try:
        async with aiosqlite.connect(DB_PATH) as c:

            cur = await c.execute(
                """
                INSERT INTO expenses(
                    date,
                    amount,
                    category,
                    subcategory,
                    note
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (date, amount, category, subcategory, note)
            )

            expense_id = cur.lastrowid

            await c.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense added successfully"
            }

    except Exception as e:
        if "readonly" in str(e).lower():
            return {
                "status": "error",
                "message": "Database is in read-only mode. Check file permissions."
            }

        return {
            "status": "error",
            "message": f"Database error: {str(e)}"
        }


@mcp.tool()
async def edit_expense(
    expense_id: int,
    date: str = None,
    amount: float = None,
    category: str = None,
    subcategory: str = None,
    note: str = None
):
    """Edit an existing expense entry."""

    try:
        async with aiosqlite.connect(DB_PATH) as c:

            cur = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE id = ?
                """,
                (expense_id,)
            )

            row = await cur.fetchone()

            if not row:
                return {
                    "status": "error",
                    "message": f"Expense with id {expense_id} not found"
                }

            expense = {
                "id": row[0],
                "date": row[1],
                "amount": row[2],
                "category": row[3],
                "subcategory": row[4],
                "note": row[5]
            }

            await c.execute(
                """
                UPDATE expenses
                SET date = ?,
                    amount = ?,
                    category = ?,
                    subcategory = ?,
                    note = ?
                WHERE id = ?
                """,
                (
                    date if date is not None else expense["date"],
                    amount if amount is not None else expense["amount"],
                    category if category is not None else expense["category"],
                    subcategory if subcategory is not None else expense["subcategory"],
                    note if note is not None else expense["note"],
                    expense_id
                )
            )

            await c.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense updated successfully"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error updating expense: {str(e)}"
        }


@mcp.tool()
async def delete_expense(expense_id: int):
    """Delete an expense entry by ID."""

    try:
        async with aiosqlite.connect(DB_PATH) as c:

            cur = await c.execute(
                "SELECT id FROM expenses WHERE id = ?",
                (expense_id,)
            )

            if not await cur.fetchone():
                return {
                    "status": "error",
                    "message": f"Expense with id {expense_id} not found"
                }

            await c.execute(
                "DELETE FROM expenses WHERE id = ?",
                (expense_id,)
            )

            await c.commit()

            return {
                "status": "success",
                "id": expense_id,
                "message": "Expense deleted successfully"
            }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error deleting expense: {str(e)}"
        }


@mcp.tool()
async def list_expenses(start_date, end_date):
    """List expense entries within an inclusive date range."""

    try:
        async with aiosqlite.connect(DB_PATH) as c:

            cur = await c.execute(
                """
                SELECT id, date, amount, category, subcategory, note
                FROM expenses
                WHERE date BETWEEN ? AND ?
                ORDER BY date DESC, id DESC
                """,
                (start_date, end_date)
            )

            cols = [d[0] for d in cur.description]

            return [
                dict(zip(cols, row))
                for row in await cur.fetchall()
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error listing expenses: {str(e)}"
        }


@mcp.tool()
async def summarize(start_date, end_date, category=None):
    """Summarize expenses by category within an inclusive date range."""

    try:
        async with aiosqlite.connect(DB_PATH) as c:

            query = """
                SELECT
                    category,
                    SUM(amount) AS total_amount,
                    COUNT(*) AS count
                FROM expenses
                WHERE date BETWEEN ? AND ?
            """

            params = [start_date, end_date]

            if category:
                query += " AND category = ?"
                params.append(category)

            query += """
                GROUP BY category
                ORDER BY total_amount DESC
            """

            cur = await c.execute(query, params)

            cols = [d[0] for d in cur.description]

            return [
                dict(zip(cols, row))
                for row in await cur.fetchall()
            ]

    except Exception as e:
        return {
            "status": "error",
            "message": f"Error summarizing expenses: {str(e)}"
        }


@mcp.resource(
    "expense:///categories",
    mime_type="application/json"
)
def categories():

    try:
        default_categories = {
            "categories": [
                "Food & Dining",
                "Transportation",
                "Shopping",
                "Entertainment",
                "Bills & Utilities",
                "Healthcare",
                "Travel",
                "Education",
                "Business",
                "Other"
            ]
        }

        try:
            with open(
                CATEGORIES_PATH,
                "r",
                encoding="utf-8"
            ) as f:
                return f.read()

        except FileNotFoundError:
            import json
            return json.dumps(default_categories, indent=2)

    except Exception as e:
        return f'{{"error": "Could not load categories: {str(e)}"}}'


if __name__ == "__main__":
    mcp.run(
        transport="http",
        host="0.0.0.0",
        port=8000
    )

