# Block Programming Feature Implementation Plan

## Overview
This document outlines the implementation plan for adding block programming functionality to the AkiraTV Simple Scheduler. The feature will allow users to create scheduled blocks of content with specific time ranges, enabling more structured programming compared to the current random/sequential scheduling.

## Current State Analysis
The existing simple scheduler provides:
- Random and sequential video scheduling
- Weekly and calendar-based scheduling modes
- Basic video management with collections and blacklisting
- Preview functionality for generated schedules

## Proposed Block Programming Features

### 1. Block Definition Interface
- **Modal Dialog**: A new modal window for creating and editing blocks
- **Block Properties**:
  - Name/Title
  - Start and End Times
  - Day(s) of Week
  - Content Selection (collections or specific videos)
  - Repeat Options (daily, weekly, custom)
  - Priority Level

### 2. Block Management System
- **Block List**: Display all defined blocks with their properties
- **Edit/Delete Operations**: Modify existing blocks
- **Validation**: Ensure blocks don't overlap or conflict
- **Import/Export**: Save/load block configurations

### 3. Enhanced Scheduling Algorithm
- **Block-Based Scheduling**: Generate schedules based on defined blocks
- **Conflict Resolution**: Handle overlapping blocks intelligently
- **Priority System**: Higher priority blocks override lower priority ones
- **Fallback Content**: Default content for empty time slots

### 4. User Interface Integration
- **New Tab**: Dedicated block programming tab in the main interface
- **Visual Timeline**: Graphical representation of blocks and schedules
- **Drag-and-Drop**: Intuitive block manipulation
- **Real-time Preview**: Immediate feedback on schedule changes

## Technical Implementation Plan

### Phase 1: Core Block System
1. **Block Data Model**
   - Create `Block` class with properties and validation
   - Implement serialization/deserialization
   - Add block storage and retrieval methods

2. **Block Management UI**
   - Design modal dialog layout
   - Implement form validation
   - Add block list display

### Phase 2: Scheduling Integration
1. **Block-Based Scheduler**
   - Modify existing scheduling algorithms
   - Implement block conflict detection
   - Add priority-based resolution

2. **UI Integration**
   - Add block programming tab
   - Implement visual timeline
   - Connect to existing preview system

### Phase 3: Advanced Features
1. **Repeat Logic**
   - Implement daily/weekly/custom repeat patterns
   - Add exception handling for holidays/special events

2. **Import/Export**
   - Create JSON-based block configuration format
   - Add import/export functionality

## File Structure Changes

### New Files
```
akiratv/
├── block_programming_scheduler.py
├── block_programming_ui.py
└── block_programming_models.py
```

### Modified Files
```
akiratv/
├── simple_scheduler.py
└── ui/
    └── main.py
```

## Key Implementation Details

### Block Data Structure
```python
class Block:
    def __init__(self, name, start_time, end_time, days, content, priority=1, repeat='daily'):
        self.name = name
        self.start_time = start_time  # datetime.time
        self.end_time = end_time      # datetime.time
        self.days = days              # list of weekdays
        self.content = content        # list of video paths or collection IDs
        self.priority = priority      # 1-10 (higher = more important)
        self.repeat = repeat          # 'daily', 'weekly', 'custom'
        self.exceptions = []          # dates to exclude
```

### Scheduling Algorithm Changes
1. **Block Processing Order**: Sort blocks by priority, then by start time
2. **Conflict Detection**: Check for overlapping time ranges
3. **Content Assignment**: Fill block time slots with selected content
4. **Fallback Handling**: Use default content for unassigned slots

## User Experience Considerations

### Modal Design
- Clean, intuitive form layout
- Real-time validation feedback
- Visual block representation in timeline

### Timeline Interface
- Color-coded blocks by priority
- Hover tooltips with block details
- Click-to-edit functionality

### Error Handling
- Clear validation messages
- Conflict resolution suggestions
- Undo/redo support for changes

## Testing Strategy

### Unit Tests
- Block validation logic
- Scheduling algorithm correctness
- Conflict resolution scenarios

### Integration Tests
- End-to-end block creation and scheduling
- UI interaction testing
- Import/export functionality

### User Acceptance Testing
- Usability testing with target users
- Performance testing with large block sets
- Edge case validation

## Timeline and Milestones

### Week 1: Core Block System
- [ ] Block data model implementation
- [ ] Basic block management UI
- [ ] Block storage and retrieval

### Week 2: Scheduling Integration
- [ ] Block-based scheduling algorithm
- [ ] UI integration and timeline view
- [ ] Preview functionality

### Week 3: Advanced Features
- [ ] Repeat logic implementation
- [ ] Import/export functionality
- [ ] Testing and bug fixes

### Week 4: Polish and Documentation
- [ ] UI refinements
- [ ] Comprehensive documentation
- [ ] User guide creation

## Success Metrics

### Functional Requirements
- [ ] Users can create and edit blocks
- [ ] Blocks generate correct schedules
- [ ] Conflicts are resolved appropriately
- [ ] Import/export works correctly

### Performance Requirements
- [ ] Schedule generation completes within 5 seconds
- [ ] UI remains responsive with 100+ blocks
- [ ] Memory usage stays below 500MB

### Usability Requirements
- [ ] New users can create blocks within 5 minutes
- [ ] Block programming is intuitive and discoverable
- [ ] Error messages are clear and helpful

## Risk Assessment

### Technical Risks
- **Complex Scheduling Logic**: May require multiple iterations
- **UI Performance**: Large block sets could impact responsiveness
- **Data Consistency**: Ensuring block integrity across sessions

### Mitigation Strategies
- **Incremental Development**: Build and test features incrementally
- **Performance Optimization**: Implement lazy loading and caching
- **Robust Testing**: Comprehensive test coverage for edge cases

## Dependencies

### Internal Dependencies
- Existing collection system
- Current scheduling algorithms
- UI framework (tkinter)

### External Dependencies
- Python standard library
- PIL (Pillow) for image handling
- tkinter for UI components

## Conclusion
The block programming feature will significantly enhance the AkiraTV Simple Scheduler by providing structured programming capabilities. The implementation plan balances functionality with usability, ensuring a powerful yet intuitive tool for content scheduling.

This plan provides a solid foundation for development while remaining flexible enough to accommodate user feedback and evolving requirements.