FROM python:3.8

# Setup lakeview user
WORKDIR /home/lakeview/app
RUN useradd lakeview && chown -R lakeview:lakeview /home/lakeview
USER lakeview

# Setup dependencies
COPY requirements.txt ./
RUN pip install -r requirements.txt
# Copy the code, templates, assets, etc.
COPY . .

EXPOSE 5000

ENTRYPOINT ["python", "server.py"]
