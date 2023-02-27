FROM python:3.8

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

RUN rm requirements.txt

COPY ./ .

CMD ["python", "app.py"]