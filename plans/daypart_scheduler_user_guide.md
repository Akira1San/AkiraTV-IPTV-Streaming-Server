# Daypart Scheduler User Guide

A tutorial on how to use the Daypart Scheduler feature in AkiraTV to create broadcast-style programming schedules.

---

## What is the Daypart Scheduler?

The Daypart Scheduler allows you to create **time-based programming blocks** for your channel. Instead of random or sequential scheduling for the entire day, you can now:

- **Schedule specific content** to exact time slots (e.g., "Kids shows from 6 AM to 10 AM")
- **Use tags** to automatically fill time blocks with related content (e.g., "Horror movies from 8 PM to midnight")
- **Run marathons** - 24-hour themed content blocks on specific days
- **Fill gaps** automatically with random content

---

## Quick Start Example

### Example: A Typical TV Channel Schedule

Let's say you want to create a channel with this programming:

| Time Slot | Content Type | Content |
|-----------|--------------|---------|
| 00:00 - 06:00 | Random from all videos | Gap filler |
| 06:00 - 10:00 | Tag: "kids" | Kids cartoons |
| 10:00 - 12:00 | Tag: "documentary" | Documentaries |
| 12:00 - 14:00 | Specific Video | "The Big Lunch" show |
| 14:00 - 17:00 | Tag: "drama" | Drama series |
| 17:00 - 20:00 | Tag: "comedy" | Comedy shows |
| 20:00 - 24:00 | Tag: "horror" | Horror movies |
| Friday: All Day | Tag: "80s" | 80s Marathon! |

Here's how to set it up:

---

## Step-by-Step Tutorial

### Step 1: Open the Schedule Programming Tab

In the AkiraTV interface, look for the **"Schedule Programming"** tab in the Added Videos panel (right side of the screen).

```
[Collections] [Standby] [Added Videos] [Schedule Programming]
```

Click on it to open the Daypart Scheduler interface.

---

### Step 2: Create Time Blocks

Time blocks define what content plays during specific time periods.

#### Adding a New Block

1. Click the **[+] Add Block** button
2. A dialog will appear with these options:

```
┌─────────────────────────────────────────────┐
│ Edit Time Block                             │
├─────────────────────────────────────────────┤
│ Start Time:  [06:00]    End Time: [10:00]  │
│                                             │
│ Content Type: ○ Specific Video  ○ Tag      │
│                                             │
│ If Tag:                                    │
│   Tag: [kids            ▼]                 │
│                                             │
│ Preview Duration: 4 hours (14400 seconds)  │
│                                             │
│ [Cancel]  [Save]                           │
```

#### Block Types

**1. Tag-Based Block (Green)**
- Select "Tag" as content type
- Choose a tag from the dropdown (e.g., "kids", "horror", "documentary")
- The scheduler will randomly select videos with that tag to fill the time block

**2. Specific Video Block (Blue)**
- Select "Specific Video" as content type
- Search for and select a specific video file
- That exact video will play during the block

**3. Marathon Block (Red)**
- Set up separately in the Marathon panel
- Runs for 24 hours on selected days

---

### Step 3: Setting Up Marathon Days

Marathons override your regular time blocks on specific days.

1. Go to the **Marathon Scheduling** panel
2. Select a tag (e.g., "80s")
3. Check the days you want the marathon to run:
   - [ ] Monday [x] Tuesday [ ] Wednesday [ ] Thursday [x] Friday [ ] Saturday [ ] Sunday
4. Options:
   - `[✓] Fill entire 24-hour period` - Plays tag content all day
   - `[✓] Shuffle within marathon` - Randomizes video order
   - `[✓] No repeats in 24h` - Won't replay videos within 24 hours

**Example**: Selecting "80s" tag + Friday + Saturday means every Friday and Saturday will be all-80s, all-day marathons!

---

### Step 4: Configure Gap Filler

Gap filler fills any time slots you haven't scheduled with content.

In the **Gap Filler Settings** panel:

1. **Enable gap filling** - Check this box
2. **Source** - Choose where to pull random content:
   - "All videos" - Any video in your library
   - "Specific collections" - Only from selected collections
   - "Specific tags" - Only from chosen tags
3. **Exclusions** - Click "Edit..." to exclude certain tags (e.g., exclude horror from morning slots)
4. **Options**:
   - `[✓] Respect 24-hour no-repeat` - Don't play same video twice in a day
   - `[✓] Shuffle selection` - Randomize order

---

### Step 5: Preview Your Schedule

Click **[Generate Preview]** to see what your schedule looks like.

The preview shows:
- A visual timeline with colored blocks
- A text listing of each scheduled segment
- Total blocks and gap filler segments

```
=== SCHEDULE PREVIEW ===
00:00 - 06:00 [RANDOM] Random from all videos
06:00 - 10:00 [TAG:kids] Random kids content
10:00 - 12:00 [TAG:documentary] Random documentary
12:00 - 14:00 [VIDEO] The Big Lunch Show.mp4
14:00 - 17:00 [TAG:drama] Random drama
17:00 - 20:00 [TAG:comedy] Random comedy
20:00 - 24:00 [TAG:horror] Random horror

Total blocks: 7 | Gap filler segments: 1
```

---

### Step 6: Save Your Schedule

Click **[Save Schedule]** to apply your daypart configuration.

Your schedule will now generate according to the time blocks you've defined!

---

## Common Use Cases

### Use Case 1: Morning Kids Block

```
Start: 06:00  End: 10:00
Content Type: Tag
Tag: kids
```

Result: Every day from 6 AM to 10 AM, random kids content plays.

---

### Use Case 2: Prime Time Specific Show

```
Start: 20:00  End: 22:00
Content Type: Specific Video
Video: "Tonight's Special Movie.mp4"
```

Result: Every day at 8 PM, this specific movie plays.

---

### Use Case 3: Friday Night Horror

**Marathon Setup:**
- Tag: horror
- Days: Friday
- Fill entire 24-hour: Yes
- No repeats: Yes

**Time Blocks (for other days):**
```
20:00 - 24:00 | Tag: horror
```

Result: Every Friday is a 24-hour horror marathon. Other days, horror plays 8 PM-midnight.

---

### Use Case 4: Weekday vs Weekend Different Programming

**Time Blocks (apply to Mon-Thu, Sun):**
```
06:00 - 09:00   | Tag: kids
09:00 - 12:00   | Tag: documentary
12:00 - 14:00   | Tag: comedy
14:00 - 18:00   | Tag: drama
18:00 - 24:00   | Tag: movie
```

**Marathon (Friday):**
- Tag: 80s
- Days: Friday

**Marathon (Saturday):**
- Tag: anime
- Days: Saturday

**Gap Filler:**
- Enabled
- Source: All videos

Result: 
- Mon-Thu, Sun: Follow the time blocks
- Friday: Full 80s marathon
- Saturday: Full anime marathon
- Any gaps filled with random content

---

## Tips and Best Practices

### 1. Plan Your Gaps

Always enable gap filler or create a time block that covers the entire day to avoid dead air.

**Good:**
```
00:00 - 24:00 | Tag: movies  (or gap filler as backup)
```

**Avoid:**
```
06:00 - 10:00 | Tag: kids
(no other blocks = 10 PM - 6 AM = dead air!)
```

---

### 2. Test Your Tags

Before creating time blocks, make sure your tags actually have content:

1. Go to Collections
2. Check which videos have which tags
3. Note: A video can have multiple tags

---

### 3. Use Overnight Blocks

You can create blocks that span midnight!

```
Start: 22:00  End: 02:00
Content: Tag: horror
```

This creates a 4-hour horror block from 10 PM to 2 AM.

---

### 4. Marathon Considerations

- Make sure your tag has **enough videos** for 24 hours
- If you have 10 hours of videos but enable 24-hour marathon, videos will repeat
- Enable "No repeats in 24h" to prevent immediate repeats

---

### 5. Video Duration Matters

If a 2-hour video is placed in a 1-hour block, the video will play completely. The next block will start after the video ends (overlapping the nominal start time).

---

## Troubleshooting

### "No videos found for tag"

**Problem:** The tag you selected has no videos.

**Solution:**
- Check your collections to ensure videos have that tag
- Add more videos with that tag
- Use a different tag

### "Schedule has gaps"

**Problem:** Time blocks don't cover the full 24 hours.

**Solution:**
- Enable gap filler, OR
- Add more time blocks to cover the day, OR
- Create one block from 00:00-24:00

### "Marathon not showing"

**Problem:** Marathon isn't playing on the selected day.

**Solution:**
- Ensure "enabled" checkbox is checked for the marathon
- Verify the day is checked in the day selection
- Check that videos exist with the marathon tag

### "Videos repeating too much"

**Problem:** Same videos playing frequently.

**Solution:**
- Enable "Respect 24-hour no-repeat" in gap filler
- Enable "No repeats in 24h" in marathon settings
- Add more videos to your library

---

## Converting from Simple Scheduler

If you were using the old simple scheduler:

1. Your existing schedule will continue to work (backward compatible)
2. To switch to Daypart mode:
   - Open Schedule Programming tab
   - Create your time blocks
   - Save the schedule
   - The old "simple" schedule will be replaced

**Note:** This is a one-way conversion. Save a backup of your simple schedule JSON if you need to revert.

---

## Keyboard Shortcuts

- `Ctrl+S` - Save schedule
- `Ctrl+P` - Generate preview
- `Delete` - Remove selected block
- `Ctrl+N` - New time block

---

## Need More Help?

- Check the AkiraTV documentation
- Ask in the community forums
- Review the technical proposal for detailed specifications

---

**Enjoy creating your custom TV schedules!**