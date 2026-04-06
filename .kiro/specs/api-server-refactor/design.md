# Design Document: API Server Refactoring

## Overview

This design document describes the refactoring of the AkiraTV API server from a monolithic 2,073-line file into a modular FastAPI router-based architecture. The refactoring will split the codebase into 14 files organized by functional domain while maintaining complete backward compatibility.

The refactored architecture will:
- Reduce the main api_server.py from 2,073 lines to ~200 lines
- Organize 50+ endpoints into 12 logical route modules
- Extract 5 Pydantic models into a dedicated models.py file
- Enable parallel development by multiple developers
- Improve testability through modular design
- Maintain all existing functionality and API contracts

## Architecture

### Current Architecture

```
akiratv/
└── api_server.py (2,073 lines)
    ├── Pydantic Models (5 models)
    ├── FastAPI App Setup
    ├── Middleware Configuration
    ├── Static File Mounting
    ├── Lifecycle Endpoints (4 endpoints)
    ├── Channel Endpoints (15 endpoints)
    ├── Configuration Endpoints (4 endpoints)
    ├── Library Endpoints (2 endpoints)
    ├── Monitoring Endpoints (4 endpoints)
    ├── Guide Endpoints (3 endpoints)
    ├── Playlist Endpoints (3 endpoints)
    ├── Standby Endpoints (1 endpoint)
    ├── Wizard Endpoints (5 endpoints)
    ├── Fast Scheduler Endpoints (10 endpoints)
    ├── VOD Endpoints (2 endpoints)
    ├── WebSocket Handler (1 endpoint)
    ├── Health Check (1 endpoint)
    ├── Helper Functions (5 functions)
    └── Main Entry Point
```

### Target Architecture

```
akiratv/
├── api_server.py (~200 lines)
│   ├── FastAPI App Initialization
│   ├── Middleware Setup (CORS)
│   ├── Static File Mounting (/static, /user)
│   ├── Router Registration (12 routers)
│   ├── Root Endpoints (/, /viewer, /health)
│   ├── Startup/Shutdown Handlers
│   └── Main Entry Point
│
├── models.py (~100 lines)
│   ├── PlayNowRequest
│   ├── ConfigUpdateRequest
│   ├── ChannelUpdateRequest
│   ├── FastScheduleRequest
│   └── Response
│
└── routes/
    ├── __init__.py
    │   └── Export all routers
    │
    ├── lifecycle.py (~80 lines)
    │   ├── POST /api/start
    │   ├── POST /api/stop
    │   ├── POST /api/restart
    │   └── GET /api/status
    │
    ├── channels.py (~400 lines)
    │   ├── GET /api/channels
    │   ├── POST /api/channels
    │   ├── GET /api/channels/urls
    │   ├── GET /api/channels/{channel}
    │   ├── POST /api/channels/{channel}/enable
    │   ├── POST /api/channels/{channel}/disable
    │   ├── PATCH /api/channels/{channel}
    │   ├── GET /api/channels/{channel}/url
    │   ├── POST /api/channels/{channel}/play
    │   ├── POST /api/channels/{channel}/stop
    │   ├── POST /api/channels/{channel}/stop-worker
    │   ├── POST /api/channels/{channel}/restart
    │   ├── POST /api/channels/{channel}/start
    │   ├── POST /api/channels/{channel}/reload-schedule
    │   └── DELETE /api/channels/{channel}
    │
    ├── config.py (~120 lines)
    │   ├── GET /api/config
    │   ├── PATCH /api/config
    │   ├── POST /api/config/save
    │   ├── GET /api/config/defaults
    │   └── GET /api/config/file
    │
    ├── library.py (~60 lines)
    │   ├── GET /api/library/stats
    │   └── POST /api/library/scan
    │
    ├── monitoring.py (~120 lines)
    │   ├── GET /api/stats
    │   ├── GET /api/viewers
    │   ├── GET /api/viewers/detail
    │   ├── GET /api/viewers/channel/{channel_name}
    │   └── GET /api/logs
    │
    ├── guide.py (~350 lines)
    │   ├── GET /api/guide
    │   ├── GET /api/guide/weekly
    │   ├── GET /api/guide/date/{date_str}
    │   ├── Helper: time_to_minutes()
    │   └── Helper: get_schedule_for_date()
    │
    ├── playlist.py (~150 lines)
    │   ├── POST /api/playlist/create
    │   ├── GET /api/playlist/videos
    │   └── POST /api/playlist/play-selected
    │
    ├── standby.py (~100 lines)
    │   └── POST /api/standby/create
    │
    ├── wizard.py (~350 lines)
    │   ├── POST /api/wizard/log
    │   ├── POST /api/wizard/scan-folder
    │   ├── POST /api/wizard/collection/check
    │   ├── POST /api/wizard/collection/create
    │   ├── POST /api/wizard/schedule/create
    │   └── Helper: get_video_duration()
    │
    ├── fast_scheduler.py (~300 lines)
    │   ├── POST /api/fast-schedule/{channel}/load-collections
    │   ├── POST /api/fast-schedule/{channel}/generate
    │   ├── GET /api/fast-schedule/{channel}/info
    │   ├── GET /api/fast-schedule/{channel}/current
    │   ├── GET /api/fast-schedule/{channel}/upcoming
    │   ├── POST /api/fast-schedule/{channel}/save-checkpoint
    │   ├── POST /api/fast-schedule/{channel}/load-checkpoint
    │   ├── GET /api/fast-schedule/collections
    │   ├── GET /api/fast-schedule/{channel}/status
    │   └── Helper: get_fast_scheduler()
    │
    ├── vod.py (~80 lines)
    │   ├── GET /api/vod/library
    │   └── GET /api/vod/video/{video_id}
    │
    └── websocket.py (~80 lines)
        ├── WebSocket /ws
        ├── Helper: broadcast_event()
        └── active_connections management
```

## Components and Interfaces

### 1. Main Application (api_server.py)

**Responsibilities:**
- Initialize FastAPI application with metadata
- Configure CORS middleware
- Mount static file directories
- Register all route modules
- Provide shared dependencies (Core API access)
- Handle startup/shutdown events
- Serve root endpoints (/, /viewer, /health)

**Key Functions:**
```python
def get_core_api() -> CoreAPI:
    """Lazy initialization of Core API instance"""
    # Returns singleton CoreAPI instance
    
app = FastAPI(title="AkiraTV API", ...)
# Configure middleware
# Mount static files
# Include routers from all route modules
```

### 2. Models Module (models.py)

**Responsibilities:**
- Define all Pydantic request models
- Define all Pydantic response models
- Provide data validation and serialization

**Models:**
```python
class PlayNowRequest(BaseModel):
    video_path: str
    
class ConfigUpdateRequest(BaseModel):
    updates: Dict[str, Any]
    
class ChannelUpdateRequest(BaseModel):
    enabled: Optional[bool]
    transcoding: Optional[str]
    subtitles: Optional[str]
    type: Optional[str]
    
class FastScheduleRequest(BaseModel):
    collections: Optional[List[str]]
    start_time: Optional[str]
    schedule_hours: Optional[int]
    bumper_frequency: Optional[int]
    trailer_probability: Optional[float]
    
class Response(BaseModel):
    success: bool
    message: Optional[str]
    error: Optional[str]
    data: Optional[Any]
```

### 3. Route Modules (routes/*.py)

Each route module follows this pattern:

**Structure:**
```python
from fastapi import APIRouter, HTTPException, Depends
from ..models import Response, [OtherModels]
from ..core_api import get_api

router = APIRouter(prefix="/api/[domain]", tags=["[Domain]"])

# Dependency for Core API access
def get_core_api():
    return get_api()

# Endpoint handlers
@router.get("/endpoint")
def handler(api = Depends(get_core_api)):
    # Implementation
    pass
```

**Shared Dependencies:**
- Core API access via dependency injection
- Pydantic models from models.py
- HTTPException for error handling

### 4. Lifecycle Routes (routes/lifecycle.py)

**Endpoints:**
- `POST /api/start` - Start the AkiraTV engine
- `POST /api/stop` - Stop the AkiraTV engine
- `POST /api/restart` - Restart the AkiraTV engine
- `GET /api/status` - Get engine status (running, uptime, stats)

**Dependencies:**
- Core API for engine control

### 5. Channel Routes (routes/channels.py)

**Endpoints:**
- `GET /api/channels` - List all channels
- `POST /api/channels` - Add new channel
- `GET /api/channels/urls` - Get streaming URLs for all channels
- `GET /api/channels/{channel}` - Get specific channel status
- `POST /api/channels/{channel}/enable` - Enable channel
- `POST /api/channels/{channel}/disable` - Disable channel
- `PATCH /api/channels/{channel}` - Update channel settings
- `GET /api/channels/{channel}/url` - Get channel streaming URL
- `POST /api/channels/{channel}/play` - Play video on VOD channel
- `POST /api/channels/{channel}/stop` - Stop current video
- `POST /api/channels/{channel}/stop-worker` - Stop channel worker
- `POST /api/channels/{channel}/restart` - Restart channel
- `POST /api/channels/{channel}/start` - Start channel worker
- `POST /api/channels/{channel}/reload-schedule` - Reload channel schedule
- `DELETE /api/channels/{channel}` - Delete channel

**Dependencies:**
- Core API for channel management
- ChannelUpdateRequest model
- PlayNowRequest model
- Socket library for IP detection

### 6. Configuration Routes (routes/config.py)

**Endpoints:**
- `GET /api/config` - Get full configuration
- `PATCH /api/config` - Update configuration
- `POST /api/config/save` - Save configuration to disk
- `GET /api/config/defaults` - Get default configuration
- `GET /api/config/file` - Get config file path

**Dependencies:**
- Core API for config management
- ConfigUpdateRequest model
- Config class for defaults

### 7. Library Routes (routes/library.py)

**Endpoints:**
- `GET /api/library/stats` - Get library statistics
- `POST /api/library/scan` - Trigger library scan

**Dependencies:**
- Core API for library operations

### 8. Monitoring Routes (routes/monitoring.py)

**Endpoints:**
- `GET /api/stats` - Get live statistics
- `GET /api/viewers` - Get active viewer count
- `GET /api/viewers/detail` - Get detailed viewer information
- `GET /api/viewers/channel/{channel_name}` - Get channel-specific viewers
- `GET /api/logs` - Get recent log entries

**Dependencies:**
- Core API for stats and logs
- viewer_tracker module for viewer information

### 9. Guide Routes (routes/guide.py)

**Endpoints:**
- `GET /api/guide` - Get current TV guide for all channels
- `GET /api/guide/weekly` - Get full weekly TV guide
- `GET /api/guide/date/{date_str}` - Get guide for specific date

**Helper Functions:**
```python
def time_to_minutes(time_str: str) -> int:
    """Convert HH:MM:SS to minutes since midnight"""
    
def get_schedule_for_date(schedule_data: dict, date_str: str, day_name: str) -> list:
    """Get schedule entries for a specific date"""
```

**Dependencies:**
- Core API for channel information
- Schedule JSON files from user/schedules/
- datetime for date handling

### 10. Playlist Routes (routes/playlist.py)

**Endpoints:**
- `POST /api/playlist/create` - Create playlist from video folder
- `GET /api/playlist/videos` - Get videos from current playlist
- `POST /api/playlist/play-selected` - Play selected video from playlist

**Dependencies:**
- Core API for playback control
- Filesystem access for playlist files

### 11. Standby Routes (routes/standby.py)

**Endpoints:**
- `POST /api/standby/create` - Create standby loop videos

**Dependencies:**
- standby module for video creation
- video_inventory.json for resolution detection

### 12. Wizard Routes (routes/wizard.py)

**Endpoints:**
- `POST /api/wizard/log` - Log wizard events
- `POST /api/wizard/scan-folder` - Scan folder for videos
- `POST /api/wizard/collection/check` - Check if collection exists
- `POST /api/wizard/collection/create` - Create collection from wizard
- `POST /api/wizard/schedule/create` - Create schedule from wizard

**Helper Functions:**
```python
def get_video_duration(video_path: str) -> float:
    """Get video duration using FFprobe"""
```

**Dependencies:**
- Core API for channel verification
- FFprobe for video metadata
- Filesystem access for collections and schedules

### 13. Fast Scheduler Routes (routes/fast_scheduler.py)

**Endpoints:**
- `POST /api/fast-schedule/{channel}/load-collections` - Load collections
- `POST /api/fast-schedule/{channel}/generate` - Generate schedule
- `GET /api/fast-schedule/{channel}/info` - Get schedule info
- `GET /api/fast-schedule/{channel}/current` - Get current entry
- `GET /api/fast-schedule/{channel}/upcoming` - Get upcoming entries
- `POST /api/fast-schedule/{channel}/save-checkpoint` - Save checkpoint
- `POST /api/fast-schedule/{channel}/load-checkpoint` - Load checkpoint
- `GET /api/fast-schedule/collections` - Get available collections
- `GET /api/fast-schedule/{channel}/status` - Get fast schedule status

**Helper Functions:**
```python
# Module-level cache
fast_schedulers: Dict[str, FastScheduler] = {}

def get_fast_scheduler(channel_name: str) -> FastScheduler:
    """Get or create FastScheduler instance for channel"""
```

**Dependencies:**
- FastScheduler class
- FastScheduleRequest model
- Filesystem access for collections

### 14. VOD Routes (routes/vod.py)

**Endpoints:**
- `GET /api/vod/library` - Get video library from all collections
- `GET /api/vod/video/{video_id}` - Get video details

**Dependencies:**
- Filesystem access for collection files
- JSON parsing for collection data

### 15. WebSocket Routes (routes/websocket.py)

**Endpoints:**
- `WebSocket /ws` - WebSocket endpoint for live updates

**Functions:**
```python
active_connections: List[WebSocket] = []

async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections"""
    
async def broadcast_event(event: Dict[str, Any]):
    """Broadcast event to all connected clients"""
```

**Dependencies:**
- FastAPI WebSocket support
- asyncio for async operations

## Data Models

### Request Models

**PlayNowRequest:**
```python
{
    "video_path": str  # Full path to video file
}
```

**ConfigUpdateRequest:**
```python
{
    "updates": Dict[str, Any]  # Configuration updates
}
```

**ChannelUpdateRequest:**
```python
{
    "enabled": Optional[bool],
    "transcoding": Optional[str],  # "global" | "enabled" | "disabled"
    "subtitles": Optional[str],    # "global" | "enabled" | "disabled"
    "type": Optional[str]          # "linear" | "vod" | "dynamic"
}
```

**FastScheduleRequest:**
```python
{
    "collections": Optional[List[str]],
    "start_time": Optional[str],        # Default: "00:00"
    "schedule_hours": Optional[int],    # Default: 24
    "bumper_frequency": Optional[int],  # Default: 3
    "trailer_probability": Optional[float]  # Default: 0.3
}
```

### Response Models

**Response:**
```python
{
    "success": bool,
    "message": Optional[str],
    "error": Optional[str],
    "data": Optional[Any]
}
```

### Shared State

**Core API Instance:**
- Singleton instance accessed via `get_core_api()`
- Lazy initialization on first access
- Shared across all route modules

**WebSocket Connections:**
- List of active WebSocket connections
- Managed by websocket.py module
- Accessible for broadcasting events

**Fast Scheduler Cache:**
- Dictionary mapping channel names to FastScheduler instances
- Managed by fast_scheduler.py module
- Persists scheduler state across requests


## Correctness Properties

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Property Reflection

After analyzing all acceptance criteria, I identified several areas where properties can be consolidated:

**Redundancy Analysis:**
- Multiple criteria check for "preservation" of specific elements (endpoints, models, middleware, etc.). These can be grouped into broader properties about API contract preservation.
- Several criteria check for "same behavior before and after" which is fundamentally a round-trip/equivalence property.
- File organization criteria (2.1-2.14, 6.1-6.6) are mostly structural checks that don't need separate properties - they're better tested as examples.
- Import and dependency criteria (1.4, 5.5, 7.1, 7.2) can be combined into properties about module independence.

**Consolidated Properties:**
1. API contract preservation (combines 4.3, 4.4, 8.1, 8.5, 10.2, 10.3)
2. Model validation equivalence (1.3)
3. Module independence (7.1, 7.2)
4. Core API accessibility (5.1)
5. Error handling consistency (10.1, 10.3)
6. Documentation preservation (8.2, 8.4)

### Property 1: API Contract Preservation

*For any* endpoint in the original API server, the refactored API server should expose the same endpoint with the same HTTP method, accept the same request format, return the same response format, and produce the same response for equivalent inputs.

**Validates: Requirements 4.3, 4.4, 8.5**

**Rationale:** This is the most critical property for backward compatibility. It ensures that any client code using the API will continue to work without modification. This property encompasses endpoint paths, HTTP methods, request schemas, response schemas, and response data.

### Property 2: Model Validation Equivalence

*For any* Pydantic model and any valid input data, creating a model instance using the extracted models.py should produce the same validation results and field values as the original monolithic implementation.

**Validates: Requirements 1.3**

**Rationale:** This ensures that extracting models to a separate file doesn't change their behavior. Model validation is critical for API correctness, so any change in validation logic would break the API contract.

### Property 3: Module Import Independence

*For any* route module in the routes/ directory, importing that module should succeed without side effects, and importing it multiple times should not cause different behavior or errors.

**Validates: Requirements 7.1, 7.2**

**Rationale:** This property ensures modules are properly isolated and can be tested independently. Side effects on import make testing difficult and can cause subtle bugs. Idempotent imports are a fundamental requirement for maintainable Python code.

### Property 4: Core API Accessibility

*For any* route module that needs Core API access, the module should be able to obtain a Core API instance through dependency injection or a shared utility function.

**Validates: Requirements 5.1**

**Rationale:** This ensures all route modules can access the core functionality they need. Without Core API access, endpoints cannot perform their functions. This property validates that the dependency injection pattern is correctly implemented across all modules.

### Property 5: Error Response Consistency

*For any* error condition that raises an HTTPException, the status code and error message format should be the same before and after refactoring.

**Validates: Requirements 10.1, 10.2, 10.3**

**Rationale:** Consistent error responses are part of the API contract. Clients may depend on specific status codes and error message formats for error handling. Changing these would break client code.

### Property 6: OpenAPI Schema Preservation

*For any* model field or endpoint parameter, the OpenAPI schema metadata (descriptions, field types, constraints) should be the same before and after refactoring.

**Validates: Requirements 8.2, 8.4**

**Rationale:** The OpenAPI schema is used to generate API documentation and client SDKs. Changes to the schema would affect documentation and potentially break generated client code. This property ensures the /docs endpoint shows the same information.

## Error Handling

### Error Handling Strategy

The refactored code will maintain the existing error handling patterns:

**HTTPException for API Errors:**
- 400 Bad Request: Invalid input, missing required fields, business logic violations
- 404 Not Found: Resource not found (channel, video, file)
- 409 Conflict: Resource already exists, conflicting state
- 500 Internal Server Error: Unexpected errors, system failures
- 503 Service Unavailable: Engine not running, service not available

**Try-Except Blocks:**
- Wrap file I/O operations to catch FileNotFoundError, PermissionError
- Wrap JSON parsing to catch JSONDecodeError
- Wrap subprocess calls to catch TimeoutExpired, CalledProcessError
- Wrap Core API calls to catch and translate internal errors

**Error Response Format:**
```python
{
    "success": false,
    "error": "Error message describing what went wrong"
}
```

Or using HTTPException:
```python
{
    "detail": "Error message"
}
```

### Error Handling in Route Modules

Each route module will follow these patterns:

**Input Validation:**
```python
@router.post("/endpoint")
def handler(request: RequestModel):
    if not request.field:
        raise HTTPException(status_code=400, detail="Field is required")
```

**Resource Not Found:**
```python
@router.get("/resource/{id}")
def handler(id: str, api = Depends(get_core_api)):
    resource = api.get_resource(id)
    if resource is None:
        raise HTTPException(status_code=404, detail=f"Resource '{id}' not found")
```

**Internal Errors:**
```python
@router.post("/operation")
def handler(api = Depends(get_core_api)):
    try:
        result = api.perform_operation()
        if not result["success"]:
            raise HTTPException(status_code=500, detail=result["error"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Operation failed: {str(e)}")
```

### Shared Error Handling

Common error handling logic will be extracted to utility functions:

```python
def handle_core_api_result(result: dict, success_message: str = None):
    """Convert Core API result to HTTP response or exception"""
    if result["success"]:
        return Response(success=True, message=success_message or result["message"])
    else:
        raise HTTPException(status_code=500, detail=result["error"])
```

## Testing Strategy

### Dual Testing Approach

The refactored code will be tested using both unit tests and property-based tests:

**Unit Tests:**
- Verify specific examples and edge cases
- Test individual endpoint handlers with mock dependencies
- Test helper functions with known inputs
- Test error conditions and exception handling
- Test integration between components

**Property-Based Tests:**
- Verify universal properties across all inputs
- Test API contract preservation across all endpoints
- Test model validation equivalence across all valid inputs
- Test module import independence across all modules
- Use randomized inputs to discover edge cases

### Unit Testing Focus

Unit tests will focus on:

1. **Endpoint Behavior:**
   - Test each endpoint with valid inputs
   - Test each endpoint with invalid inputs
   - Test error responses
   - Test response formats

2. **Helper Functions:**
   - Test time_to_minutes() with various time formats
   - Test get_schedule_for_date() with calendar and weekly schedules
   - Test get_video_duration() with valid and invalid video paths

3. **Model Validation:**
   - Test each model with valid data
   - Test each model with invalid data
   - Test optional fields
   - Test field constraints

4. **Integration Points:**
   - Test Core API dependency injection
   - Test router registration
   - Test static file mounting
   - Test middleware configuration

### Property-Based Testing Configuration

Property tests will be configured with:
- Minimum 100 iterations per test (due to randomization)
- Each test tagged with: **Feature: api-server-refactor, Property {number}: {property_text}**
- Use hypothesis (Python) for property-based testing
- Generate random valid inputs for models and endpoints

### Property Test Examples

**Property 1: API Contract Preservation**
```python
@given(endpoint=sampled_from(original_endpoints))
def test_endpoint_preservation(endpoint):
    """Test that refactored API has same endpoints as original"""
    # Tag: Feature: api-server-refactor, Property 1: API contract preservation
    original_route = get_original_route(endpoint)
    refactored_route = get_refactored_route(endpoint)
    
    assert original_route.path == refactored_route.path
    assert original_route.methods == refactored_route.methods
    assert original_route.response_model == refactored_route.response_model
```

**Property 2: Model Validation Equivalence**
```python
@given(model_class=sampled_from(model_classes), data=dictionaries(text(), text()))
def test_model_validation_equivalence(model_class, data):
    """Test that extracted models validate the same as original"""
    # Tag: Feature: api-server-refactor, Property 2: Model validation equivalence
    try:
        original_result = create_original_model(model_class, data)
        refactored_result = create_refactored_model(model_class, data)
        assert original_result.dict() == refactored_result.dict()
    except ValidationError as e1:
        with pytest.raises(ValidationError) as e2:
            create_refactored_model(model_class, data)
        assert str(e1) == str(e2.value)
```

**Property 3: Module Import Independence**
```python
@given(module_name=sampled_from(route_modules))
def test_module_import_independence(module_name):
    """Test that route modules can be imported independently"""
    # Tag: Feature: api-server-refactor, Property 3: Module import independence
    # Import module multiple times
    import importlib
    mod1 = importlib.import_module(f"akiratv.routes.{module_name}")
    mod2 = importlib.import_module(f"akiratv.routes.{module_name}")
    
    # Should not raise ImportError
    assert mod1 is not None
    assert mod2 is not None
    # Should be the same module object (Python caches imports)
    assert mod1 is mod2
```

### Testing Balance

The testing strategy balances unit tests and property tests:

- **Unit tests** provide concrete examples and catch specific bugs
- **Property tests** provide comprehensive coverage and catch general correctness issues
- Together they ensure both specific behavior and general correctness

Avoid writing too many unit tests for behavior that property tests already cover. Focus unit tests on:
- Specific edge cases not easily generated
- Integration points between components
- Error conditions with specific expected messages
- Examples that demonstrate correct usage

### Test Organization

Tests will be organized to mirror the source structure:

```
tests/
├── test_api_server.py          # Main app tests
├── test_models.py              # Model validation tests
└── routes/
    ├── test_lifecycle.py       # Lifecycle endpoint tests
    ├── test_channels.py        # Channel endpoint tests
    ├── test_config.py          # Config endpoint tests
    ├── test_library.py         # Library endpoint tests
    ├── test_monitoring.py      # Monitoring endpoint tests
    ├── test_guide.py           # Guide endpoint tests
    ├── test_playlist.py        # Playlist endpoint tests
    ├── test_standby.py         # Standby endpoint tests
    ├── test_wizard.py          # Wizard endpoint tests
    ├── test_fast_scheduler.py  # Fast scheduler endpoint tests
    ├── test_vod.py             # VOD endpoint tests
    └── test_websocket.py       # WebSocket tests
```

Each test file will include both unit tests and property-based tests for its module.
