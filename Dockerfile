FROM python:3.9

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

ENV LAKEVIEW_VERSION="0.1.0"
ENTRYPOINT ["python", "server.py"]
