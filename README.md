![alt](https://github.com/steffenglock/Paperless-ngx-Export-/blob/main/screenshot.png)
# Paperless-ngx Export

A lightweight web interface for querying, filtering, and exporting document metadata from **Paperless-ngx**.

---

## Overview

**Paperless-ngx Export** connects to your existing **Paperless-ngx** instance through its API and provides a simple browser-based interface to:

- search and filter documents
- view results in a sortable table
- open documents directly in Paperless-ngx
- export filtered results as **CSV**

This container is intended for users who want a fast and practical way to extract structured document data from Paperless-ngx for reporting, review, or spreadsheet processing.

---

## Features

- connect to an existing **Paperless-ngx** instance using URL and API token
- automatic configuration prompt on first start
- filter by:
  - full-text search
  - correspondent
  - document type
  - tags
  - storage path
  - date range
- switch date filtering between:
  - **created**
  - **added**
- sortable table columns
- visible sort direction in the column header
- show or hide columns
- automatic truncation of long text with tooltip on hover
- clickable document title linking directly to the document in **Paperless-ngx**
- CSV export of the displayed results
- persistent configuration storage

---

## Displayed Fields

The table can display the following document metadata:

- Created
- Added
- Title
- Correspondent
- Tags
- Document type
- Storage path
- Document ID

---

## Notes

- The CSV export contains the visible text values only, not the HTML links.
- The application does not store documents itself.
- It only queries your existing **Paperless-ngx** instance via API.

---

## Quick Start with Docker

~~~bash
docker run -d \
  --name paperless-ngx-export \
  -p 5001:5001 \
  -v paperless_ngx_export_data:/data \
  steffenglock/paperless-ngx-export:latest
~~~

### Open in your browser

~~~text
http://YOUR-HOST-IP:5001
~~~

At first start, the web UI will ask for:

- your Paperless-ngx base URL
- your Paperless-ngx API token

---

## Portainer Stack

~~~yaml
version: "3.8"

services:
  paperless-ngx-export:
    image: steffenglock/paperless-ngx-export:latest
    container_name: paperless-ngx-export
    restart: unless-stopped
    ports:
      - "5001:5001"
    volumes:
      - paperless_ngx_export_data:/data

volumes:
  paperless_ngx_export_data:
~~~
