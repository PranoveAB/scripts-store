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
    executor = ScriptExecutor(script_name, project_name)
    try:
        executor.execute()
    finally:
        executor.cleanup()

class ScriptScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_jobstore('sqlalchemy', url='sqlite:///jobs.sqlite')

    def start(self):
        """Start the scheduler and restore any existing jobs"""
        if not self.scheduler.running:
            self.scheduler.start()
            self._restore_jobs()
            logger.info("Scheduler started and jobs restored")

    def stop(self):
        """Stop the scheduler"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler stopped")

    def schedule_script(self, script_name: str, project_name: str, cron_expression: str):
        """Schedule a script to run on a cron schedule"""
        try:
            job_id = f"{project_name}_{script_name}"

            # Remove existing job if it exists
            if job_id in [job.id for job in self.scheduler.get_jobs()]:
                self.scheduler.remove_job(job_id)

            # Add new job using the global function
            trigger = CronTrigger.from_crontab(cron_expression)
            
            self.scheduler.add_job(
                execute_scheduled_script,  # Using the global function
                trigger=trigger,
                args=[script_name, project_name],
                id=job_id,
                name=f"{project_name} - {script_name}",
                replace_existing=True,
                misfire_grace_time=None  # Allow misfired jobs to run immediately
            )

            logger.info(f"Scheduled script {script_name} with cron: {cron_expression}")
            return True

        except Exception as e:
            logger.error(f"Error scheduling script: {str(e)}")
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
                    logger.error(f"Error restoring job for {script.script_name}: {str(e)}")

            logger.info(f"Restored {len(active_scripts)} scheduled jobs")

        except Exception as e:
            logger.error(f"Error restoring jobs: {str(e)}")
        finally:
            db.close()

# Create global scheduler instance
scheduler = ScriptScheduler()