FROM nginx
COPY test.html /usr/share/nginx/html/index.html


FROM python:latest

COPY test.py ./

RUN pip install numpy matplotlib

CMD ["python","./test.py"]
