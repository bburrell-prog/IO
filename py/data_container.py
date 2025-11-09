#!/usr/bin/env python3
"""
Data Container Module
Aggregates and manages all throughput end-state data from analysis cycles.
Provides a centralized storage system for screenshots, reports, statistics, and AI responses.
"""
import json
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

@dataclass
class AnalysisCycle:
    """Represents a complete analysis cycle with all end-state data."""
    cycle_id: int
    timestamp: str
    screenshot_path: Optional[str] = None
    report_path: Optional[str] = None
    analysis_report: Optional[Dict[str, Any]] = None
    statistics: Optional[Dict[str, Any]] = None
    chatgpt_response: Optional[str] = None
    error_message: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

class DataContainer:
    """Centralized container for all analysis cycle data with real-time updates."""

    def __init__(self, storage_path: str = "data_container.json"):
        """Initialize the data container."""
        self.storage_path = Path(storage_path)
        self.cycles: Dict[int, AnalysisCycle] = {}
        self.listeners: List[callable] = []
        self.lock = threading.RLock()
        self._load_data()
        logger.info(f"DataContainer initialized with {len(self.cycles)} existing cycles")

    def _load_data(self):
        """Load existing data from storage file."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cycle_data in data.get('cycles', []):
                        cycle = AnalysisCycle(**cycle_data)
                        self.cycles[cycle.cycle_id] = cycle
            except Exception as e:
                logger.error(f"Failed to load data container: {e}")

    def _save_data(self):
        """Save current data to storage file."""
        try:
            data = {
                'cycles': [asdict(cycle) for cycle in self.cycles.values()],
                'last_updated': datetime.now().isoformat(),
                'total_cycles': len(self.cycles)
            }
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save data container: {e}")

    def add_cycle(self, cycle_data: Dict[str, Any]) -> int:
        """Add a new analysis cycle to the container."""
        with self.lock:
            # Generate cycle ID
            cycle_id = max(self.cycles.keys(), default=0) + 1

            # Create AnalysisCycle object
            cycle = AnalysisCycle(
                cycle_id=cycle_id,
                **cycle_data
            )

            # Store the cycle
            self.cycles[cycle_id] = cycle

            # Save to disk
            self._save_data()

            # Notify listeners
            self._notify_listeners('cycle_added', cycle)

            logger.info(f"Added cycle {cycle_id} to data container")
            return cycle_id

    def update_cycle(self, cycle_id: int, updates: Dict[str, Any]):
        """Update an existing cycle with new data."""
        with self.lock:
            if cycle_id in self.cycles:
                cycle = self.cycles[cycle_id]
                for key, value in updates.items():
                    if hasattr(cycle, key):
                        setattr(cycle, key, value)

                # Update timestamp
                cycle.created_at = datetime.now().isoformat()

                # Save to disk
                self._save_data()

                # Notify listeners
                self._notify_listeners('cycle_updated', cycle)

                logger.info(f"Updated cycle {cycle_id}")
            else:
                logger.warning(f"Attempted to update non-existent cycle {cycle_id}")

    def get_cycle(self, cycle_id: int) -> Optional[AnalysisCycle]:
        """Retrieve a specific cycle by ID."""
        with self.lock:
            return self.cycles.get(cycle_id)

    def get_all_cycles(self) -> List[AnalysisCycle]:
        """Get all cycles sorted by ID (newest first)."""
        with self.lock:
            return sorted(self.cycles.values(), key=lambda c: c.cycle_id, reverse=True)

    def get_cycles_in_range(self, start_id: int, end_id: int) -> List[AnalysisCycle]:
        """Get cycles within a specific ID range."""
        with self.lock:
            return [cycle for cycle in self.cycles.values()
                   if start_id <= cycle.cycle_id <= end_id]

    def search_cycles(self, query: str, fields: List[str] = None) -> List[AnalysisCycle]:
        """Search cycles by text query in specified fields."""
        if fields is None:
            fields = ['chatgpt_response', 'error_message']

        query_lower = query.lower()
        results = []

        with self.lock:
            for cycle in self.cycles.values():
                cycle_dict = asdict(cycle)
                for field in fields:
                    value = cycle_dict.get(field, '')
                    if value and query_lower in str(value).lower():
                        results.append(cycle)
                        break

        return results

    def get_statistics_summary(self) -> Dict[str, Any]:
        """Generate summary statistics across all cycles."""
        with self.lock:
            total_cycles = len(self.cycles)
            if total_cycles == 0:
                return {'total_cycles': 0}

            cycles_with_errors = sum(1 for c in self.cycles.values() if c.error_message)
            cycles_with_responses = sum(1 for c in self.cycles.values() if c.chatgpt_response)

            # Calculate average processing time
            processing_times = [c.processing_time for c in self.cycles.values() if c.processing_time]
            avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else None

            return {
                'total_cycles': total_cycles,
                'cycles_with_errors': cycles_with_errors,
                'cycles_with_responses': cycles_with_responses,
                'error_rate': cycles_with_errors / total_cycles if total_cycles > 0 else 0,
                'response_rate': cycles_with_responses / total_cycles if total_cycles > 0 else 0,
                'average_processing_time': avg_processing_time,
                'last_updated': max((c.created_at for c in self.cycles.values()), default=None)
            }

    def add_listener(self, callback: callable):
        """Add a listener for data container events."""
        with self.lock:
            self.listeners.append(callback)

    def remove_listener(self, callback: callable):
        """Remove a listener."""
        with self.lock:
            if callback in self.listeners:
                self.listeners.remove(callback)

    def _notify_listeners(self, event_type: str, data: Any):
        """Notify all listeners of an event."""
        for listener in self.listeners:
            try:
                listener(event_type, data)
            except Exception as e:
                logger.error(f"Error notifying listener: {e}")

    def cleanup_old_cycles(self, max_cycles: int = 1000):
        """Remove oldest cycles if we exceed the maximum."""
        with self.lock:
            if len(self.cycles) > max_cycles:
                # Sort by ID and keep the newest
                sorted_cycles = sorted(self.cycles.items(), key=lambda x: x[1].cycle_id, reverse=True)
                to_keep = dict(sorted_cycles[:max_cycles])
                removed_count = len(self.cycles) - len(to_keep)

                self.cycles = to_keep
                self._save_data()

                logger.info(f"Cleaned up {removed_count} old cycles, keeping {len(self.cycles)}")
                return removed_count

        return 0

    def export_to_json(self, filepath: str):
        """Export all data to a JSON file."""
        with self.lock:
            data = {
                'export_timestamp': datetime.now().isoformat(),
                'cycles': [asdict(cycle) for cycle in self.cycles.values()],
                'summary': self.get_statistics_summary()
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

            logger.info(f"Exported {len(self.cycles)} cycles to {filepath}")

    def import_from_json(self, filepath: str):
        """Import data from a JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            imported_count = 0
            for cycle_data in data.get('cycles', []):
                # Skip if cycle ID already exists
                cycle_id = cycle_data.get('cycle_id')
                if cycle_id and cycle_id not in self.cycles:
                    cycle = AnalysisCycle(**cycle_data)
                    self.cycles[cycle_id] = cycle
                    imported_count += 1

            if imported_count > 0:
                self._save_data()
                logger.info(f"Imported {imported_count} cycles from {filepath}")

            return imported_count

        except Exception as e:
            logger.error(f"Failed to import from {filepath}: {e}")
            return 0