from supabase import create_client, Client
from typing import Optional, Dict, Any, List
from app.core.config import settings

# Initialize Supabase client with service role for admin operations
supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)

class SupabaseService:
    """Wrapper for Supabase database operations."""
    
    @staticmethod
    async def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile by ID."""
        result = supabase.table("profiles").select("*").eq("id", user_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def create_clip(clip_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new clip."""
        result = supabase.table("clips").insert(clip_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def update_clip(clip_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a clip."""
        result = supabase.table("clips").update(update_data).eq("id", clip_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def list_clips(
        user_id: str,
        status: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List clips with filters."""
        query = supabase.table("clips").select("*").eq("user_id", user_id)
        
        if status:
            query = query.eq("status", status)
        if pipeline_id:
            query = query.eq("pipeline_id", pipeline_id)
        
        result = query.order("created_at", desc=True).limit(limit).offset(offset).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def create_pipeline(pipeline_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new pipeline."""
        result = supabase.table("pipelines").insert(pipeline_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def list_pipelines(user_id: str) -> List[Dict[str, Any]]:
        """List all pipelines for a user."""
        result = supabase.table("pipelines").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def create_source(source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new video source."""
        result = supabase.table("sources").insert(source_data).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def list_sources(user_id: str) -> List[Dict[str, Any]]:
        """List all sources for a user."""
        result = supabase.table("sources").select("*").eq("user_id", user_id).execute()
        return result.data if result.data else []
    
    @staticmethod
    async def get_source(source_id: str) -> Optional[Dict[str, Any]]:
        """Get a source by ID."""
        result = supabase.table("sources").select("*").eq("id", source_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def get_pipeline(pipeline_id: str) -> Optional[Dict[str, Any]]:
        """Get a pipeline by ID."""
        result = supabase.table("pipelines").select("*").eq("id", pipeline_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def update_pipeline(pipeline_id: str, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update a pipeline."""
        result = supabase.table("pipelines").update(update_data).eq("id", pipeline_id).execute()
        return result.data[0] if result.data else {}
    
    @staticmethod
    async def delete_pipeline(pipeline_id: str) -> bool:
        """Delete a pipeline."""
        result = supabase.table("pipelines").delete().eq("id", pipeline_id).execute()
        return len(result.data) > 0 if result.data else False
    
    @staticmethod
    async def get_clip(clip_id: str) -> Optional[Dict[str, Any]]:
        """Get a clip by ID."""
        result = supabase.table("clips").select("*").eq("id", clip_id).single().execute()
        return result.data if result.data else None
    
    @staticmethod
    async def delete_clip(clip_id: str) -> bool:
        """Delete a clip."""
        result = supabase.table("clips").delete().eq("id", clip_id).execute()
        return len(result.data) > 0 if result.data else False
    
    @staticmethod
    async def get_clips_for_posting(
        status: str = "approved",
        scheduled_before: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get clips ready for posting."""
        query = supabase.table("clips").select("*").eq("status", status)
        
        if scheduled_before:
            query = query.lte("scheduled_post_time", scheduled_before)
        
        result = query.execute()
        return result.data if result.data else []
    
    @staticmethod
    async def update_earnings(earnings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or update earnings record."""
        result = supabase.table("earnings").upsert(earnings_data).execute()
        return result.data[0] if result.data else {}
