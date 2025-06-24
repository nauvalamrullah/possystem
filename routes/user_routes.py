from flask import Blueprint, request, jsonify
import sqlite3

user_routes = Blueprint('user_routes', __name__)

@user_routes.route('/validate_user/<int:user_id>', methods=['POST'])
def validate_user(user_id):
    conn = sqlite3.connect("myappdb.db")
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET status='verified' WHERE id=?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        print("Error:", str(e))
        return jsonify({"success": False})
