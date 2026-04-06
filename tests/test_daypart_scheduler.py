# tests/test_daypart_scheduler.py
"""
Unit tests for daypart_scheduler module
"""

import pytest
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from akiratv.daypart_scheduler import (
    TimeBlock, MarathonConfig, GapFillerConfig,
    parse_time_string, format_time_string,
    calculate_duration, detect_gaps, has_overlapping_blocks,
    validate_time_block, validate_daypart_config,
    get_weekday_indices, has_excluded_tag
)


class TestTimeBlock:
    """Tests for TimeBlock class"""
    
    def test_creation(self):
        block = TimeBlock("06:00", "10:00", "tag", "kids")
        assert block.start_time == "06:00"
        assert block.end_time == "10:00"
        assert block.content_type == "tag"
        assert block.content_value == "kids"
        assert block.block_id is not None
    
    def test_duration_seconds(self):
        block = TimeBlock("06:00", "10:00", "tag", "kids")
        assert block.duration_seconds == 14400  # 4 hours
    
    def test_duration_mins(self):
        block = TimeBlock("10:00", "12:00", "tag", "doc")
        assert block.duration_seconds == 7200  # 2 hours
    
    def test_serialization(self):
        block = TimeBlock("06:00", "10:00", "video", "/path/to/video.mp4", "block_123")
        data = block.to_dict()
        assert data["start_time"] == "06:00"
        assert data["end_time"] == "10:00"
        assert data["content_type"] == "video"
        assert data["content_value"] == "/path/to/video.mp4"
        assert data["block_id"] == "block_123"
        
        # Deserialize
        block2 = TimeBlock.from_dict(data)
        assert block2.start_time == block.start_time
        assert block2.end_time == block.end_time
        assert block2.content_type == block.content_type
        assert block2.content_value == block.content_value
        assert block2.block_id == block.block_id
    
    def test_handle_2400(self):
        """Test that 24:00 is handled correctly"""
        block = TimeBlock("22:00", "24:00", "tag", "horror")
        assert block.duration_seconds == 7200  # 2 hours
    
    def test_invalid_duration_zero(self):
        """Test block with same start and end"""
        block = TimeBlock("06:00", "06:00", "tag", "test")
        assert block.duration_seconds == 0


class TestMarathonConfig:
    """Tests for MarathonConfig class"""
    
    def test_creation(self):
        marathon = MarathonConfig("80s", ["friday", "saturday"])
        assert marathon.tag == "80s"
        assert marathon.days == ["friday", "saturday"]
        assert marathon.enabled is True
        assert marathon.shuffle is True
        assert marathon.no_repeat_24h is True
    
    def test_serialization(self):
        marathon = MarathonConfig("action", ["monday", "tuesday"], enabled=False, shuffle=False, no_repeat_24h=False)
        data = marathon.to_dict()
        assert data["tag"] == "action"
        assert data["days"] == ["monday", "tuesday"]
        assert data["enabled"] is False
        assert data["shuffle"] is False
        assert data["no_repeat_24h"] is False
        
        marathon2 = MarathonConfig.from_dict(data)
        assert marathon2.tag == marathon.tag
        assert marathon2.days == marathon.days
        assert marathon2.enabled == marathon.enabled
    
    def test_default_values(self):
        marathon = MarathonConfig("test", ["sunday"])
        assert marathon.enabled is True
        assert marathon.shuffle is True
        assert marathon.no_repeat_24h is True


class TestGapFillerConfig:
    """Tests for GapFillerConfig class"""
    
    def test_creation(self):
        config = GapFillerConfig(enabled=True, source="all", excluded_tags=["horror"])
        assert config.enabled is True
        assert config.source == "all"
        assert config.excluded_tags == ["horror"]
        assert config.respect_24h_norepeat is True
        assert config.shuffle is True
    
    def test_serialization(self):
        config = GapFillerConfig(
            enabled=False,
            source="tags",
            excluded_tags=["kids"],
            respect_24h_norepeat=False,
            shuffle=False
        )
        config.tags = ["action", "comedy"]
        data = config.to_dict()
        assert data["enabled"] is False
        assert data["source"] == "tags"
        assert data["tags"] == ["action", "comedy"]
        assert data["excluded_tags"] == ["kids"]
        assert data["respect_24h_norepeat"] is False
        assert data["shuffle"] is False


class TestTimeParsing:
    """Tests for time parsing functions"""
    
    def test_parse_time_string_normal(self):
        dt = parse_time_string("06:30")
        assert dt.hour == 6
        assert dt.minute == 30
    
    def test_parse_time_string_2400(self):
        """24:00 should become 00:00 of next day"""
        dt = parse_time_string("24:00")
        assert dt.hour == 0
        assert dt.minute == 0
        assert dt.day == 2  # Next day
    
    def test_format_time_string_normal(self):
        dt = datetime(2023, 1, 1, 14, 30)
        assert format_time_string(dt) == "14:30"
    
    def test_format_time_string_2400(self):
        """Midnight of next day should format as 24:00"""
        dt = datetime(2023, 1, 2, 0, 0)  # Next day midnight
        assert format_time_string(dt) == "24:00"
    
    def test_calculate_duration(self):
        assert calculate_duration("06:00", "10:00") == 14400
        assert calculate_duration("00:00", "24:00") == 86400
        assert calculate_duration("22:00", "02:00") == 14400  # Overnight
    
    def test_calculate_duration_short(self):
        assert calculate_duration("10:00", "10:30") == 1800


class TestGapDetection:
    """Tests for gap detection algorithm"""
    
    def test_no_blocks(self):
        gaps = detect_gaps([])
        assert gaps == [("00:00", "24:00")]
    
    def test_single_block(self):
        blocks = [TimeBlock("06:00", "10:00", "tag", "kids")]
        gaps = detect_gaps(blocks)
        expected = [("00:00", "06:00"), ("10:00", "24:00")]
        assert gaps == expected
    
    def test_multiple_blocks(self):
        blocks = [
            TimeBlock("06:00", "10:00", "tag", "a"),
            TimeBlock("12:00", "14:00", "tag", "b"),
            TimeBlock("20:00", "24:00", "tag", "c")
        ]
        gaps = detect_gaps(blocks)
        expected = [("00:00", "06:00"), ("10:00", "12:00"), ("14:00", "20:00")]
        assert gaps == expected
    
    def test_adjacent_blocks(self):
        """Blocks that are exactly adjacent should produce no gap between them"""
        blocks = [
            TimeBlock("06:00", "10:00", "tag", "a"),
            TimeBlock("10:00", "14:00", "tag", "b"),
            TimeBlock("14:00", "18:00", "tag", "c")
        ]
        gaps = detect_gaps(blocks)
        expected = [("00:00", "06:00"), ("18:00", "24:00")]
        assert gaps == expected
    
    def test_blocks_with_2400(self):
        """Test gap detection with 24:00 end time"""
        blocks = [TimeBlock("22:00", "24:00", "tag", "horror")]
        gaps = detect_gaps(blocks)
        expected = [("00:00", "22:00")]
        assert gaps == expected
    
    def test_blocks_covering_entire_day(self):
        """Blocks that cover entire day should produce no gaps"""
        blocks = [
            TimeBlock("00:00", "06:00", "tag", "a"),
            TimeBlock("06:00", "12:00", "tag", "b"),
            TimeBlock("12:00", "18:00", "tag", "c"),
            TimeBlock("18:00", "24:00", "tag", "d")
        ]
        gaps = detect_gaps(blocks)
        assert gaps == []


class TestOverlapDetection:
    """Tests for overlap detection"""
    
    def test_no_overlap_single_block(self):
        blocks = [TimeBlock("06:00", "10:00", "tag", "a")]
        assert not has_overlapping_blocks(blocks)
    
    def test_no_overlap_adjacent(self):
        blocks = [
            TimeBlock("06:00", "10:00", "tag", "a"),
            TimeBlock("10:00", "14:00", "tag", "b")
        ]
        assert not has_overlapping_blocks(blocks)
    
    def test_no_overlap_separate(self):
        blocks = [
            TimeBlock("06:00", "10:00", "tag", "a"),
            TimeBlock("12:00", "14:00", "tag", "b")
        ]
        assert not has_overlapping_blocks(blocks)
    
    def test_overlap_detected(self):
        blocks = [
            TimeBlock("06:00", "10:00", "tag", "a"),
            TimeBlock("09:00", "12:00", "tag", "b")  # Overlaps
        ]
        assert has_overlapping_blocks(blocks)
    
    def test_overlap_complete_containment(self):
        blocks = [
            TimeBlock("06:00", "14:00", "tag", "a"),
            TimeBlock("10:00", "12:00", "tag", "b")  # Inside first block
        ]
        assert has_overlapping_blocks(blocks)
    
    def test_overlap_three_blocks(self):
        blocks = [
            TimeBlock("06:00", "10:00", "tag", "a"),
            TimeBlock("10:00", "14:00", "tag", "b"),
            TimeBlock("13:00", "15:00", "tag", "c")  # Overlaps with second
        ]
        assert has_overlapping_blocks(blocks)


class TestValidation:
    """Tests for time block validation"""
    
    def test_valid_block(self):
        block = TimeBlock("06:00", "10:00", "tag", "kids")
        error = validate_time_block(block)
        assert error is None
    
    def test_invalid_time_format(self):
        block = TimeBlock("25:00", "10:00", "tag", "kids")
        error = validate_time_block(block)
        assert error is not None
        assert "Invalid start time format" in error
    
    def test_invalid_end_time_format(self):
        block = TimeBlock("06:00", "abc", "tag", "kids")
        error = validate_time_block(block)
        assert error is not None
    
    def test_overnight_block_invalid(self):
        block = TimeBlock("22:00", "02:00", "tag", "horror")
        error = validate_time_block(block)
        assert error is not None
        assert "Overnight blocks not allowed" in error
    
    def test_zero_duration_invalid(self):
        block = TimeBlock("06:00", "06:00", "tag", "test")
        error = validate_time_block(block)
        assert error is not None
        assert "positive" in error.lower()
    
    def test_empty_content_value(self):
        block = TimeBlock("06:00", "10:00", "tag", "")
        error = validate_time_block(block)
        assert error is not None
        assert "empty" in error.lower()
    
    def test_invalid_content_type(self):
        block = TimeBlock("06:00", "10:00", "invalid", "test")
        error = validate_time_block(block)
        assert error is not None
        assert "Invalid content_type" in error


class TestHelperFunctions:
    """Tests for helper functions"""
    
    def test_get_weekday_indices(self):
        indices = get_weekday_indices(["monday", "friday", "sunday"])
        assert indices == [0, 4, 6]
    
    def test_get_weekday_indices_case_insensitive(self):
        indices = get_weekday_indices(["MONDAY", "Friday"])
        assert indices == [0, 4]
    
    def test_has_excluded_tag(self):
        video = {"tags": ["action", "adventure", "80s"]}
        assert has_excluded_tag(video, ["horror", "comedy"]) is False
        assert has_excluded_tag(video, ["action"]) is True
        assert has_excluded_tag(video, ["80s", "kids"]) is True
        assert has_excluded_tag(video, []) is False
    
    def test_validate_daypart_config_empty(self):
        config = {}
        errors = validate_daypart_config(config)
        assert "Missing 'daypart_config' section" in errors
    
    def test_validate_daypart_config_valid(self):
        config = {
            "daypart_config": {
                "time_blocks": [
                    {
                        "block_id": "test",
                        "start_time": "06:00",
                        "end_time": "10:00",
                        "content_type": "tag",
                        "content_value": "kids",
                        "duration_seconds": 14400
                    }
                ],
                "marathons": [],
                "gap_filler": {
                    "enabled": True,
                    "source": "all",
                    "excluded_tags": []
                }
            }
        }
        errors = validate_daypart_config(config)
        assert len(errors) == 0
    
    def test_validate_daypart_config_overlapping_blocks(self):
        config = {
            "daypart_config": {
                "time_blocks": [
                    {
                        "block_id": "block1",
                        "start_time": "06:00",
                        "end_time": "10:00",
                        "content_type": "tag",
                        "content_value": "a",
                        "duration_seconds": 14400
                    },
                    {
                        "block_id": "block2",
                        "start_time": "08:00",  # Overlaps
                        "end_time": "12:00",
                        "content_type": "tag",
                        "content_value": "b",
                        "duration_seconds": 14400
                    }
                ],
                "marathons": [],
                "gap_filler": {"enabled": True, "source": "all"}
            }
        }
        errors = validate_daypart_config(config)
        assert any("overlap" in e.lower() for e in errors)
    
    def test_validate_marathon_missing_tag(self):
        config = {
            "daypart_config": {
                "time_blocks": [],
                "marathons": [
                    {"days": ["friday"]}  # Missing tag
                ],
                "gap_filler": {"enabled": True, "source": "all"}
            }
        }
        errors = validate_daypart_config(config)
        assert any("Missing tag" in e for e in errors)
    
    def test_validate_marathon_missing_days(self):
        config = {
            "daypart_config": {
                "time_blocks": [],
                "marathons": [
                    {"tag": "80s"}  # Missing days
                ],
                "gap_filler": {"enabled": True, "source": "all"}
            }
        }
        errors = validate_daypart_config(config)
        assert any("no days selected" in e.lower() for e in errors)
    
    def test_validate_gap_filler_invalid_source(self):
        config = {
            "daypart_config": {
                "time_blocks": [],
                "marathons": [],
                "gap_filler": {
                    "enabled": True,
                    "source": "invalid_source"
                }
            }
        }
        errors = validate_daypart_config(config)
        assert any("Invalid gap_filler source" in e for e in errors)


class TestDaypartSchedulerClass:
    """Tests for DaypartScheduler class"""
    
    def test_creation(self):
        from akiratv.daypart_scheduler import DaypartScheduler
        scheduler = DaypartScheduler()
        assert scheduler.configs == {}
        assert scheduler.enabled_channels == set()
    
    def test_load_config_nonexistent(self):
        from akiratv.daypart_scheduler import DaypartScheduler
        scheduler = DaypartScheduler()
        config = scheduler.load_config("nonexistent_channel")
        assert config is None
    
    def test_save_and_load_config(self, tmp_path):
        from akiratv.daypart_scheduler import DaypartScheduler, create_default_daypart_config
        # Temporarily override SCHEDULE_DIR
        import akiratv.daypart_scheduler as ds
        original_dir = ds.SCHEDULE_DIR
        ds.SCHEDULE_DIR = tmp_path
        
        try:
            scheduler = DaypartScheduler()
            config = create_default_daypart_config()
            config["enabled"] = True
            
            success = scheduler.save_config("test_channel", config)
            assert success is True
            
            loaded = scheduler.load_config("test_channel")
            assert loaded is not None
            assert loaded["enabled"] is True
        finally:
            ds.SCHEDULE_DIR = original_dir
    
    def test_is_enabled(self):
        from akiratv.daypart_scheduler import DaypartScheduler, create_default_daypart_config
        scheduler = DaypartScheduler()
        config = create_default_daypart_config()
        config["enabled"] = True
        scheduler.configs["test"] = config
        
        assert scheduler.is_enabled("test") is True
        
        config["enabled"] = False
        assert scheduler.is_enabled("test") is False
    
    def test_enable_channel(self):
        from akiratv.daypart_scheduler import DaypartScheduler, create_default_daypart_config
        import akiratv.daypart_scheduler as ds
        original_dir = ds.SCHEDULE_DIR
        ds.SCHEDULE_DIR = Path(".")  # Use current dir for test
        
        try:
            scheduler = DaypartScheduler()
            config = create_default_daypart_config()
            scheduler.configs["test"] = config
            
            scheduler.enable_channel("test", True)
            assert scheduler.is_enabled("test") is True
            assert "test" in scheduler.enabled_channels
            
            scheduler.enable_channel("test", False)
            assert scheduler.is_enabled("test") is False
            assert "test" not in scheduler.enabled_channels
        finally:
            ds.SCHEDULE_DIR = original_dir
    
    def test_clear_cache(self):
        from akiratv.daypart_scheduler import DaypartScheduler
        scheduler = DaypartScheduler()
        scheduler.configs["test1"] = {}
        scheduler.enabled_channels.add("test2")
        
        scheduler.clear_cache()
        assert scheduler.configs == {}
        assert scheduler.enabled_channels == set()


class TestGetAvailableTags:
    """Tests for get_available_tags_from_collections"""
    
    def test_extract_tags(self):
        from akiratv.daypart_scheduler import get_available_tags_from_collections
        collections = [
            {"tags": ["action", "adventure"]},
            {"tags": ["horror", "thriller"]},
            {"tags": ["action", "comedy"]}
        ]
        tags = get_available_tags_from_collections(collections)
        assert set(tags) == {"action", "adventure", "horror", "thriller", "comedy"}
    
    def test_empty_collections(self):
        from akiratv.daypart_scheduler import get_available_tags_from_collections
        tags = get_available_tags_from_collections([])
        assert tags == []
    
    def test_collections_without_tags(self):
        from akiratv.daypart_scheduler import get_available_tags_from_collections
        collections = [
            {"tags": []},
            {"tags": ["drama"]}
        ]
        tags = get_available_tags_from_collections(collections)
        assert tags == ["drama"]


class TestScheduleGeneration:
    """Integration tests for schedule generation functions"""
    
    def test_generate_block_schedule_tag_based(self):
        """Test tag-based block schedule generation"""
        from akiratv.daypart_scheduler import TimeBlock, generate_block_schedule
        
        # Create mock available videos
        available_videos = [
            {"path": "/video1.mp4", "duration": 600, "tags": ["kids"]},
            {"path": "/video2.mp4", "duration": 600, "tags": ["kids"]},
            {"path": "/video3.mp4", "duration": 600, "tags": ["horror"]}
        ]
        
        block = TimeBlock("06:00", "08:00", "tag", "kids")
        entries = generate_block_schedule(block, available_videos, [], "test_channel")
        
        assert len(entries) >= 1  # At least one entry to fill time
        for entry in entries:
            assert entry["source"] == "daypart_tag"
            assert entry["metadata"]["tag_used"] == "kids"
    
    def test_generate_block_schedule_specific_video(self):
        """Test specific video block schedule generation"""
        from akiratv.daypart_scheduler import TimeBlock, generate_block_schedule
        
        available_videos = [
            {"path": "/video1.mp4", "duration": 120, "tags": ["action"], "collection": {"id": "col1"}}
        ]
        
        block = TimeBlock("10:00", "12:00", "video", "/video1.mp4")
        entries = generate_block_schedule(block, available_videos, [], "test_channel")
        
        assert len(entries) == 1
        assert entries[0]["file"] == "/video1.mp4"
        assert entries[0]["source"] == "daypart_video"
    
    def test_generate_marathon_schedule(self):
        """Test marathon schedule generation"""
        from akiratv.daypart_scheduler import MarathonConfig, generate_marathon_schedule
        
        available_videos = [
            {"path": "/v1.mp4", "duration": 3600, "tags": ["80s"]},
            {"path": "/v2.mp4", "duration": 3600, "tags": ["80s"]},
            {"path": "/v3.mp4", "duration": 3600, "tags": ["80s"]}
        ]
        
        marathon = MarathonConfig("80s", ["friday"])
        entries = generate_marathon_schedule("80s", available_videos, marathon, [], "test_channel")
        
        # Marathon should fill 24 hours
        assert len(entries) > 0
        for entry in entries:
            assert entry["source"] == "daypart_marathon"
    
    def test_fill_gaps_with_random_all_source(self):
        """Test gap filling with source='all'"""
        from akiratv.daypart_scheduler import GapFillerConfig, fill_gaps_with_random
        
        gaps = [("10:00", "12:00")]
        available_videos = [
            {"path": "/v1.mp4", "duration": 1800, "tags": ["action"], "collection": {"id": "col1"}},
            {"path": "/v2.mp4", "duration": 1800, "tags": ["comedy"], "collection": {"id": "col2"}}
        ]
        
        config = GapFillerConfig(enabled=True, source="all")
        entries = fill_gaps_with_random(gaps, available_videos, config, [], "test_channel")
        
        assert len(entries) > 0
        assert all(e["source"] == "gap_filler" for e in entries)
    
    def test_fill_gaps_with_random_collections_filter(self):
        """Test gap filling with collection filtering"""
        from akiratv.daypart_scheduler import GapFillerConfig, fill_gaps_with_random
        
        gaps = [("10:00", "12:00")]
        available_videos = [
            {"path": "/v1.mp4", "duration": 1800, "tags": ["action"], "collection": {"id": "col1"}},
            {"path": "/v2.mp4", "duration": 1800, "tags": ["comedy"], "collection": {"id": "col2"}},
            {"path": "/v3.mp4", "duration": 1800, "tags": ["drama"], "collection": {"id": "col3"}}
        ]
        
        # Filter to only col1
        config = GapFillerConfig(enabled=True, source="collections", collection_ids=["col1"])
        entries = fill_gaps_with_random(gaps, available_videos, config, [], "test_channel")
        
        # All entries should be from col1
        for entry in entries:
            assert entry["collection_id"] == "col1"
    
    def test_fill_gaps_with_random_tags_filter(self):
        """Test gap filling with tag filtering"""
        from akiratv.daypart_scheduler import GapFillerConfig, fill_gaps_with_random
        
        gaps = [("10:00", "12:00")]
        available_videos = [
            {"path": "/v1.mp4", "duration": 1800, "tags": ["action"], "collection": {"id": "col1"}},
            {"path": "/v2.mp4", "duration": 1800, "tags": ["comedy"], "collection": {"id": "col2"}},
            {"path": "/v3.mp4", "duration": 1800, "tags": ["action", "comedy"], "collection": {"id": "col3"}}
        ]
        
        # Filter to only action tag
        config = GapFillerConfig(enabled=True, source="tags", tags=["action"])
        entries = fill_gaps_with_random(gaps, available_videos, config, [], "test_channel")
        
        # All entries should have action tag
        for entry in entries:
            # Get the video that was selected
            video = next((v for v in available_videos if v["path"] == entry["file"]), None)
            assert video is not None and "action" in video["tags"]
    
    def test_fill_gaps_with_excluded_tags(self):
        """Test gap filling respects excluded tags"""
        from akiratv.daypart_scheduler import GapFillerConfig, fill_gaps_with_random
        
        # Use a 2-hour gap with 2 videos to ensure we don't exhaust candidates
        gaps = [("10:00", "12:00")]
        available_videos = [
            {"path": "/horror1.mp4", "duration": 3600, "tags": ["horror"], "collection": {"id": "c1"}},
            {"path": "/action1.mp4", "duration": 3600, "tags": ["action"], "collection": {"id": "c2"}}
        ]
        
        # Exclude horror
        config = GapFillerConfig(enabled=True, source="all", excluded_tags=["horror"], respect_24h_norepeat=False)
        entries = fill_gaps_with_random(gaps, available_videos, config, [], "test_channel")
        
        # No horror videos should be selected
        for entry in entries:
            assert "/horror" not in entry["file"]
    
    def test_generate_daypart_schedule_full(self):
        """Test complete daypart schedule generation"""
        from akiratv.daypart_scheduler import generate_daypart_schedule, TimeBlock, generate_block_schedule
        from datetime import date
        
        daypart_config = {
            "daypart_config": {
                "time_blocks": [
                    {
                        "block_id": "block1",
                        "start_time": "06:00",
                        "end_time": "10:00",
                        "content_type": "tag",
                        "content_value": "kids",
                        "duration_seconds": 14400
                    }
                ],
                "marathons": [],
                "gap_filler": {
                    "enabled": True,
                    "source": "all",
                    "excluded_tags": [],
                    "respect_24h_norepeat": True,
                    "shuffle": True
                }
            }
        }
        
        available_videos = [
            {"path": "/k1.mp4", "duration": 7200, "tags": ["kids"], "collection": {"id": "c1"}},
            {"path": "/k2.mp4", "duration": 7200, "tags": ["kids"], "collection": {"id": "c1"}},
            {"path": "/a1.mp4", "duration": 3600, "tags": ["action"], "collection": {"id": "c2"}}
        ]
        
        entries = generate_daypart_schedule(daypart_config, available_videos, "test_channel", date.today())
        
        # Should have entries - either from time block or gap filler
        assert len(entries) > 0
    
    def test_generate_daypart_schedule_marathon_day(self):
        """Test daypart schedule on marathon day"""
        from akiratv.daypart_scheduler import generate_daypart_schedule
        from datetime import date
        
        # Use a fixed date that's a Friday
        test_date = date(2025, 1, 3)  # This is a Friday
        
        daypart_config = {
            "daypart_config": {
                "time_blocks": [
                    {
                        "block_id": "block1",
                        "start_time": "06:00",
                        "end_time": "10:00",
                        "content_type": "tag",
                        "content_value": "kids",
                        "duration_seconds": 14400
                    }
                ],
                "marathons": [
                    {
                        "tag": "80s",
                        "days": ["friday"],
                        "enabled": True,
                        "shuffle": True,
                        "no_repeat_24h": True
                    }
                ],
                "gap_filler": {
                    "enabled": True,
                    "source": "all"
                }
            }
        }
        
        # Use longer videos to fill more of the 24-hour period
        available_videos = [
            {"path": "/v1.mp4", "duration": 28800, "tags": ["80s"], "collection": {"id": "c1"}},  # 8 hours
            {"path": "/v2.mp4", "duration": 28800, "tags": ["80s"], "collection": {"id": "c1"}},  # 8 hours
            {"path": "/v3.mp4", "duration": 28800, "tags": ["80s"], "collection": {"id": "c1"}},  # 8 hours
        ]
        
        entries = generate_daypart_schedule(daypart_config, available_videos, "test_channel", test_date)
        
        # Handle both tuple and list returns (backward compatibility)
        if isinstance(entries, tuple):
            entries = entries[0]
        
        # Should have entries from marathon on Friday
        assert len(entries) > 0
        # At least some entries should be marathon entries
        marathon_entries = [e for e in entries if e.get("source") == "daypart_marathon"]
        assert len(marathon_entries) > 0, f"Expected marathon entries but got: {entries}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
