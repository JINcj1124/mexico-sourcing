"""数据库初始化脚本"""
import sys
sys.path.insert(0, ".")

from backend.models.database import init_db

if __name__ == "__main__":
    init_db()
    print("✅ Database initialized successfully")
    print(f"   Path: backend/../data/sourcing.db")
