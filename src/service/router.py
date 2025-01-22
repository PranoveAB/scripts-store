# src/service/router.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.service.models.db_model import Script
from src.service.models.schemas import ScriptRegistration
from src.static.executor import ScriptExecutor
from src.static.scheduler import scheduler
from src.static.package_manager import PackageManager
from src.utils.validator import ScriptValidator
from datetime import datetime
import os
import zipfile
from loguru import logger
import shutil
from croniter import croniter
import hmac
import hashlib

router = APIRouter()

def verify_github_signature(payload: bytes, signature: str) -> bool:
    """Verify GitHub webhook signature"""
    if not signature or not os.getenv('GITHUB_WEBHOOK_SECRET'):
        return False
    
    expected = 'sha256=' + hmac.new(
        os.getenv('GITHUB_WEBHOOK_SECRET').encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

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
        
        # Handle existing version cleanup
        existing_script = db.query(Script).filter(
            Script.project_name == project_name,
            Script.script_name == script_name,
            Script.is_active == True
        ).first()

        if existing_script:
            old_package_manager = PackageManager(project_name, script_name)
            old_package_manager.cleanup_environment()
            
        # Clean up existing directory
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
        # Save and extract zip
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        
        os.remove(zip_path)

        # Validate script
        validator = ScriptValidator(project_name, script_name)
        is_valid, message = validator.validate_all()
        
        if not is_valid:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)
            raise HTTPException(status_code=400, detail=f"Validation failed: {message}")

        # Handle versioning
        new_version = "1.0.0"
        if existing_script:
            version_parts = existing_script.version.split('.')
            new_version = f"{version_parts[0]}.{version_parts[1]}.{int(version_parts[2]) + 1}"
            existing_script.is_active = False
            db.add(existing_script)

        # Create new script record
        new_script = Script(
            script_name=script_name,
            project_name=project_name,
            version=new_version,
            is_active=True,
            created_at=datetime.utcnow()
        )

        if cron_expression:
            if not croniter.is_valid(cron_expression):
                raise HTTPException(status_code=400, detail="Invalid cron expression")
            new_script.cron_expression = cron_expression

        db.add(new_script)
        db.commit()

        if cron_expression:
            scheduler.schedule_script(script_name, project_name, cron_expression)

        return {
            "status": "success",
            "message": "Script uploaded successfully",
            "version": new_version
        }

    except HTTPException:
        raise
    except Exception as e:
        if extract_dir and os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        logger.bind(log_type="execute").error(f"Error uploading script: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook/github")
async def github_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle GitHub webhook events"""
    try:
        # Verify webhook signature
        signature = request.headers.get('X-Hub-Signature-256')
        payload = await request.body()
        if not verify_github_signature(payload, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

        data = await request.json()
        
        # Only process push events
        if data.get('ref', '').startswith('refs/heads/'):
            branch = data['ref'].split('/')[-1]
            repo_url = data['repository']['clone_url']
            commit_sha = data['after']

            # Find affected scripts
            scripts = db.query(Script).filter(
                Script.repository == repo_url,
                Script.branch == branch,
                Script.is_active == True
            ).all()

            processed_scripts = []
            for script in scripts:
                script.commit_sha = commit_sha
                processed_scripts.append(script.script_name)

            db.commit()

            return {
                "status": "success",
                "message": f"Processed scripts: {', '.join(processed_scripts)}"
            }
        
        return {"status": "ignored", "message": "Not a push event"}

    except HTTPException:
        raise
    except Exception as e:
        logger.bind(log_type="github").error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/scripts/register")
async def register_script(script_info: ScriptRegistration, db: Session = Depends(get_db)):
    """Register or update a script from GitHub"""
    try:
        script = db.query(Script).filter(
            Script.script_name == script_info.script_name,
            Script.project_name == script_info.project_name,
            Script.is_active == True
        ).first()
        
        if script:
            # Update existing script
            old_version = script.version.split('.')
            script.version = f"{old_version[0]}.{old_version[1]}.{int(old_version[2]) + 1}"
            script.commit_sha = script_info.commit_sha
            script.repository = script_info.repository
            script.branch = script_info.branch
        else:
            # Create new script
            script = Script(
                script_name=script_info.script_name,
                project_name=script_info.project_name,
                version="1.0.0",
                repository=script_info.repository,
                branch=script_info.branch,
                commit_sha=script_info.commit_sha,
                is_active=True
            )
            db.add(script)

        if script_info.cron_expression:
            if not croniter.is_valid(script_info.cron_expression):
                raise HTTPException(status_code=400, detail="Invalid cron expression")
            script.cron_expression = script_info.cron_expression
            scheduler.schedule_script(
                script.script_name,
                script.project_name,
                script.cron_expression
            )

        db.commit()

        return {
            "status": "success",
            "message": f"Script registered successfully with version {script.version}"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.bind(log_type="github").error(f"Registration error: {str(e)}")
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
        script = db.query(Script).filter(
            Script.script_name == script_name,
            Script.project_name == project_name,
            Script.is_active == True
        ).first()
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found or not active")

        executor = ScriptExecutor(script_name, project_name)
        return await executor.execute(params)

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
        if not croniter.is_valid(cron_expression):
            raise HTTPException(status_code=400, detail="Invalid cron expression")
        
        script = db.query(Script).filter(
            Script.script_name == script_name,
            Script.project_name == project_name,
            Script.is_active == True
        ).first()
        
        if not script:
            raise HTTPException(status_code=404, detail="Script not found or not active")
        
        script.cron_expression = cron_expression
        db.commit()
        
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
        "cron_expression": script.cron_expression,
        "repository": script.repository,
        "branch": script.branch,
        "commit_sha": script.commit_sha
    }