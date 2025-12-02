# Docker Setup Guide

This guide explains how to run the manga scraper application using Docker Compose.

## Architecture

The application consists of three containers:
1. **MySQL** - Database server
2. **Reader** - FastAPI web application for reading manga (port 8888)
3. **Scraper** - FastAPI API service for scraping manga (port 8000)

## Prerequisites

- Docker
- Docker Compose

## Quick Start

1. **Set environment variables** (optional):
   Create a `.env` file in the project root with:
   ```env
   SECRET_KEY=your-secret-key-here
   DB_PASSWORD=pwd
   ```

2. **Build and start all services**:
   ```bash
   docker-compose up -d
   ```

3. **View logs**:
   ```bash
   # All services
   docker-compose logs -f

   # Specific service
   docker-compose logs -f reader
   docker-compose logs -f scraper
   docker-compose logs -f mysql
   ```

4. **Stop services**:
   ```bash
   docker-compose down
   ```

5. **Stop and remove volumes** (WARNING: This deletes all data):
   ```bash
   docker-compose down -v
   ```

## Services

### MySQL Database
- **Port**: 3306
- **Database**: manga_reader
- **Username**: root
- **Password**: pwd (configurable via environment variable)
- **Data**: Persisted in `mysql_data` volume

### Reader Service
- **Port**: 8888
- **URL**: http://localhost:8888
- **Environment Variables**:
  - `DB_HOST`: Database host (default: mysql)
  - `DB_PORT`: Database port (default: 3306)
  - `DB_USERNAME`: Database username (default: root)
  - `DB_PASSWORD`: Database password (default: pwd)
  - `DB_NAME`: Database name (default: manga_reader)
  - `RUN_MODE`: Run mode (default: prod)
  - `LOCAL_FOLDER`: Path to store comics (default: /app/local_comics)
  - `SECRET_KEY`: Secret key for sessions

### Scraper API Service
- **Port**: 8000
- **URL**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Environment Variables**: Same as reader service, plus:
  - `SCRAPER_API_PORT`: API port (default: 8000)

## Scraper API Endpoints

### Health Check
```bash
GET /health
```

### Create Comic
```bash
POST /comics/create
Content-Type: application/json

{
  "comic_name": "My Manga",
  "comic_url": "https://mangafire.to/manga/my-manga/",
  "scanlation_group": "mangafire_to",
  "comic_type": "manga",
  "status": "ongoing",
  "update_frequency": "monthly",
  "tags": ["action", "adventure"]
}
```

### Validate URL
```bash
POST /comics/validate-url
Content-Type: application/json

{
  "url": "https://mangafire.to/manga/my-manga/",
  "scanlation_group": "mangafire_to"
}
```

### Refresh Comic
```bash
POST /comics/{comic_id}/refresh
```

### Scan All Comics
```bash
POST /scan/all
```

### Scan Specific Scanlation Group
```bash
POST /scan/{scanlation_group}
# scanlation_group: "mangafire_to" or "asura_scans"
```

## Volumes

- `mysql_data`: MySQL database data
- `local_comics`: Shared volume for downloaded manga chapters (accessible by both reader and scraper)

## Network

All services are connected to a bridge network (`manga_network`) allowing them to communicate using service names (e.g., `mysql`, `reader`, `scraper`).

## Troubleshooting

### Database Connection Issues
- Ensure MySQL container is healthy: `docker-compose ps`
- Check MySQL logs: `docker-compose logs mysql`
- Verify environment variables are set correctly

### Port Conflicts
- If ports 3306, 8000, or 8888 are already in use, modify the port mappings in `docker-compose.yml`

### Permission Issues
- Ensure Docker has proper permissions
- Check volume permissions if accessing `local_comics` from host

### Build Issues
- Clear Docker cache: `docker-compose build --no-cache`
- Ensure all dependencies are in `requirements.txt`

## Development

To rebuild containers after code changes:
```bash
docker-compose build
docker-compose up -d
```

To rebuild specific service:
```bash
docker-compose build reader
docker-compose up -d reader
```

