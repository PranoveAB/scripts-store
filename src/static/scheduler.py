# src/static/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
from loguru import logger
from src.database.db import SessionLocal
from src.service.models.db_model import Script
from src.static.executor import ScriptExecutor

def execute_scheduled_script(script_name: str, project_name: str):
    """
    Global function for script execution that APScheduler can serialize.
    This will be called by the scheduler.
    """
    log = logger.bind(log_type="schedule")
    log.info(f"Starting scheduled execution of {script_name}")
    
    executor = ScriptExecutor(script_name, project_name)
    try:
        executor.execute()
        log.info(f"Completed scheduled execution of {script_name}")
    except Exception as e:
        log.error(f"Failed scheduled execution of {script_name}: {str(e)}")
    # finally:
    #     executor.cleanup()

class ScriptScheduler:
    def __init__(self):
        # Initialize scheduler with SQLite job store for persistence
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore('sqlalchemy', url='sqlite:////opt/data/jobs.sqlite')  # Absolute path
        self.log = logger.bind(log_type="schedule")

    def start(self):
        """Start the scheduler and restore any existing jobs"""
        if not self.scheduler.running:
            self.scheduler.start()
            self._restore_jobs()
            self.log.info("Scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.log.info("Scheduler stopped")

    def schedule_script(self, script_name: str, project_name: str, cron_expression: str):
        """Schedule a script to run on a cron schedule"""
        try:
            job_id = f"{project_name}_{script_name}"
            self.log.info(f"Scheduling {script_name} with cron: {cron_expression}")

            # Remove existing job if it exists
            if job_id in [job.id for job in self.scheduler.get_jobs()]:
                self.scheduler.remove_job(job_id)
                self.log.info(f"Removed existing job for {script_name}")

            # Add new job
            trigger = CronTrigger.from_crontab(cron_expression)
            
            self.scheduler.add_job(
                execute_scheduled_script,
                trigger=trigger,
                args=[script_name, project_name],
                id=job_id,
                name=f"{project_name} - {script_name}",
                replace_existing=True,
                misfire_grace_time=None  # Allow misfired jobs to run immediately
            )

            self.log.info(f"Successfully scheduled {script_name}")
            return True

        except Exception as e:
            self.log.error(f"Error scheduling {script_name}: {str(e)}")
            raise

    def _restore_jobs(self):
        """Restore scheduled jobs from the database"""
        db = SessionLocal()
        try:
            # Get all active scripts with cron expressions
            active_scripts = db.query(Script).filter(
                Script.is_active == True,
                Script.cron_expression.isnot(None)
            ).all()

            for script in active_scripts:
                try:
                    self.schedule_script(
                        script.script_name,
                        script.project_name,
                        script.cron_expression
                    )
                except Exception as e:
                    self.log.error(f"Error restoring job for {script.script_name}: {str(e)}")

            self.log.info(f"Restored {len(active_scripts)} scheduled jobs")

        except Exception as e:
            self.log.error(f"Error restoring jobs: {str(e)}")
        finally:
            db.close()

# Create global scheduler instance
scheduler = ScriptScheduler()