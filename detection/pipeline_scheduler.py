"""
Scheduler and Fault Tolerance System

Implements continuous pipeline execution with error recovery.

Implements Step 12 of the oil spill detection pipeline.
"""

import logging
import time
import os
from typing import Optional, Dict, Callable
from datetime import datetime, timedelta
from pathlib import Path
import json
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class PipelineScheduler(ABC):
    """Abstract base class for pipeline schedulers"""
    
    @abstractmethod
    def should_run(self) -> bool:
        """Determine if pipeline should run now"""
        pass
    
    @abstractmethod
    def next_run_in(self) -> float:
        """Return seconds until next scheduled run"""
        pass


class IntervalScheduler(PipelineScheduler):
    """
    Simple interval-based scheduler.
    
    Runs pipeline every N hours.
    """
    
    def __init__(self, interval_hours: float = 24.0):
        """
        Initialize scheduler.
        
        Args:
            interval_hours: Run interval in hours
        """
        self.interval_hours = interval_hours
        self.interval_seconds = interval_hours * 3600
        self.last_run_time: Optional[datetime] = None
    
    def should_run(self) -> bool:
        """Check if enough time has passed since last run"""
        if self.last_run_time is None:
            return True  # First run
        
        elapsed = datetime.now() - self.last_run_time
        return elapsed.total_seconds() >= self.interval_seconds
    
    def next_run_in(self) -> float:
        """Return seconds until next run"""
        if self.last_run_time is None:
            return 0.0
        
        elapsed = datetime.now() - self.last_run_time
        remaining = self.interval_seconds - elapsed.total_seconds()
        return max(0.0, remaining)
    
    def mark_run(self):
        """Mark that a run has completed"""
        self.last_run_time = datetime.now()


class TimeWindowScheduler(PipelineScheduler):
    """
    Schedule runs within specific time windows.
    
    Useful for avoiding peak hours or running during specific times.
    """
    
    def __init__(
        self,
        interval_hours: float = 24.0,
        start_hour: int = 0,
        end_hour: int = 23
    ):
        """
        Initialize scheduler.
        
        Args:
            interval_hours: Base run interval
            start_hour: Start hour (0-23)
            end_hour: End hour (0-23)
        """
        self.interval_scheduler = IntervalScheduler(interval_hours)
        self.start_hour = start_hour
        self.end_hour = end_hour
    
    def should_run(self) -> bool:
        """Check if within time window and interval elapsed"""
        if not self.interval_scheduler.should_run():
            return False
        
        hour = datetime.now().hour
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour <= self.end_hour
        else:
            # Window spans midnight
            return hour >= self.start_hour or hour <= self.end_hour
    
    def next_run_in(self) -> float:
        """Return seconds until next run"""
        now = datetime.now()
        hour = now.hour
        
        # Check if currently in window
        if self.start_hour <= self.end_hour:
            in_window = self.start_hour <= hour <= self.end_hour
        else:
            in_window = hour >= self.start_hour or hour <= self.end_hour
        
        if not in_window:
            # Calculate time to next window
            if hour < self.start_hour:
                next_window = now.replace(hour=self.start_hour, minute=0, second=0)
            else:
                next_window = (now + timedelta(days=1)).replace(hour=self.start_hour, minute=0, second=0)
            
            return (next_window - now).total_seconds()
        
        # In window, check interval
        return self.interval_scheduler.next_run_in()
    
    def mark_run(self):
        """Mark that a run has completed"""
        self.interval_scheduler.mark_run()


class FaultTolerantRunner:
    """
    Run pipeline with fault tolerance and recovery.
    
    Features:
    - Automatic retry on failure
    - Exponential backoff
    - Error logging and reporting
    - State persistence
    """
    
    def __init__(
        self,
        pipeline,
        scheduler: PipelineScheduler,
        max_retries: int = 3,
        state_file: str = "pipeline_state.json"
    ):
        """
        Initialize fault-tolerant runner.
        
        Args:
            pipeline: OilSpillDetectionPipeline instance
            scheduler: Scheduler instance
            max_retries: Maximum retry attempts
            state_file: Path to state persistence file
        """
        self.pipeline = pipeline
        self.scheduler = scheduler
        self.max_retries = max_retries
        self.state_file = Path(state_file)
        
        self.run_count = 0
        self.error_count = 0
        self.success_count = 0
        
        self._load_state()
    
    def _load_state(self):
        """Load saved state from file"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r') as f:
                    state = json.load(f)
                
                self.run_count = state.get("run_count", 0)
                self.error_count = state.get("error_count", 0)
                self.success_count = state.get("success_count", 0)
                
                if "last_run_time" in state:
                    last_run = datetime.fromisoformat(state["last_run_time"])
                    self.scheduler.last_run_time = last_run
                    if hasattr(self.scheduler, 'interval_scheduler'):
                        self.scheduler.interval_scheduler.last_run_time = last_run
                
                logger.info(f"✓ Loaded runner state from {self.state_file}")
            
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")
    
    def _save_state(self):
        """Save state to file"""
        try:
            state = {
                "run_count": self.run_count,
                "error_count": self.error_count,
                "success_count": self.success_count,
                "last_run_time": datetime.now().isoformat()
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
        
        except Exception as e:
            logger.error(f"Failed to save state: {e}")
    
    def run_with_retry(self) -> Dict:
        """
        Run pipeline with automatic retry on failure.
        
        Returns:
            Pipeline results dictionary
        """
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Pipeline run attempt {attempt + 1}/{self.max_retries} "
                    f"(Run #{self.run_count + 1})"
                )
                
                results = self.pipeline.run()
                
                if results.get("status") == "success":
                    self.success_count += 1
                    self.run_count += 1
                    self._save_state()
                    return results
                
                elif results.get("status") == "no_new_data":
                    logger.info("No new data, skipping run")
                    self.run_count += 1
                    self._save_state()
                    return results
                
                else:
                    # Pipeline returned but with error status
                    raise Exception(f"Pipeline failed: {results.get('error', 'Unknown error')}")
            
            except Exception as e:
                logger.error(f"Pipeline attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    # Exponential backoff: wait 2^attempt minutes
                    wait_seconds = (2 ** attempt) * 60
                    logger.info(f"Retrying in {wait_seconds/60:.1f} minutes...")
                    time.sleep(wait_seconds)
                else:
                    self.error_count += 1
                    self.run_count += 1
                    self._save_state()
                    
                    return {
                        "status": "failed",
                        "error": str(e),
                        "attempts": self.max_retries,
                        "timestamp": datetime.now().isoformat()
                    }
        
        return {
            "status": "failed",
            "error": "Max retries exceeded"
        }


class PipelineLoop:
    """
    Continuous loop for pipeline execution.
    
    Runs scheduler in an infinite loop with graceful shutdown.
    """
    
    def __init__(
        self,
        runner: FaultTolerantRunner,
        poll_interval_seconds: float = 60.0
    ):
        """
        Initialize pipeline loop.
        
        Args:
            runner: FaultTolerantRunner instance
            poll_interval_seconds: How often to check scheduler
        """
        self.runner = runner
        self.poll_interval_seconds = poll_interval_seconds
        self.running = False
        self.run_history = []
    
    def start(self, max_runs: Optional[int] = None):
        """
        Start pipeline loop.
        
        Args:
            max_runs: Optional maximum number of runs before stopping
        """
        self.running = True
        run_num = 0
        
        logger.info("="*60)
        logger.info("STARTING PIPELINE LOOP")
        logger.info("="*60)
        
        try:
            while self.running:
                if max_runs and run_num >= max_runs:
                    logger.info(f"Reached max runs ({max_runs}), stopping")
                    break
                
                # Check if should run
                if self.runner.scheduler.should_run():
                    logger.info(
                        f"\n{'='*60}\n"
                        f"SCHEDULED RUN TRIGGERED\n"
                        f"{'='*60}"
                    )
                    
                    # Run pipeline
                    results = self.runner.run_with_retry()
                    self.run_history.append(results)
                    
                    if results.get("status") == "success":
                        self.runner.scheduler.mark_run()
                        run_num += 1
                
                # Check next run time
                next_run_in = self.runner.scheduler.next_run_in()
                
                if next_run_in > 0:
                    logger.info(
                        f"Next run in {next_run_in/3600:.1f} hours "
                        f"({next_run_in/60:.0f} minutes)"
                    )
                
                # Sleep until next check
                time.sleep(self.poll_interval_seconds)
        
        except KeyboardInterrupt:
            logger.info("\n✓ Pipeline loop stopped by user")
        
        except Exception as e:
            logger.error(f"Pipeline loop encountered error: {e}")
        
        finally:
            self.running = False
            self._print_summary()
    
    def stop(self):
        """Stop the pipeline loop"""
        self.running = False
    
    def _print_summary(self):
        """Print execution summary"""
        total_runs = len(self.run_history)
        successful = sum(1 for r in self.run_history if r.get("status") == "success")
        failed = sum(1 for r in self.run_history if r.get("status") == "failed")
        
        logger.info("="*60)
        logger.info("PIPELINE LOOP SUMMARY")
        logger.info("="*60)
        logger.info(f"Total runs: {total_runs}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        
        if self.run_history:
            total_detections = sum(
                len(r.get("tile_results", []))
                for r in self.run_history
                if r.get("status") == "success"
            )
            logger.info(f"Total tiles processed: {total_detections}")


def create_scheduler(
    scheduler_type: str = "interval",
    **kwargs
) -> PipelineScheduler:
    """
    Factory function to create scheduler.
    
    Args:
        scheduler_type: "interval" or "time_window"
        **kwargs: Arguments for specific scheduler
    
    Returns:
        Configured scheduler
    """
    if scheduler_type == "interval":
        interval = kwargs.get("interval_hours", 24.0)
        return IntervalScheduler(interval)
    
    elif scheduler_type == "time_window":
        interval = kwargs.get("interval_hours", 24.0)
        start = kwargs.get("start_hour", 0)
        end = kwargs.get("end_hour", 23)
        return TimeWindowScheduler(interval, start, end)
    
    else:
        logger.warning(f"Unknown scheduler type: {scheduler_type}, using interval")
        return IntervalScheduler()


def start_pipeline_loop(
    pipeline,
    interval_hours: float = 24.0,
    max_retries: int = 3,
    poll_interval: float = 60.0,
    max_runs: Optional[int] = None,
    state_file: str = "pipeline_state.json"
):
    """
    Start oil spill detection pipeline in continuous loop.
    
    Implements Step 12 of the pipeline.
    
    Args:
        pipeline: OilSpillDetectionPipeline instance
        interval_hours: Run interval
        max_retries: Maximum retries per run
        poll_interval: Polling interval in seconds
        max_runs: Optional maximum runs before stopping
        state_file: State persistence file
    """
    # Create scheduler
    scheduler = create_scheduler("interval", interval_hours=interval_hours)
    
    # Create fault-tolerant runner
    runner = FaultTolerantRunner(
        pipeline=pipeline,
        scheduler=scheduler,
        max_retries=max_retries,
        state_file=state_file
    )
    
    # Create and start loop
    loop = PipelineLoop(runner, poll_interval_seconds=poll_interval)
    
    try:
        loop.start(max_runs=max_runs)
    except KeyboardInterrupt:
        logger.info("Shutting down pipeline loop...")
        loop.stop()
