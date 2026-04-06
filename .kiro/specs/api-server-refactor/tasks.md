# Implementation Plan: API Server Refactoring

## Overview

This plan breaks down the refactoring of the AkiraTV API server from a monolithic 2,073-line file into a modular FastAPI router-based architecture. The implementation will proceed incrementally, creating route modules one at a time while maintaining a working server at each step.

## Tasks

- [x] 1. Create models.py and extract Pydantic models
  - Extract all 5 Pydantic models (PlayNowRequest, ConfigUpdateRequest, ChannelUpdateRequest, FastScheduleRequest, Response) from api_server.py into a new models.py file
  - Update imports in api_server.py to use the new models module
  - Verify the server still starts and endpoints work
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [ ]* 1.1 Write property test for model validation equivalence
  - **Property 2: Model validation equivalence**
  - **Validates: Requirements 1.3**

- [x] 2. Create routes directory structure and lifecycle routes
  - [x] 2.1 Create routes/ directory with __init__.py
    - Create the routes/ directory
    - Create routes/__init__.py with router exports
    - _Requirements: 2.1_
  
  - [x] 2.2 Create routes/lifecycle.py with lifecycle endpoints
    - Extract lifecycle endpoints (start, stop, restart, status) into routes/lifecycle.py
    - Create APIRouter with prefix="/api" and tag="Lifecycle"
    - Implement get_core_api dependency
    - Move 4 endpoint handlers from api_server.py
    - _Requirements: 2.2_
  
  - [x] 2.3 Register lifecycle router in main api_server.py
    - Import lifecycle router in api_server.py
    - Register router using app.include_router()
    - Remove original lifecycle endpoints from api_server.py
    - Verify lifecycle endpoints still work
    - _Requirements: 2.2, 4.3, 4.4_

- [ ]* 2.4 Write property test for API contract preservation (lifecycle endpoints)
  - **Property 1: API contract preservation**
  - **Validates: Requirements 4.3, 4.4**

- [x] 3. Create channel routes module
  - [x] 3.1 Create routes/channels.py with channel endpoints
    - Create APIRouter with prefix="/api" and tag="Channels"
    - Extract all 15 channel endpoints from api_server.py
    - Include socket import for IP detection in get_all_channel_urls
    - Move channel-related helper logic
    - _Requirements: 2.3_
  
  - [x] 3.2 Register channels router in main api_server.py
    - Import channels router
    - Register using app.include_router()
    - Remove original channel endpoints from api_server.py
    - Verify all channel endpoints work
    - _Requirements: 2.3, 4.3, 4.4_

- [ ]* 3.3 Write unit tests for channel endpoints
  - Test channel creation, enable/disable, update settings
  - Test URL generation for LAN and Tailscale
  - Test play/stop operations on VOD channels
  - _Requirements: 2.3_

- [x] 4. Create configuration routes module
  - [x] 4.1 Create routes/config.py with configuration endpoints
    - Create APIRouter with prefix="/api/config" and tag="Configuration"
    - Extract 5 configuration endpoints from api_server.py
    - Import Config class for defaults endpoint
    - _Requirements: 2.4_
  
  - [x] 4.2 Register config router in main api_server.py
    - Import config router
    - Register using app.include_router()
    - Remove original config endpoints from api_server.py
    - Verify config endpoints work
    - _Requirements: 2.4, 4.3, 4.4_

- [x] 5. Create library and monitoring routes modules
  - [x] 5.1 Create routes/library.py with library endpoints
    - Create APIRouter with prefix="/api/library" and tag="Library"
    - Extract 2 library endpoints (stats, scan)
    - _Requirements: 2.5_
  
  - [x] 5.2 Create routes/monitoring.py with monitoring endpoints
    - Create APIRouter with prefix="/api" and tag="Monitoring"
    - Extract 5 monitoring endpoints (stats, viewers, logs)
    - Import viewer_tracker for viewer detail endpoints
    - _Requirements: 2.6_
  
  - [x] 5.3 Register library and monitoring routers
    - Import both routers in api_server.py
    - Register using app.include_router()
    - Remove original endpoints from api_server.py
    - Verify endpoints work
    - _Requirements: 2.5, 2.6, 4.3, 4.4_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. Create guide routes module with helper functions
  - [x] 7.1 Create routes/guide.py with guide endpoints and helpers
    - Create APIRouter with prefix="/api/guide" and tag="TV Guide"
    - Extract 3 guide endpoints (current, weekly, date-specific)
    - Move time_to_minutes() helper function
    - Move get_schedule_for_date() helper function
    - Import datetime and Path for date handling
    - _Requirements: 2.7, 6.3, 6.4_
  
  - [x] 7.2 Register guide router in main api_server.py
    - Import guide router
    - Register using app.include_router()
    - Remove original guide endpoints and helpers from api_server.py
    - Verify guide endpoints work correctly
    - _Requirements: 2.7, 4.3, 4.4_

- [ ]* 7.3 Write unit tests for guide helper functions
  - Test time_to_minutes with various time formats
  - Test get_schedule_for_date with calendar and weekly schedules
  - _Requirements: 6.3, 6.4_

- [x] 8. Create playlist and standby routes modules
  - [x] 8.1 Create routes/playlist.py with playlist endpoints
    - Create APIRouter with prefix="/api/playlist" and tag="Playlist"
    - Extract 3 playlist endpoints (create, get videos, play selected)
    - _Requirements: 2.8_
  
  - [x] 8.2 Create routes/standby.py with standby endpoint
    - Create APIRouter with prefix="/api/standby" and tag="Standby"
    - Extract standby creation endpoint
    - Import standby module and Counter for resolution detection
    - _Requirements: 2.9_
  
  - [x] 8.3 Register playlist and standby routers
    - Import both routers in api_server.py
    - Register using app.include_router()
    - Remove original endpoints from api_server.py
    - Verify endpoints work
    - _Requirements: 2.8, 2.9, 4.3, 4.4_

- [x] 9. Create wizard routes module with helper function
  - [x] 9.1 Create routes/wizard.py with wizard endpoints
    - Create APIRouter with prefix="/api/wizard" and tag="Wizard"
    - Extract 5 wizard endpoints (log, scan folder, check collection, create collection, create schedule)
    - Move get_video_duration() helper function
    - Import subprocess and json for FFprobe integration
    - _Requirements: 2.10, 6.5_
  
  - [x] 9.2 Register wizard router in main api_server.py
    - Import wizard router
    - Register using app.include_router()
    - Remove original wizard endpoints and helper from api_server.py
    - Verify wizard endpoints work
    - _Requirements: 2.10, 4.3, 4.4_

- [ ]* 9.3 Write unit tests for wizard endpoints
  - Test folder scanning with various directory structures
  - Test collection creation and validation
  - Test get_video_duration with valid and invalid paths
  - _Requirements: 2.10, 6.5_

- [x] 10. Create fast scheduler routes module
  - [x] 10.1 Create routes/fast_scheduler.py with fast scheduler endpoints
    - Create APIRouter with prefix="/api/fast-schedule" and tag="Fast Scheduler"
    - Extract 9 fast scheduler endpoints
    - Move fast_schedulers cache dictionary
    - Move get_fast_scheduler() helper function
    - Import FastScheduler class
    - _Requirements: 2.11, 6.6_
  
  - [x] 10.2 Register fast scheduler router in main api_server.py
    - Import fast_scheduler router
    - Register using app.include_router()
    - Remove original fast scheduler endpoints and helpers from api_server.py
    - Verify fast scheduler endpoints work
    - _Requirements: 2.11, 4.3, 4.4_

- [x] 11. Create VOD and WebSocket routes modules
  - [x] 11.1 Create routes/vod.py with VOD endpoints
    - Create APIRouter with prefix="/api/vod" and tag="VOD"
    - Extract 2 VOD endpoints (library, video details)
    - _Requirements: 2.12_
  
  - [x] 11.2 Create routes/websocket.py with WebSocket handler
    - Create WebSocket endpoint at /ws
    - Move active_connections list
    - Move broadcast_event() helper function
    - Import WebSocket, WebSocketDisconnect from fastapi
    - _Requirements: 2.13, 6.6_
  
  - [x] 11.3 Register VOD router and WebSocket endpoint
    - Import vod router in api_server.py
    - Import websocket_endpoint function
    - Register vod router using app.include_router()
    - Register WebSocket endpoint using @app.websocket decorator
    - Remove original endpoints from api_server.py
    - Verify VOD and WebSocket work
    - _Requirements: 2.12, 2.13, 4.3, 4.4_

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Update routes/__init__.py to export all routers
  - Import all route modules
  - Export all routers in __all__ list
  - Verify all routers can be imported from routes package
  - _Requirements: 2.14_

- [ ]* 13.1 Write property test for module import independence
  - **Property 3: Module import independence**
  - **Validates: Requirements 7.1, 7.2**

- [x] 14. Refactor main api_server.py to minimal structure
  - [x] 14.1 Clean up main api_server.py
    - Remove all extracted endpoint handlers
    - Remove all extracted helper functions
    - Keep only: FastAPI app initialization, middleware setup, static file mounting, router registration, root endpoints (/, /viewer, /health), startup/shutdown handlers, main entry point
    - Verify file is approximately 200 lines or less
    - _Requirements: 3.1, 3.2, 3.3, 3.4_
  
  - [x] 14.2 Verify backward compatibility
    - Test launch with: uvicorn akiratv.api_server:app --reload --port 8000
    - Test direct execution: python -m akiratv.api_server
    - Verify app variable can be imported
    - Verify all middleware is configured
    - Verify static files are mounted
    - _Requirements: 4.1, 4.2, 4.5, 4.6, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [ ]* 14.3 Write property test for Core API accessibility
  - **Property 4: Core API accessibility**
  - **Validates: Requirements 5.1**

- [ ]* 14.4 Write property test for error response consistency
  - **Property 5: Error response consistency**
  - **Validates: Requirements 10.1, 10.2, 10.3**

- [ ] 15. Verify OpenAPI documentation preservation
  - [ ] 15.1 Compare OpenAPI schemas before and after refactoring
    - Generate OpenAPI schema from original api_server.py
    - Generate OpenAPI schema from refactored api_server.py
    - Compare schemas to ensure they match
    - Verify /docs endpoint displays same structure
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [ ]* 15.2 Write property test for OpenAPI schema preservation
  - **Property 6: OpenAPI schema preservation**
  - **Validates: Requirements 8.2, 8.4**

- [ ] 16. Final integration testing
  - [ ] 16.1 Test all endpoints end-to-end
    - Test lifecycle endpoints (start, stop, restart, status)
    - Test channel endpoints (create, enable, disable, play, stop)
    - Test configuration endpoints (get, update, save)
    - Test library endpoints (stats, scan)
    - Test monitoring endpoints (stats, viewers, logs)
    - Test guide endpoints (current, weekly, date-specific)
    - Test playlist endpoints (create, get, play)
    - Test standby endpoint
    - Test wizard endpoints (scan, create collection, create schedule)
    - Test fast scheduler endpoints (load, generate, info)
    - Test VOD endpoints (library, video details)
    - Test WebSocket connection
    - _Requirements: 4.3, 4.4_
  
  - [ ] 16.2 Verify error handling consistency
    - Test error responses for invalid inputs
    - Test error responses for missing resources
    - Test error responses for internal errors
    - Verify status codes match original implementation
    - Verify error message formats match original implementation
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- The refactoring maintains backward compatibility at every step
- Each route module can be created and tested independently
- The server should remain functional after each major step
