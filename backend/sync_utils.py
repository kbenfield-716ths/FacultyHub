"""
Utility functions to keep Provider and Faculty tables in sync.
Provider table is used for moonlighting, Faculty table for service scheduling.
They should always have matching emails for the same person.
"""
from sqlalchemy.orm import Session
from .models import Provider, Faculty
import logging

logger = logging.getLogger(__name__)


def sync_provider_from_faculty(db: Session, faculty_id: str) -> bool:
    """
    Sync a Provider record with the corresponding Faculty record.
    Creates Provider if it doesn't exist, updates email if it does.
    
    Args:
        db: Database session
        faculty_id: The faculty/provider ID (e.g., "KE4Z")
    
    Returns:
        bool: True if sync was successful, False otherwise
    """
    try:
        faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
        if not faculty:
            logger.warning(f"No Faculty record found for {faculty_id}")
            return False
        
        provider = db.query(Provider).filter(Provider.id == faculty_id).first()
        
        if not provider:
            # Create new Provider from Faculty
            provider = Provider(
                id=faculty.id,
                name=faculty.name,
                email=faculty.email
            )
            db.add(provider)
            logger.info(f"Created Provider record for {faculty.name} ({faculty_id})")
        else:
            # Update existing Provider
            provider.name = faculty.name
            provider.email = faculty.email
            logger.info(f"Updated Provider record for {faculty.name} ({faculty_id})")
        
        db.commit()
        return True
        
    except Exception as e:
        logger.error(f"Error syncing provider {faculty_id}: {e}")
        db.rollback()
        return False


def sync_faculty_from_provider(db: Session, provider_id: str) -> bool:
    """
    Sync a Faculty record with the corresponding Provider record.
    Only updates email if Faculty exists (doesn't create new Faculty records).
    
    Args:
        db: Database session
        provider_id: The provider ID (e.g., "KE4Z")
    
    Returns:
        bool: True if sync was successful, False otherwise
    """
    try:
        provider = db.query(Provider).filter(Provider.id == provider_id).first()
        if not provider or not provider.email:
            return False
        
        faculty = db.query(Faculty).filter(Faculty.id == provider_id).first()
        if faculty:
            faculty.email = provider.email
            db.commit()
            logger.info(f"Synced Faculty email from Provider for {provider_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error syncing faculty {provider_id}: {e}")
        db.rollback()
        return False


def sync_all_providers_from_faculty(db: Session) -> dict:
    """
    One-time sync of all Provider records from Faculty table.
    Creates missing Providers and updates emails for existing ones.
    
    Returns:
        dict: Summary of sync operation
    """
    try:
        all_faculty = db.query(Faculty).filter(Faculty.active == True).all()
        
        created = 0
        updated = 0
        skipped = 0
        
        for faculty in all_faculty:
            provider = db.query(Provider).filter(Provider.id == faculty.id).first()
            
            if not provider:
                # Create new Provider
                provider = Provider(
                    id=faculty.id,
                    name=faculty.name,
                    email=faculty.email
                )
                db.add(provider)
                created += 1
                logger.info(f"Created Provider for {faculty.name} ({faculty.id})")
            else:
                # Update existing Provider
                if provider.email != faculty.email or provider.name != faculty.name:
                    provider.name = faculty.name
                    provider.email = faculty.email
                    updated += 1
                    logger.info(f"Updated Provider for {faculty.name} ({faculty.id})")
                else:
                    skipped += 1
        
        db.commit()
        
        summary = {
            "status": "ok",
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "total": len(all_faculty)
        }
        
        logger.info(f"Sync complete: {summary}")
        return summary
        
    except Exception as e:
        logger.error(f"Error during bulk sync: {e}")
        db.rollback()
        return {
            "status": "error",
            "message": str(e)
        }
