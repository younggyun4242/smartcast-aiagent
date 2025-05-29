from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json

# 데이터베이스 연결
engine = create_engine("sqlite:///aiagent.db")
Session = sessionmaker(bind=engine)
session = Session()

# 모든 레코드 조회
try:
    # 직접 SQL 실행
    result = engine.execute("SELECT * FROM receipt_records")
    
    # 결과 출력
    for row in result:
        print("\n--- 레코드 ---")
        for column, value in row.items():
            print(f"{column}: {value}")
            
except Exception as e:
    print(f"오류 발생: {e}")
finally:
    session.close() 