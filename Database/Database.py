from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Tạo kết nối đến cơ sở dữ liệu MySQL
engine = create_engine('mysql+pymysql://root@localhost/toram?charset=utf8mb4')## sua cai nay lai

# Tạo một session để thao tác với cơ sở dữ liệu
Session = sessionmaker(bind=engine)
session = Session()

# Định nghĩa một Base cho các lớp ánh xạ đối tượng
Base = declarative_base()

# Chạy hàm này để tạo các bảng nếu chưa tồn tại
Base.metadata.create_all(engine)
