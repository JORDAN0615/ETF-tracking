import sqlite3
import os

DB_PATH = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "etf_tracking.db"))

def get_latest_holdings():
    """
    Fetch the most recent portfolio snapshot from the my_holdings table.
    Returns a dict containing trade_date, holdings list, and total_value.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Find the latest trade date
    cursor.execute("SELECT trade_date FROM my_holdings ORDER BY trade_date DESC LIMIT 1")
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    latest_date = row['trade_date']

    # Fetch all holdings for that date
    cursor.execute("SELECT ticker, name, shares, close_price, market_value FROM my_holdings WHERE trade_date = ?", (latest_date,))
    rows = cursor.fetchall()
    
    holdings = []
    total_value = 0
    for r in rows:
        market_val = r['market_value']
        holdings.append({
            "ticker": r['ticker'],
            "name": r['name'],
            "shares": r['shares'],
            "close_price": r['close_price'],
            "market_value": market_val
        })
        total_value += market_val

    conn.close()
    
    return {
        "trade_date": latest_date,
        "holdings": holdings,
        "total_value": total_value
    }
