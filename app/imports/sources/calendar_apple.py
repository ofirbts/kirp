from app.imports.base import BaseImporter, ImportChunk
from app.imports.utils.ics_parser import extract_ics_field

class AppleCalendarImporter(BaseImporter):
    def parse(self, raw_data: str):
        for event in raw_data.split("BEGIN:VEVENT"):
            if "SUMMARY" not in event:
                continue
            summary = extract_ics_field(event, "SUMMARY")
            start = extract_ics_field(event, "DTSTART")
            end = extract_ics_field(event, "DTEND")
            content = f"Event: {summary} ({start} - {end})"
            yield ImportChunk(content=content, source="apple_calendar_import")
