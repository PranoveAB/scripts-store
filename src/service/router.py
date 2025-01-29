# src/service/router.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.service.models.db_model import Script
from src.static.executor import ScriptExecutor
from src.static.scheduler import scheduler
from src.static.package_manager import PackageManager
from src.utils.validator import ScriptValidator
from src.service.models.register_model import ScriptRegistration
from datetime import datetime
import os
import zipfile
from loguru import logger
import shutil
from croniter import croniter

router = APIRouter()

@router.post("/scripts/register")
async def register_script(
    registration: ScriptRegistration,
    db: Session = Depends(get_db)
):
    """Register a script deployed by GitHub Actions"""
    log = logger.bind(
        log_type="execute",
        script_name=registration.script_name,
        project_name=registration.project_name
    )
    
    try:
        script_path = f"/opt/scripts-store/{registration.project_name}/{registration.script_name}"
        
        # Verify script directory exists
        if not os.path.exists(script_path):
            raise HTTPException(
                status_code=400,
                detail="Script directory not found. Ensure copy step completed successfully."
            )
            
        # Validate script
        log.info(f"Validating script at {script_path}")
        validator = ScriptValidator(registration.project_name, registration.script_name)
        is_valid, message = validator.validate_all()
        
        if not is_valid:
            raise HTTPException(
                status_code=400,
                detail=f"Validation failed: {message}"
            )

        # Handle existing script version
        existing_script = db.query(Script).filter(
            Script.project_name == registration.project_name,
            Script.script_name == registration.script_name,
            Script.is_active == True
        ).first()

        if existing_script:
            # Clean up old version's environment
            old_package_manager = PackageManager(registration.project_name, registration.script_name)
            old_package_manager.cleanup_environment()
            log.info(f"Cleaned up old version environment")
            
            # Increment version
            version_parts = existing_script.version.split('.')
            new_version = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"
            
            # Deactivate old version
            existing_script.is_active = False
            db.add(existing_script)
            log.info(f"Deactivated old version {existing_script.version}")
        else:
            new_version = "1.0.0"

        # Validate cron expression if provided
        if registration.cron_expression:
            if not croniter.is_valid(registration.cron_expression):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid cron expression"
                )
            log.info(f"Validated cron expression: {registration.cron_expression}")

        # Create new script record
        new_script = Script(
            script_name=registration.script_name,
            project_name=registration.project_name,
            version=new_version,
            is_active=True,
            created_at=datetime.utcnow(),
            cron_expression=registration.cron_expression
        )

        db.add(new_script)
        db.commit()
        log.info(f"Created new script record with version {new_version}")

        # Schedule the script if cron expression provided
        if registration.cron_expression:
            scheduler.schedule_script(
                registration.script_name,
                registration.project_name,
                registration.cron_expression
            )
            log.info("Script scheduled successfully")

        return {
            "status": "success",
            "message": "Script registered successfully",
            "version": new_version,
            "repository": registration.repository,
            "commit_sha": registration.commit_sha
        }

    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error registering script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scripts/upload")
async def upload_script(
    project_name: str = Form(...),
    script_name: str = Form(...),
    file: UploadFile = File(...),
    cron_expression: str = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a script package"""
    extract_dir = None
    log = logger.bind(log_type="execute")
    
    try:
        if not file.filename.endswith('.zip'):
            raise HTTPException(
                status_code=400,
                detail="Only zip files are accepted"
            )

        # Create project directory
        project_dir = f"/opt/scripts-store/{project_name}"
        os.makedirs(project_dir, exist_ok=True)
        
        # Save and extract zip
        zip_path = os.path.join(project_dir, file.filename)
        extract_dir = os.path.join(project_dir, script_name)
        
        # Handle existing version cleanup before extraction
        existing_script = db.query(Script).filter(
            Script.project_name == project_name,
            Script.script_name == script_name,
            Script.is_active == True
        ).first()

        if existing_script:
            # Clean up old version's environment
            old_package_manager = PackageManager(project_name, script_name)
            old_package_manager.cleanup_environment()
            logger.bind(log_type="execute").info(f"Cleaned up old version of {script_name} in {project_name}")

        # Clean up existing directory if it exists
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
        # Save zip file
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Extract zip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        logger.bind(log_type="execute").info(f"Extracted {file.filename} to {extract_dir}")
        
        # Remove zip file after extraction
        os.remove(zip_path)

        logger.bind(log_type="execute").info(f"Validating {script_name} in {project_name}")
        # Validate script
        validator = ScriptValidator(project_name, script_name)
        is_valid, message = validator.validate_all()
        
        if not is_valid:
            if extract_dir and os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            raise HTTPException(
                status_code=400,
                detail=f"Validation failed: {message}"
            )

        # Handle versioning
        if existing_script:
            # Increment version
            logger.bind(log_type="execute").info(f"Found existing version of {script_name} in {project_name}, incrementing version")
            version_parts = existing_script.version.split('.')
            new_version = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"
            
            # Deactivate old version
            existing_script.is_active = False
            db.add(existing_script)
            logger.bind(log_type="execute").info(f"Deactivated old version of {script_name} in {project_name}, new version is {new_version}")
        else:
            new_version = "1.0.0"

        # Create new script record
        new_script = Script(
            script_name=script_name,
            project_name=project_name,
            version=new_version,
            is_active=True,
            created_at=datetime.utcnow()
        )
        logger.bind(log_type="execute").info(f"Created record for {script_name} in {project_name}")

        # Add cron expression if provided
        if cron_expression:
            logger.bind(log_type="execute").info(f"Found cron expression: {cron_expression}, validating")
            if not croniter.is_valid(cron_expression):
                raise HTTPException(status_code=400, detail="Invalid cron expression")
            new_script.cron_expression = cron_expression
            logger.bind(log_type="execute").info(f"Validated cron expression: {cron_expression}")

        db.add(new_script)
        db.commit()

        # Schedule the script if cron expression provided
        if cron_expression:
            scheduler.schedule_script(script_name, project_name, cron_expression)
            logger.bind(log_type="execute").info(f"Script scheduled with cron expression: {cron_expression}")

        logger.bind(log_type="execute").info(f"Script uploaded successfully: {script_name} in {project_name}")
        return {
            "status": "success",
            "message": f"Script uploaded successfully",
            "version": new_version
        }

    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        if extract_dir and os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        logger.bind(log_type="execute").error(f"Error uploading script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scripts/{script_name}/run")
async def run_script(
    script_name: str,
    project_name: str,
    params: str = None,
    db: Session = Depends(get_db)
):
    """Run a script immediately"""
    try:
        # Verify script exists and is active
        script = db.query(Script).filter(
            Script.script_name == script_name,
            Script.project_name == project_name,
            Script.is_active == True
        ).first()
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found or not active")

        # Create executor and run script
        executor = ScriptExecutor(script_name, project_name)
        try:
            result = executor.execute(params)
            return result
        except Exception as e:
            raise e

    except HTTPException:
        raise
    except Exception as e:
        logger.bind(log_type="execute").error(f"Error running script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scripts/{script_name}/schedule")
async def schedule_script_endpoint(
    script_name: str,
    project_name: str,
    cron_expression: str,
    db: Session = Depends(get_db)
):
    """Schedule a script with cron expression"""
    try:
        # Validate cron expression
        if not croniter.is_valid(cron_expression):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
        
        # Verify script exists and is active
        script = db.query(Script).filter(
            Script.script_name == script_name,
            Script.project_name == project_name,
            Script.is_active == True
        ).first()
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found or not active")
        
        # Update script with cron expression
        script.cron_expression = cron_expression
        db.commit()
        
        # Schedule the script
        scheduler.schedule_script(script_name, project_name, cron_expression)
        
        return {
            "status": "success",
            "message": f"Script scheduled with cron expression: {cron_expression}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.bind(log_type="schedule").error(f"Error scheduling script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/scripts")
async def get_scripts(db: Session = Depends(get_db)):
    """Get all scripts"""
    return db.query(Script).all()

@router.get("/scripts/{script_name}/status")
async def get_script_status(
    script_name: str,
    project_name: str,
    db: Session = Depends(get_db)
):
    """Get status of a specific script"""
    script = db.query(Script).filter(
        Script.script_name == script_name,
        Script.project_name == project_name,
        Script.is_active == True
    ).first()
    
    if not script:
        raise HTTPException(status_code=404, detail="Script not found or not active")
        
    return {
        "script_name": script.script_name,
        "project_name": script.project_name,
        "version": script.version,
        "is_active": script.is_active,
        "last_run": script.last_run,
        "last_status": script.last_status,
        "run_count": script.run_count,
        "cron_expression": script.cron_expression
    }