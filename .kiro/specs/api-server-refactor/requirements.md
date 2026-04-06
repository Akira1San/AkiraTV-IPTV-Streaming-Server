# Requirements Document

## Introduction

This document specifies the requirements for refactoring the AkiraTV API server from a monolithic 2,073-line file into a modular FastAPI router-based architecture. The refactoring aims to improve maintainability, testability, and enable parallel development while maintaining complete backward compatibility with existing functionality.

## Glossary

- **API_Server**: The main FastAPI application instance that serves HTTP endpoints
- **Router**: A FastAPI APIRouter instance that groups related endpoints
- **Route_Module**: A Python file containing a Router and its endpoint handlers
- **Pydantic_Model**: A data validation model using the Pydantic library
- **Core_API**: The existing CoreAPI interface that the API server wraps
- **Endpoint**: An HTTP route handler function (GET, POST, PATCH, DELETE, etc.)
- **Backward_Compatibility**: Ensuring existing imports and launch methods continue to work
- **Static_Files**: User assets (covers, logos) and web UI files served by the server

## Requirements

### Requirement 1: Extract Pydantic Models

**User Story:** As a developer, I want all Pydantic models in a separate file, so that I can reuse them across route modules without circular dependencies.

#### Acceptance Criteria

1. THE API_Server SHALL extract all Pydantic models into a dedicated models.py file
2. WHEN models.py is created, THE API_Server SHALL include all request and response models (PlayNowRequest, ConfigUpdateRequest, ChannelUpdateRequest, FastScheduleRequest, Response)
3. THE API_Server SHALL maintain the same model structure and validation rules after extraction
4. WHEN route modules import models, THE API_Server SHALL not create circular import dependencies

### Requirement 2: Create Modular Route Structure

**User Story:** As a developer, I want the API organized into logical route modules, so that I can work on specific features without navigating a 2,000+ line file.

#### Acceptance Criteria

1. THE API_Server SHALL create a routes/ directory containing separate route modules
2. THE API_Server SHALL create lifecycle.py for engine start/stop/restart/status endpoints
3. THE API_Server SHALL create channels.py for channel management endpoints (get, add, enable, disable, update, delete, URLs, play, stop, restart)
4. THE API_Server SHALL create config.py for configuration endpoints (get, update, save, defaults, file access)
5. THE API_Server SHALL create library.py for library scan and statistics endpoints
6. THE API_Server SHALL create monitoring.py for stats, viewers, and logs endpoints
7. THE API_Server SHALL create guide.py for TV guide endpoints (current, weekly, date-specific)
8. THE API_Server SHALL create playlist.py for playlist management endpoints (create, get videos, play selected)
9. THE API_Server SHALL create standby.py for standby video creation endpoints
10. THE API_Server SHALL create wizard.py for collection wizard endpoints (log, scan folder, check collection, create collection, create schedule)
11. THE API_Server SHALL create fast_scheduler.py for fast scheduling endpoints (load collections, generate, info, current, upcoming, save/load checkpoint, status)
12. THE API_Server SHALL create vod.py for VOD library endpoints (get library, video details)
13. THE API_Server SHALL create websocket.py for WebSocket connection handling
14. THE API_Server SHALL create routes/__init__.py to export all routers

### Requirement 3: Refactor Main API Server File

**User Story:** As a developer, I want the main api_server.py file reduced to ~200 lines, so that the application structure is immediately clear.

#### Acceptance Criteria

1. WHEN the refactoring is complete, THE API_Server SHALL have a main api_server.py file of approximately 200 lines or less
2. THE API_Server SHALL include only FastAPI app initialization, middleware setup, static file mounting, router registration, and startup/shutdown handlers in the main file
3. THE API_Server SHALL move all endpoint handler functions to appropriate route modules
4. THE API_Server SHALL move all helper functions (time_to_minutes, get_schedule_for_date, get_video_duration) to appropriate route modules or utility files
5. THE API_Server SHALL preserve the get_core_api() lazy initialization function in the main file or a shared utility module

### Requirement 4: Maintain Backward Compatibility

**User Story:** As a system operator, I want existing launch methods and imports to continue working, so that I don't need to update deployment scripts or external integrations.

#### Acceptance Criteria

1. WHEN the refactoring is complete, THE API_Server SHALL support the existing launch command: `uvicorn akiratv.api_server:app --reload --port 8000`
2. THE API_Server SHALL support the existing direct execution: `python -m akiratv.api_server`
3. THE API_Server SHALL maintain the same API endpoint paths and HTTP methods
4. THE API_Server SHALL maintain the same request and response formats for all endpoints
5. THE API_Server SHALL preserve all existing middleware (CORS, static files)
6. THE API_Server SHALL preserve the global `app` variable export from api_server.py

### Requirement 5: Preserve Shared State and Dependencies

**User Story:** As a developer, I want shared state and dependencies properly managed, so that route modules can access the Core API and WebSocket connections.

#### Acceptance Criteria

1. THE API_Server SHALL provide access to the Core_API instance from all route modules
2. THE API_Server SHALL provide access to the active_connections list for WebSocket broadcasting from route modules
3. THE API_Server SHALL provide access to the fast_schedulers cache from the fast scheduler route module
4. WHEN route modules need shared state, THE API_Server SHALL use FastAPI dependency injection or shared utility modules
5. THE API_Server SHALL not create circular dependencies between route modules

### Requirement 6: Organize Helper Functions

**User Story:** As a developer, I want helper functions organized logically, so that I can find and reuse utility code easily.

#### Acceptance Criteria

1. WHEN helper functions are specific to a route module, THE API_Server SHALL place them in that route module
2. WHEN helper functions are shared across multiple modules, THE API_Server SHALL place them in a shared utilities module
3. THE API_Server SHALL move time_to_minutes() to the guide route module or a shared utilities module
4. THE API_Server SHALL move get_schedule_for_date() to the guide route module or a shared utilities module
5. THE API_Server SHALL move get_video_duration() to the wizard route module or a shared utilities module
6. THE API_Server SHALL move broadcast_event() to the websocket route module or a shared utilities module

### Requirement 7: Maintain Testing Capability

**User Story:** As a developer, I want the refactored code to be more testable, so that I can write unit tests for individual route modules.

#### Acceptance Criteria

1. WHEN route modules are created, THE API_Server SHALL ensure each module can be imported independently
2. THE API_Server SHALL ensure route modules do not have side effects on import
3. THE API_Server SHALL use dependency injection for Core_API access to enable test mocking
4. THE API_Server SHALL structure route modules so individual endpoints can be tested without starting the full server

### Requirement 8: Preserve Documentation and Metadata

**User Story:** As an API consumer, I want the API documentation to remain accurate, so that I can understand available endpoints.

#### Acceptance Criteria

1. THE API_Server SHALL preserve all endpoint docstrings after refactoring
2. THE API_Server SHALL preserve all Pydantic model descriptions and field metadata
3. THE API_Server SHALL preserve the FastAPI app title, description, and version
4. WHEN accessing /docs, THE API_Server SHALL display the same Swagger documentation structure
5. THE API_Server SHALL preserve response_model declarations for all endpoints

### Requirement 9: Handle Static Files and Startup Logic

**User Story:** As a system operator, I want static file serving and startup logic to work correctly, so that the web UI and assets are accessible.

#### Acceptance Criteria

1. THE API_Server SHALL preserve static file mounting for /static and /user directories
2. THE API_Server SHALL preserve the root endpoint (/) that serves index.html
3. THE API_Server SHALL preserve the /viewer endpoint that serves viewer.html
4. THE API_Server SHALL preserve the /health health check endpoint
5. THE API_Server SHALL preserve startup and shutdown event handlers
6. THE API_Server SHALL preserve the main entry point with uvicorn configuration

### Requirement 10: Maintain Error Handling Patterns

**User Story:** As an API consumer, I want consistent error responses, so that I can handle errors predictably.

#### Acceptance Criteria

1. THE API_Server SHALL preserve HTTPException usage for error responses
2. THE API_Server SHALL preserve error status codes (400, 404, 500, 503, etc.)
3. THE API_Server SHALL preserve error message formats
4. WHEN route modules raise errors, THE API_Server SHALL use the same error handling patterns as the original implementation
5. THE API_Server SHALL preserve try-except blocks and error logging
