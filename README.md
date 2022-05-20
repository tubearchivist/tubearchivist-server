# Tube Archivist Server
All code for www.tubearchivist.com.

## Tubearchivist
Flask API to render the html website. Build with Docker. API endpoints to:

### Listen for GitHub hooks to
- Create tasks for unstable testing images
- Create tasks for new releases
- Update Roadmap in Discord

### Listen for DockerHub hooks to
- Send notifications for new unstable builds to Discord
- Send nitifications for new release builds to Discord

## Builder
Standalone python script subscribed to Redis waiting for build commands.
