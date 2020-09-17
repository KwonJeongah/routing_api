# Routing
다중 경유지와 차량의 용량 및 수거할 폐기물의 부피를 고려한 경로 탐색 API입니다.

## 개발 환경    
* 기본환경    
    + OS: WIndow 10    
    + Server    
        - Python3
        - Django 3.0.3
        - Sqlite3
      
## 빌드 및 실행하기    
**터미널 환경** 
    + Git, Python, Django는 설치되어 있다고 가정
'''    
  $ git clone https://github.com/dsalice/routing_api.git
  $ python manage.py
'''

**접속 Base URL** http://localhost:8000 

**경로 좌푯값 확인*** http://localhost:8000/route/


## 기능 요구사항    
* 데이터베이스에 저장된 경유지 및 차량 데이터로 차량의 폐기물 수거 경로 탐색하는 API 개발
* 출력 예시

![routing_api_출력예시](https://user-images.githubusercontent.com/37493709/93412520-473c9b00-f8d8-11ea-9f07-5dbb291104f9.jpg)



  






