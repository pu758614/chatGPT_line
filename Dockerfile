# 使用Python 3.9作為基礎映像
FROM python:3.9

# 設置工作目錄
WORKDIR /src

# 複製本地文件到容器中
COPY src/requirements.txt .

# 安裝Python依賴庫
RUN pip install -r requirements.txt

# 複製整個目錄到容器中
COPY . .